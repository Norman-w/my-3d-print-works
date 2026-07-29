file(GLOB html_files "web/*.html")

idf_component_register(
    SRCS
        "main.cpp"
        "piezo_capture.cpp"
        "utils.cpp"
        "device_storage.cpp"
        "dns_server.cpp"
        "wifi_manager.cpp"
        "web_server.cpp"
        "http.cpp"
        "status_led.cpp"
        "power_control.cpp"
        "ws_data_server.cpp"
        "im948_sdk.cpp"
        "im948_sensor.cpp"
        "http/connection_api_handlers.cpp"
        "http/connection_page_handlers.cpp"
    INCLUDE_DIRS
        "."
        "http"
    EMBED_TXTFILES ${html_files}
    REQUIRES
        driver
        nvs_flash
        esp_timer
        esp_wifi
        esp_http_server
        esp_netif
        esp_event
        esp_adc
        mdns
        led_strip
)
