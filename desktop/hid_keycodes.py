"""USB HID Usage Table Page 0x07 (Keyboard) keycodes and robust VK mapping."""

import ctypes
from ctypes import wintypes
from pynput.keyboard import Key, KeyCode
from desktop.protocol import (
    MOD_LCTRL, MOD_LSHIFT, MOD_LALT, MOD_LGUI,
    MOD_RCTRL, MOD_RSHIFT, MOD_RALT, MOD_RGUI
)

user32 = ctypes.windll.user32
user32.VkKeyScanW.argtypes = [ctypes.c_wchar]
user32.VkKeyScanW.restype = ctypes.c_short

# USB HID Keycodes
HID_KEY_ENTER = 0x28
HID_KEY_ESCAPE = 0x29
HID_KEY_BACKSPACE = 0x2A
HID_KEY_TAB = 0x2B
HID_KEY_SPACE = 0x2C
HID_KEY_CAPSLOCK = 0x39

# Modifiers
HID_KEY_LEFTCTRL = 0xE0
HID_KEY_LEFTSHIFT = 0xE1
HID_KEY_LEFTALT = 0xE2
HID_KEY_LEFTMETA = 0xE3
HID_KEY_RIGHTCTRL = 0xE4
HID_KEY_RIGHTSHIFT = 0xE5
HID_KEY_RIGHTALT = 0xE6
HID_KEY_RIGHTMETA = 0xE7

# Master Virtual Key (Windows VK) -> USB HID Mapping Table
VK_TO_HID = {
    # Control keys
    0x0D: 0x28,  # VK_RETURN -> Enter
    0x1B: 0x29,  # VK_ESCAPE -> Esc
    0x08: 0x2A,  # VK_BACK -> Backspace
    0x09: 0x2B,  # VK_TAB -> Tab
    0x20: 0x2C,  # VK_SPACE -> Space
    0x14: 0x39,  # VK_CAPITAL -> Caps Lock

    # Punctuation & Symbols (US Keyboard layout)
    0xBD: 0x2D,  # VK_OEM_MINUS -> '-'
    0xBB: 0x2E,  # VK_OEM_PLUS -> '='
    0xDB: 0x2F,  # VK_OEM_4 -> '['
    0xDD: 0x30,  # VK_OEM_6 -> ']'
    0xDC: 0x31,  # VK_OEM_5 -> '\'
    0xBA: 0x33,  # VK_OEM_1 -> ';'
    0xDE: 0x34,  # VK_OEM_7 -> "'"
    0xC0: 0x35,  # VK_OEM_3 -> '`'
    0xBC: 0x36,  # VK_OEM_COMMA -> ','
    0xBE: 0x37,  # VK_OEM_PERIOD -> '.'
    0xBF: 0x38,  # VK_OEM_2 -> '/'

    # Navigation & Editing
    0x2C: 0x46,  # VK_SNAPSHOT -> PrintScreen
    0x91: 0x47,  # VK_SCROLL -> ScrollLock
    0x13: 0x48,  # VK_PAUSE -> Pause
    0x2D: 0x49,  # VK_INSERT -> Insert
    0x24: 0x4A,  # VK_HOME -> Home
    0x21: 0x4B,  # VK_PRIOR -> PageUp
    0x2E: 0x4C,  # VK_DELETE -> Delete
    0x23: 0x4D,  # VK_END -> End
    0x22: 0x4E,  # VK_NEXT -> PageDown
    0x27: 0x4F,  # VK_RIGHT -> Right Arrow
    0x25: 0x50,  # VK_LEFT -> Left Arrow
    0x28: 0x51,  # VK_DOWN -> Down Arrow
    0x26: 0x52,  # VK_UP -> Up Arrow

    # Modifiers
    0xA2: 0xE0,  # VK_LCONTROL
    0x11: 0xE0,  # VK_CONTROL
    0xA0: 0xE1,  # VK_LSHIFT
    0x10: 0xE1,  # VK_SHIFT
    0xA4: 0xE2,  # VK_LMENU (Alt)
    0x12: 0xE2,  # VK_MENU (Alt)
    0x5B: 0xE3,  # VK_LWIN
    0xA3: 0xE4,  # VK_RCONTROL
    0xA1: 0xE5,  # VK_RSHIFT
    0xA5: 0xE6,  # VK_RMENU (Alt)
    0x5C: 0xE7,  # VK_RWIN

    # Numpad
    0x60: 0x62,  # VK_NUMPAD0
    0x61: 0x59,  # VK_NUMPAD1
    0x62: 0x5A,  # VK_NUMPAD2
    0x63: 0x5B,  # VK_NUMPAD3
    0x64: 0x5C,  # VK_NUMPAD4
    0x65: 0x5D,  # VK_NUMPAD5
    0x66: 0x5E,  # VK_NUMPAD6
    0x67: 0x5F,  # VK_NUMPAD7
    0x68: 0x60,  # VK_NUMPAD8
    0x69: 0x61,  # VK_NUMPAD9
    0x6A: 0x55,  # VK_MULTIPLY
    0x6B: 0x57,  # VK_ADD
    0x6D: 0x56,  # VK_SUBTRACT
    0x6E: 0x63,  # VK_DECIMAL
    0x6F: 0x54,  # VK_DIVIDE
}

# A-Z (0x41 - 0x5A) -> HID 0x04 - 0x1D
for i in range(26):
    VK_TO_HID[0x41 + i] = 0x04 + i

# 0-9 (0x30 - 0x39) -> HID 0x27 for 0, 0x1E - 0x26 for 1-9
VK_TO_HID[0x30] = 0x27
for i in range(1, 10):
    VK_TO_HID[0x30 + i] = 0x1E + (i - 1)

# F1-F12 (0x70 - 0x7B) -> HID 0x3A - 0x45
for i in range(12):
    VK_TO_HID[0x70 + i] = 0x3A + i

# Modifier bitmask mapping
MODIFIER_KEY_MASK = {
    Key.ctrl_l: MOD_LCTRL,
    Key.ctrl: MOD_LCTRL,
    Key.ctrl_r: MOD_RCTRL,
    Key.shift_l: MOD_LSHIFT,
    Key.shift: MOD_LSHIFT,
    Key.shift_r: MOD_RSHIFT,
    Key.alt_l: MOD_LALT,
    Key.alt: MOD_LALT,
    Key.alt_r: MOD_RALT,
    Key.cmd: MOD_LGUI,
    Key.cmd_l: MOD_LGUI,
    Key.cmd_r: MOD_RGUI,
}


def key_to_vk(key) -> int:
    """Resolve pynput Key or KeyCode to Windows Virtual Key code."""
    # 1. From key.vk
    if hasattr(key, 'vk') and key.vk is not None:
        return key.vk
    # 2. From key.value.vk (special Key enum)
    if hasattr(key, 'value') and hasattr(key.value, 'vk') and key.value.vk is not None:
        return key.value.vk
    # 3. From key.char
    if hasattr(key, 'char') and key.char:
        c = key.char
        if 'a' <= c <= 'z' or 'A' <= c <= 'Z':
            return ord(c.upper())
        if '0' <= c <= '9':
            return ord(c)
        scan = user32.VkKeyScanW(c)
        if scan != -1:
            return scan & 0xFF
    return 0


def key_to_hid(key) -> int:
    """Convert pynput Key or KeyCode to USB HID Keycode (excludes modifier keys)."""
    vk = key_to_vk(key)
    hid = VK_TO_HID.get(vk, 0)
    # 0xE0 - 0xE7 are USB HID modifiers, they belong in modifier byte, NOT in keycode array
    if 0xE0 <= hid <= 0xE7:
        return 0
    return hid

