//
// HTTP 路由聚合 — SmartPaddle
//

#include "http.h"
#include "esp_err.h"
#include "esp_http_server.h"
#include "http/connection_api_handlers.h"
#include "http/connection_page_handlers.h"
#include "ws_data_server.h"


esp_err_t register_all_http_handlers(httpd_handle_t server) {
    esp_err_t ret = ESP_OK;

    // 注册连接 API (/login, /status, /dhcp_status, /try_connect_to_ap, /sta_result_checking_page_loaded)
    ret = register_connection_api_handlers(server);
    if (ret != ESP_OK) return ret;

    // /ws 必须在通配符 "/*" 之前注册，否则会被 captive portal 抢走
    ret = register_ws_data_handler(server);
    if (ret != ESP_OK) return ret;

    // 配网页通配符（业务 UI 在专用端，不烧进 ESP）
    ret = register_connection_page_handlers(server);
    if (ret != ESP_OK) return ret;

    return ret;
}
