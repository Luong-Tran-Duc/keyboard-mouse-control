#include "rgb_led.h"
#include "esp_log.h"
#include "led_strip.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "wifi_config.h"

static const char *TAG = "rgb_led";

static led_strip_handle_t s_led_strip = NULL;
static rgb_state_t s_current_state = RGB_STATE_OFF;
static TaskHandle_t s_blink_task = NULL;

static void rgb_blink_task(void *pvParameters)
{
    bool toggle = false;

    while (1) {
        if (s_current_state == RGB_STATE_CONNECTING) {
            if (toggle) {
                // Yellow: Red + Green (moderate brightness)
                led_strip_set_pixel(s_led_strip, 0, 40, 30, 0);
                led_strip_refresh(s_led_strip);
            } else {
                led_strip_clear(s_led_strip);
            }
            toggle = !toggle;
            vTaskDelay(pdMS_TO_TICKS(500));
        } else {
            // Wait when not in blinking state
            ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
            toggle = true;
        }
    }
}

esp_err_t rgb_led_init(void)
{
    ESP_LOGI(TAG, "Initializing RGB LED on GPIO %d", CONFIG_RGB_LED_GPIO);

    led_strip_config_t strip_config = {
        .strip_gpio_num = CONFIG_RGB_LED_GPIO,
        .max_leds = 1,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
        .flags = {
            .invert_out = false,
        }
    };

    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000, // 10MHz
        .flags = {
            .with_dma = false,
        }
    };

    esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &s_led_strip);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize RMT led_strip: %s", esp_err_to_name(err));
        return err;
    }

    led_strip_clear(s_led_strip);

    BaseType_t ret = xTaskCreate(
        rgb_blink_task,
        "rgb_blink",
        2048,
        NULL,
        tskIDLE_PRIORITY + 1,
        &s_blink_task
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create RGB blink task");
        return ESP_FAIL;
    }

    return ESP_OK;
}

void rgb_led_set_color(uint8_t red, uint8_t green, uint8_t blue)
{
    if (!s_led_strip) return;

    if (red == 0 && green == 0 && blue == 0) {
        led_strip_clear(s_led_strip);
    } else {
        led_strip_set_pixel(s_led_strip, 0, red, green, blue);
        led_strip_refresh(s_led_strip);
    }
}

void rgb_led_set_state(rgb_state_t state)
{
    if (!s_led_strip) return;

    s_current_state = state;

    switch (state) {
        case RGB_STATE_CONNECTING:
            if (s_blink_task) {
                xTaskNotifyGive(s_blink_task);
            }
            break;

        case RGB_STATE_FAILED:
            // Solid Red
            rgb_led_set_color(50, 0, 0);
            break;

        case RGB_STATE_CONNECTED:
            // Solid Green
            rgb_led_set_color(0, 50, 0);
            break;

        case RGB_STATE_OFF:
        default:
            rgb_led_set_color(0, 0, 0);
            break;
    }
}

