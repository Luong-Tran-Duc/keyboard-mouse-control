#include "usb_hid.h"
#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "class/hid/hid_device.h"

static const char *TAG = "usb_hid";

#define TUSB_DESC_TOTAL_LEN (TUD_CONFIG_DESC_LEN + CFG_TUD_HID * TUD_HID_DESC_LEN)

// Composite HID report descriptor: Keyboard + Mouse
const uint8_t hid_report_descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD(HID_REPORT_ID(HID_ITF_PROTOCOL_KEYBOARD)),
    TUD_HID_REPORT_DESC_MOUSE(HID_REPORT_ID(HID_ITF_PROTOCOL_MOUSE))
};

// USB string descriptors
const char *hid_string_descriptor[5] = {
    (char[]){0x09, 0x04},     // 0: English (0x0409)
    "Espressif",              // 1: Manufacturer
    "KM Bridge HID Device",   // 2: Product
    "ESP32S3KM001",           // 3: Serial Number
    "KM Bridge HID Interface" // 4: Interface Name
};

// USB configuration descriptor
static const uint8_t hid_configuration_descriptor[] = {
    // Configuration descriptor
    TUD_CONFIG_DESCRIPTOR(1, 1, 0, TUSB_DESC_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),
    // HID interface descriptor
    TUD_HID_DESCRIPTOR(0, 4, false, sizeof(hid_report_descriptor), 0x81, 16, 10),
};

// Internal input state
static uint8_t s_mouse_buttons = 0;
static uint8_t s_modifiers = 0;
static uint8_t s_active_keys[6] = {0};
static SemaphoreHandle_t s_hid_mutex = NULL;

// TinyUSB callbacks
uint8_t const *tud_hid_descriptor_report_cb(uint8_t instance)
{
    (void)instance;
    return hid_report_descriptor;
}

uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t *buffer, uint16_t reqlen)
{
    (void)instance;
    (void)report_id;
    (void)report_type;
    (void)buffer;
    (void)reqlen;
    return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type, uint8_t const *buffer, uint16_t bufsize)
{
    (void)instance;
    (void)report_id;
    (void)report_type;
    (void)buffer;
    (void)bufsize;
}

esp_err_t usb_hid_init(void)
{
    ESP_LOGI(TAG, "Initializing TinyUSB HID stack");

    s_hid_mutex = xSemaphoreCreateMutex();
    if (!s_hid_mutex) {
        ESP_LOGE(TAG, "Failed to create HID mutex");
        return ESP_ERR_NO_MEM;
    }

    tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();
    tusb_cfg.descriptor.device = NULL;
    tusb_cfg.descriptor.full_speed_config = hid_configuration_descriptor;
    tusb_cfg.descriptor.string = hid_string_descriptor;
    tusb_cfg.descriptor.string_count = sizeof(hid_string_descriptor) / sizeof(hid_string_descriptor[0]);

    esp_err_t err = tinyusb_driver_install(&tusb_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install TinyUSB driver: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "TinyUSB HID driver initialized successfully");
    return ESP_OK;
}

bool usb_hid_is_mounted(void)
{
    return tud_mounted();
}

static inline int8_t clamp_i8(int16_t val)
{
    if (val > 127) return 127;
    if (val < -127) return -127;
    return (int8_t)val;
}

static bool send_keyboard_report_with_retry(void)
{
    // Wait up to 30ms for USB endpoint to become ready
    for (int retry = 0; retry < 15; retry++) {
        if (tud_hid_ready()) {
            if (tud_hid_keyboard_report(HID_ITF_PROTOCOL_KEYBOARD, s_modifiers, s_active_keys)) {
                return true;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    return false;
}

void usb_hid_mouse_move(int16_t dx, int16_t dy)
{
    if (!tud_mounted() || !tud_hid_ready()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(5)) == pdTRUE) {
        int8_t clamped_x = clamp_i8(dx);
        int8_t clamped_y = clamp_i8(dy);
        tud_hid_mouse_report(HID_ITF_PROTOCOL_MOUSE, s_mouse_buttons, clamped_x, clamped_y, 0, 0);
        xSemaphoreGive(s_hid_mutex);
    }
}

void usb_hid_mouse_click(uint8_t button, uint8_t pressed)
{
    if (!tud_mounted()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
        if (pressed) {
            s_mouse_buttons |= button;
        } else {
            s_mouse_buttons &= ~button;
        }
        tud_hid_mouse_report(HID_ITF_PROTOCOL_MOUSE, s_mouse_buttons, 0, 0, 0, 0);
        xSemaphoreGive(s_hid_mutex);
    }
}

void usb_hid_mouse_scroll(int16_t delta)
{
    if (!tud_mounted()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
        int8_t clamped_delta = clamp_i8(delta);
        tud_hid_mouse_report(HID_ITF_PROTOCOL_MOUSE, s_mouse_buttons, 0, 0, clamped_delta, 0);
        xSemaphoreGive(s_hid_mutex);
    }
}

void usb_hid_keyboard_press(uint8_t keycode, uint8_t modifiers)
{
    if (!tud_mounted()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(20)) == pdTRUE) {
        s_modifiers = modifiers;

        if (keycode != 0) {
            // Compact existing keys and check if already present
            uint8_t compacted[6] = {0};
            int count = 0;
            bool already_pressed = false;

            for (int i = 0; i < 6; i++) {
                if (s_active_keys[i] != 0) {
                    if (s_active_keys[i] == keycode) {
                        already_pressed = true;
                    }
                    if (count < 6) {
                        compacted[count++] = s_active_keys[i];
                    }
                }
            }

            if (!already_pressed && count < 6) {
                compacted[count++] = keycode;
            }

            memcpy(s_active_keys, compacted, sizeof(s_active_keys));
        }

        send_keyboard_report_with_retry();
        xSemaphoreGive(s_hid_mutex);
    }
}

void usb_hid_keyboard_release(uint8_t keycode)
{
    if (!tud_mounted()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(20)) == pdTRUE) {
        if (keycode == 0) {
            // Keycode 0 means release all active keys
            memset(s_active_keys, 0, sizeof(s_active_keys));
        } else {
            // Compact remaining keys, excluding the released keycode
            uint8_t compacted[6] = {0};
            int count = 0;

            for (int i = 0; i < 6; i++) {
                if (s_active_keys[i] != 0 && s_active_keys[i] != keycode) {
                    if (count < 6) {
                        compacted[count++] = s_active_keys[i];
                    }
                }
            }

            memcpy(s_active_keys, compacted, sizeof(s_active_keys));
        }

        send_keyboard_report_with_retry();
        xSemaphoreGive(s_hid_mutex);
    }
}

void usb_hid_release_all(void)
{
    if (!tud_mounted()) return;

    if (xSemaphoreTake(s_hid_mutex, pdMS_TO_TICKS(20)) == pdTRUE) {
        s_mouse_buttons = 0;
        s_modifiers = 0;
        memset(s_active_keys, 0, sizeof(s_active_keys));

        tud_hid_mouse_report(HID_ITF_PROTOCOL_MOUSE, 0, 0, 0, 0, 0);
        send_keyboard_report_with_retry();
        xSemaphoreGive(s_hid_mutex);
    }
}

