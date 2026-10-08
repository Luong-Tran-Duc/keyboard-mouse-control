"""Core controller managing state, input hooks, and event forwarding."""

import sys
import time
import logging
import threading
import ctypes
from ctypes import wintypes
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

# Enable Per-Monitor DPI awareness on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from desktop import config
from desktop.protocol import (
    pack_mouse_move, pack_mouse_click, pack_mouse_scroll,
    pack_key_press, pack_key_release, pack_active, pack_inactive,
    MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE,
    MOD_LCTRL, MOD_LSHIFT, MOD_LALT, MOD_LGUI,
    MOD_RCTRL, MOD_RSHIFT, MOD_RALT, MOD_RGUI
)
from desktop.hid_keycodes import key_to_hid, MODIFIER_KEY_MASK
from desktop.network import UDPClient
from desktop.raw_mouse import RawMouseListener

logger = logging.getLogger("KMBridge")
user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]


def calculate_accelerated_delta(raw_delta: int, sensitivity: float, use_accel: bool) -> int:
    """Calculate snappy responsive mouse delta."""
    if raw_delta == 0:
        return 0

    mag = abs(raw_delta)
    if use_accel:
        if mag <= 3:
            factor = 1.0
        elif mag <= 10:
            factor = 1.2
        elif mag <= 25:
            factor = 1.45
        else:
            factor = 1.75
    else:
        factor = 1.0

    val = int(raw_delta * sensitivity * factor)
    return val if val != 0 else (1 if raw_delta > 0 else -1)


class KMController:
    def __init__(self):
        self.client = UDPClient(config.ESP32_IP, config.UDP_PORT)
        self.is_active = False  # False = Laptop A, True = Laptop B

        # Track active HID keycodes currently held down
        self.pressed_hid_codes = set()
        self.active_modifiers = 0

        # Track ctrl / alt for hotkey toggle (Ctrl + Alt + Space)
        self.ctrl_pressed = False
        self.alt_pressed = False

        # Screen metrics
        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)
        self.screen_cx = self.screen_w // 2
        self.screen_cy = self.screen_h // 2

        # High-frequency mouse accumulator (prevents Wi-Fi UDP buffer bloat)
        self.accum_dx = 0
        self.accum_dy = 0
        self.accum_lock = threading.Lock()
        self.mouse_worker_running = True
        self.mouse_thread = threading.Thread(target=self._mouse_sender_loop, daemon=True)
        self.mouse_thread.start()

        # Listeners
        self.kb_listener = None
        self.mouse_listener = RawMouseListener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )

    def _mouse_sender_loop(self):
        """Dedicated high-speed 125Hz sender loop (8ms interval)."""
        interval = 1.0 / max(30, config.MOUSE_POLL_RATE_HZ)
        while self.mouse_worker_running:
            start_t = time.perf_counter()

            if self.is_active:
                send_dx = 0
                send_dy = 0
                with self.accum_lock:
                    if self.accum_dx != 0 or self.accum_dy != 0:
                        send_dx = self.accum_dx
                        send_dy = self.accum_dy
                        self.accum_dx = 0
                        self.accum_dy = 0

                if send_dx != 0 or send_dy != 0:
                    adj_dx = calculate_accelerated_delta(
                        send_dx, config.MOUSE_SENSITIVITY, config.MOUSE_ACCELERATION
                    )
                    adj_dy = calculate_accelerated_delta(
                        send_dy, config.MOUSE_SENSITIVITY, config.MOUSE_ACCELERATION
                    )

                    if config.INVERT_X:
                        adj_dx = -adj_dx
                    if config.INVERT_Y:
                        adj_dy = -adj_dy

                    if adj_dx != 0 or adj_dy != 0:
                        self.client.send(pack_mouse_move(adj_dx, adj_dy))

            elapsed = time.perf_counter() - start_t
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def toggle_state(self):
        """Toggle active control between Laptop A and Laptop B."""
        self.is_active = not self.is_active

        if self.is_active:
            print("\n" + "=" * 50)
            print(">>> ACTIVE: CONTROLLING LAPTOP B <<<")
            print("Press [Ctrl + Alt + Space] to return to Laptop A")
            print("=" * 50)
            self.client.send(pack_active())
            self.pressed_hid_codes.clear()
            self.ctrl_pressed = False
            self.alt_pressed = False
            self.active_modifiers = 0

            with self.accum_lock:
                self.accum_dx = 0
                self.accum_dy = 0

            # Center and lock cursor on Laptop A
            user32.SetCursorPos(self.screen_cx, self.screen_cy)
            clip_rect = RECT(self.screen_cx, self.screen_cy, self.screen_cx + 1, self.screen_cy + 1)
            user32.ClipCursor(ctypes.byref(clip_rect))

            # Suppress keyboard and mouse clicks on Laptop A
            if self.kb_listener:
                self.kb_listener._suppress = True
            if self.mouse_listener:
                self.mouse_listener.suppress = True
        else:
            print("\n" + "=" * 50)
            print("<<< INACTIVE: CONTROLLING LAPTOP A >>>")
            print("Press [Ctrl + Alt + Space] to switch to Laptop B")
            print("=" * 50)
            self.client.send(pack_inactive())
            self.pressed_hid_codes.clear()
            self.ctrl_pressed = False
            self.alt_pressed = False
            self.active_modifiers = 0

            with self.accum_lock:
                self.accum_dx = 0
                self.accum_dy = 0

            # Unlock cursor on Laptop A
            user32.ClipCursor(None)

            # Release suppression
            if self.kb_listener:
                self.kb_listener._suppress = False
            if self.mouse_listener:
                self.mouse_listener.suppress = False

    def on_key_press(self, key):
        # Update modifier tracking
        if key in (Key.ctrl_l, Key.ctrl, Key.ctrl_r):
            self.ctrl_pressed = True
        if key in (Key.alt_l, Key.alt, Key.alt_r, Key.alt_gr):
            self.alt_pressed = True

        # Check hotkey: Ctrl + Alt + Space
        if self.ctrl_pressed and self.alt_pressed and key == Key.space:
            self.toggle_state()
            return

        if not self.is_active:
            return

        # Handle modifier keys (Ctrl, Shift, Alt, GUI) - send with keycode 0
        if key in MODIFIER_KEY_MASK:
            old_mod = self.active_modifiers
            self.active_modifiers |= MODIFIER_KEY_MASK[key]
            if self.active_modifiers != old_mod:
                self.client.send(pack_key_press(0, self.active_modifiers))
            return

        hid_code = key_to_hid(key)
        if hid_code != 0:
            # Drop repeat events from OS auto-repeat while key is held down
            if hid_code in self.pressed_hid_codes:
                return

            self.pressed_hid_codes.add(hid_code)
            self.client.send(pack_key_press(hid_code, self.active_modifiers))
            print(f"[KEY] DOWN: {str(key):<12} -> HID 0x{hid_code:02X}")

    def on_key_release(self, key):
        if key in (Key.ctrl_l, Key.ctrl, Key.ctrl_r):
            self.ctrl_pressed = False
        if key in (Key.alt_l, Key.alt, Key.alt_r, Key.alt_gr):
            self.alt_pressed = False

        if not self.is_active:
            return

        # Handle modifier keys release - send with keycode 0
        if key in MODIFIER_KEY_MASK:
            old_mod = self.active_modifiers
            self.active_modifiers &= ~MODIFIER_KEY_MASK[key]
            if self.active_modifiers != old_mod:
                self.client.send(pack_key_press(0, self.active_modifiers))
            return

        hid_code = key_to_hid(key)
        if hid_code != 0:
            self.pressed_hid_codes.discard(hid_code)
            pkt = pack_key_release(hid_code)
            self.client.send(pkt)
            self.client.send(pkt)
            print(f"[KEY] UP  : {str(key):<12} -> HID 0x{hid_code:02X}")

    def on_mouse_move(self, dx, dy):
        if not self.is_active:
            return

        # Fast accumulation: sum deltas until next 125Hz transmission tick
        with self.accum_lock:
            self.accum_dx += dx
            self.accum_dy += dy

    def on_mouse_click(self, button, pressed):
        if not self.is_active:
            return

        # Send clicks immediately (0ms delay)
        self.client.send(pack_mouse_click(button, pressed))

    def on_mouse_scroll(self, delta):
        if not self.is_active:
            return

        if delta != 0:
            self.client.send(pack_mouse_scroll(int(delta)))

    def start(self):
        """Start listening for mouse and keyboard events."""
        print("KM Bridge Client started.")
        print(f"Target ESP32: {config.ESP32_IP}:{config.UDP_PORT}")
        print(f"Toggle Hotkey: Ctrl + Alt + Space")
        print(f"Mouse Rate: {config.MOUSE_POLL_RATE_HZ}Hz (Anti-Lag Batching)")
        print(f"Sensitivity: {config.MOUSE_SENSITIVITY}x")
        print("Current mode: CONTROLLING LAPTOP A")
        print("Press Ctrl+C to terminate.")

        self.kb_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release,
            suppress=False
        )
        self.kb_listener.start()
        self.mouse_listener.start()

        try:
            self.kb_listener.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Gracefully shutdown."""
        print("\nStopping KM Bridge Client...")
        self.mouse_worker_running = False
        user32.ClipCursor(None)
        if self.is_active:
            self.client.send(pack_inactive())
        if self.kb_listener:
            self.kb_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        self.client.close()
        print("Stopped.")
