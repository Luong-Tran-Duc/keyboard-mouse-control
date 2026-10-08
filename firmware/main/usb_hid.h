#ifndef USB_HID_H
#define USB_HID_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// Initialize TinyUSB driver with composite HID (Keyboard + Mouse)
esp_err_t usb_hid_init(void);

// Check if USB device is mounted on host
bool usb_hid_is_mounted(void);

// Mouse control functions
void usb_hid_mouse_move(int16_t dx, int16_t dy);
void usb_hid_mouse_click(uint8_t button, uint8_t pressed);
void usb_hid_mouse_scroll(int16_t delta);

// Keyboard control functions
void usb_hid_keyboard_press(uint8_t keycode, uint8_t modifiers);
void usb_hid_keyboard_release(uint8_t keycode);

// Release all keys and mouse buttons
void usb_hid_release_all(void);

#ifdef __cplusplus
}
#endif

#endif // USB_HID_H

