#include "wifi_udp.h"
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "protocol.h"
#include "usb_hid.h"
#include "rgb_led.h"
#include "wifi_config.h"
#include "esp_system.h"
#include "soc/rtc_cntl_reg.h"

static const char *TAG = "wifi_udp";

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static EventGroupHandle_t s_wifi_event_group;
static int s_retry_num = 0;
static const int MAXIMUM_RETRY = 5;
static bool s_is_connected = false;

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        rgb_led_set_state(RGB_STATE_CONNECTING);
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        s_is_connected = false;
        if (s_retry_num < MAXIMUM_RETRY) {
            rgb_led_set_state(RGB_STATE_CONNECTING);
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retrying Wi-Fi connection (%d/%d)...", s_retry_num, MAXIMUM_RETRY);
        } else {
            // Maximum retries reached -> Signal Failed (Solid Red)
            rgb_led_set_state(RGB_STATE_FAILED);
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGW(TAG, "Failed to connect to Wi-Fi. Retrying in 5 seconds...");
            vTaskDelay(pdMS_TO_TICKS(5000));
            s_retry_num = 0;
            esp_wifi_connect();
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Wi-Fi Connected! IP Address: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        s_is_connected = true;
        // Connected -> Signal Green
        rgb_led_set_state(RGB_STATE_CONNECTED);
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

esp_err_t wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_WIFI_SSID,
            .password = CONFIG_WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE)); // Ultra-low latency mode (1ms)

    ESP_LOGI(TAG, "Wi-Fi STA started (PS_NONE). Target SSID: '%s'", CONFIG_WIFI_SSID);
    return ESP_OK;
}

bool wifi_is_connected(void)
{
    return s_is_connected;
}

static void udp_server_task(void *pvParameters)
{
    uint8_t rx_buffer[128];
    struct sockaddr_in server_addr;
    struct sockaddr_in source_addr;
    socklen_t socklen = sizeof(source_addr);

    // Wait until Wi-Fi is connected
    xEventGroupWaitBits(s_wifi_event_group,
                        WIFI_CONNECTED_BIT,
                        pdFALSE,
                        pdTRUE,
                        portMAX_DELAY);

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGE(TAG, "Unable to create UDP socket: errno %d", errno);
        vTaskDelete(NULL);
        return;
    }

    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(CONFIG_UDP_SERVER_PORT);

    int err = bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr));
    if (err < 0) {
        ESP_LOGE(TAG, "Socket unable to bind to port %d: errno %d", CONFIG_UDP_SERVER_PORT, errno);
        close(sock);
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "UDP listener started on port %d", CONFIG_UDP_SERVER_PORT);

    while (1) {
        int len = recvfrom(sock, rx_buffer, sizeof(rx_buffer), 0,
                           (struct sockaddr *)&source_addr, &socklen);

        if (len < 0) {
            ESP_LOGE(TAG, "recvfrom failed: errno %d", errno);
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        if (len == 0) {
            continue;
        }

        uint8_t cmd = rx_buffer[0];

        switch (cmd) {
            case CMD_MOUSE_MOVE: {
                if (len >= sizeof(packet_mouse_move_t)) {
                    packet_mouse_move_t *pkt = (packet_mouse_move_t *)rx_buffer;
                    usb_hid_mouse_move(pkt->dx, pkt->dy);
                }
                break;
            }

            case CMD_MOUSE_CLICK: {
                if (len >= sizeof(packet_mouse_click_t)) {
                    packet_mouse_click_t *pkt = (packet_mouse_click_t *)rx_buffer;
                    usb_hid_mouse_click(pkt->button, pkt->pressed);
                }
                break;
            }

            case CMD_MOUSE_SCROLL: {
                if (len >= sizeof(packet_mouse_scroll_t)) {
                    packet_mouse_scroll_t *pkt = (packet_mouse_scroll_t *)rx_buffer;
                    usb_hid_mouse_scroll(pkt->delta);
                }
                break;
            }

            case CMD_KEY_PRESS: {
                if (len >= sizeof(packet_key_press_t)) {
                    packet_key_press_t *pkt = (packet_key_press_t *)rx_buffer;
                    usb_hid_keyboard_press(pkt->keycode, pkt->modifiers);
                }
                break;
            }

            case CMD_KEY_RELEASE: {
                if (len >= sizeof(packet_key_release_t)) {
                    packet_key_release_t *pkt = (packet_key_release_t *)rx_buffer;
                    usb_hid_keyboard_release(pkt->keycode);
                }
                break;
            }

            case CMD_ACTIVE: {
                // Active mode: Cyan color indicating PC B control is active
                rgb_led_set_color(0, 40, 50);
                ESP_LOGI(TAG, "Active Mode: ON (controlling Laptop B)");
                break;
            }

            case CMD_INACTIVE: {
                // Inactive mode: Return to Solid Green (connected)
                rgb_led_set_state(RGB_STATE_CONNECTED);
                usb_hid_release_all();
                ESP_LOGI(TAG, "Active Mode: OFF (released all keys/mouse)");
                break;
            }

            case CMD_REBOOT_BOOTLOADER: {
                ESP_LOGI(TAG, "Remote reboot command received! Entering ROM Download Mode...");
                REG_WRITE(RTC_CNTL_OPTION1_REG, RTC_CNTL_FORCE_DOWNLOAD_BOOT);
                esp_restart();
                break;
            }

            default:
                ESP_LOGW(TAG, "Unknown command received: 0x%02X", cmd);
                break;
        }
    }

    if (sock != -1) {
        close(sock);
    }
    vTaskDelete(NULL);
}

esp_err_t start_udp_server(void)
{
    BaseType_t ret = xTaskCreatePinnedToCore(
        udp_server_task,
        "udp_server",
        4096,
        NULL,
        configMAX_PRIORITIES - 2, // High priority for low latency
        NULL,
        1                          // Core 1
    );

    return (ret == pdPASS) ? ESP_OK : ESP_FAIL;
}
