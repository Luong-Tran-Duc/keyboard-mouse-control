idf_component_register(
    SRCS 
        "main.c" 
        "usb_hid.c" 
        "wifi_udp.c"
        "rgb_led.c"
    INCLUDE_DIRS "."
    REQUIRES 
        esp_tinyusb 
        esp_wifi 
        esp_event 
        nvs_flash 
        esp_driver_gpio 
        lwip
        led_strip
)
