#include "web_server.h"
#include "esp_log.h"
// #include "http_handlers.h" // For http_handlers_register
#include "http.h"

static const char *TAG = "web_server";

httpd_handle_t start_webserver(void)
{
    httpd_handle_t server = NULL;
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.uri_match_fn = httpd_uri_match_wildcard;
    config.max_uri_handlers = 16;
    config.lru_purge_enable = true;
    config.keep_alive_enable = true;

    ESP_LOGI(TAG, "启动Web服务器...");
    if (httpd_start(&server, &config) == ESP_OK) {
        ESP_LOGI(TAG, "注册URI处理器...");
        register_all_http_handlers(server);
    } else {
        ESP_LOGE(TAG, "启动Web服务器失败");
    }
    return server;
}

void stop_webserver(httpd_handle_t server)
{
    if (server) {
        httpd_stop(server);
    }
} 