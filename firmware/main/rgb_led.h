#ifndef RGB_LED_H
#define RGB_LED_H

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    RGB_STATE_OFF = 0,
    RGB_STATE_CONNECTING,  // Blinking yellow (trying to connect to Wi-Fi)
    RGB_STATE_FAILED,      // Solid red (connection failed / disconnected)
    RGB_STATE_CONNECTED    // Solid green (connected to Wi-Fi)
} rgb_state_t;

// Initialize the onboard WS2812 RGB LED via RMT
esp_err_t rgb_led_init(void);

// Set the RGB status state
void rgb_led_set_state(rgb_state_t state);

// Direct RGB color control (0 - 255)
void rgb_led_set_color(uint8_t red, uint8_t green, uint8_t blue);

#ifdef __cplusplus
}
#endif

#endif // RGB_LED_H

