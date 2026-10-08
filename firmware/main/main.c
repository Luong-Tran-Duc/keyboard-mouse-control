#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "usb_hid.h"
#include "wifi_udp.h"
#include "rgb_led.h"
#include "wifi_config.h"

static const char *TAG = "main";

void app_main(void)
{
    ESP_LOGI(TAG, "================================================");
    ESP_LOGI(TAG, "   KM Bridge ESP32-S3 Firmware (ESP-IDF v6.x)   ");
    ESP_LOGI(TAG, "================================================");

    // 1. Initialize NVS Flash (required for Wi-Fi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Initialize Onboard WS2812 RGB Status LED
    ESP_ERROR_CHECK(rgb_led_init());

    // 3. Initialize USB TinyUSB HID (Mouse + Keyboard composite)
    ESP_ERROR_CHECK(usb_hid_init());

    // 4. Initialize Wi-Fi Station (will trigger RGB yellow blinking while connecting)
    ESP_ERROR_CHECK(wifi_init_sta());

    // 5. Start UDP Server Task
    ESP_ERROR_CHECK(start_udp_server());

    ESP_LOGI(TAG, "All subsystems running. Awaiting input packets...");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
