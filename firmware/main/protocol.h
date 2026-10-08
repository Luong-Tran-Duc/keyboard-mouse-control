#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Command OpCodes
#define CMD_MOUSE_MOVE    0x01
#define CMD_MOUSE_CLICK   0x02
#define CMD_MOUSE_SCROLL  0x03
#define CMD_KEY_PRESS     0x04
#define CMD_KEY_RELEASE   0x05
#define CMD_ACTIVE            0xFE
#define CMD_INACTIVE          0xFF
#define CMD_REBOOT_BOOTLOADER 0xAA

// Mouse button bitmasks
#define MOUSE_BUTTON_LEFT   (1 << 0)
#define MOUSE_BUTTON_RIGHT  (1 << 1)
#define MOUSE_BUTTON_MIDDLE (1 << 2)

#pragma pack(push, 1)

typedef struct {
    uint8_t cmd;      // CMD_MOUSE_MOVE
    int16_t dx;       // Relative X movement
    int16_t dy;       // Relative Y movement
} packet_mouse_move_t;

typedef struct {
    uint8_t cmd;      // CMD_MOUSE_CLICK
    uint8_t button;   // MOUSE_BUTTON_LEFT / RIGHT / MIDDLE
    uint8_t pressed;  // 1 = Pressed, 0 = Released
} packet_mouse_click_t;

typedef struct {
    uint8_t cmd;      // CMD_MOUSE_SCROLL
    int16_t delta;    // Scroll delta (wheel)
} packet_mouse_scroll_t;

typedef struct {
    uint8_t cmd;        // CMD_KEY_PRESS
    uint8_t keycode;    // USB HID Keycode
    uint8_t modifiers;  // Modifier bitmask (Ctrl, Shift, Alt, GUI)
} packet_key_press_t;

typedef struct {
    uint8_t cmd;        // CMD_KEY_RELEASE
    uint8_t keycode;    // USB HID Keycode
} packet_key_release_t;

typedef struct {
    uint8_t cmd;        // CMD_ACTIVE or CMD_INACTIVE
} packet_control_t;

#pragma pack(pop)

#ifdef __cplusplus
}
#endif

#endif // PROTOCOL_H

