#ifndef WIFI_UDP_H
#define WIFI_UDP_H

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// Initialize Wi-Fi in Station mode
esp_err_t wifi_init_sta(void);

// Start FreeRTOS UDP server task to receive input packets
esp_err_t start_udp_server(void);

// Check if Wi-Fi has acquired an IP address
bool wifi_is_connected(void);

#ifdef __cplusplus
}
#endif

#endif // WIFI_UDP_H

