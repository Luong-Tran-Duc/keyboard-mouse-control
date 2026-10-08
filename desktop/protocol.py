"""Binary protocol encoder matching firmware/main/protocol.h."""

import struct

CMD_MOUSE_MOVE = 0x01
CMD_MOUSE_CLICK = 0x02
CMD_MOUSE_SCROLL = 0x03
CMD_KEY_PRESS = 0x04
CMD_KEY_RELEASE = 0x05
CMD_ACTIVE = 0xFE
CMD_INACTIVE = 0xFF
CMD_REBOOT_BOOTLOADER = 0xAA

MOUSE_BUTTON_LEFT = 1 << 0
MOUSE_BUTTON_RIGHT = 1 << 1
MOUSE_BUTTON_MIDDLE = 1 << 2

MOD_LCTRL = 1 << 0
MOD_LSHIFT = 1 << 1
MOD_LALT = 1 << 2
MOD_LGUI = 1 << 3
MOD_RCTRL = 1 << 4
MOD_RSHIFT = 1 << 5
MOD_RALT = 1 << 6
MOD_RGUI = 1 << 7


def pack_mouse_move(dx: int, dy: int) -> bytes:
    """Pack relative mouse movement."""
    # Clamp to signed 16-bit
    dx = max(-32768, min(32767, int(dx)))
    dy = max(-32768, min(32767, int(dy)))
    return struct.pack("<Bhh", CMD_MOUSE_MOVE, dx, dy)


def pack_mouse_click(button: int, pressed: bool) -> bytes:
    """Pack mouse button press or release."""
    return struct.pack("<BBB", CMD_MOUSE_CLICK, button, 1 if pressed else 0)


def pack_mouse_scroll(delta: int) -> bytes:
    """Pack mouse scroll wheel delta."""
    delta = max(-32768, min(32767, int(delta)))
    return struct.pack("<Bh", CMD_MOUSE_SCROLL, delta)


def pack_key_press(keycode: int, modifiers: int = 0) -> bytes:
    """Pack USB HID key press with active modifier bitmask."""
    return struct.pack("<BBB", CMD_KEY_PRESS, keycode & 0xFF, modifiers & 0xFF)


def pack_key_release(keycode: int) -> bytes:
    """Pack USB HID key release."""
    return struct.pack("<BB", CMD_KEY_RELEASE, keycode & 0xFF)


def pack_active() -> bytes:
    """Pack active mode notification."""
    return struct.pack("<B", CMD_ACTIVE)


def pack_inactive() -> bytes:
    """Pack inactive mode notification."""
    return struct.pack("<B", CMD_INACTIVE)


def pack_reboot_bootloader() -> bytes:
    """Pack reboot into download mode command."""
    return struct.pack("<B", CMD_REBOOT_BOOTLOADER)

