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

    // 注册配网页面处理器 (通配符 "/*", 放在 API 之后)
    ret = register_connection_page_handlers(server);
    if (ret != ESP_OK) return ret;

    // 注册 WebSocket 数据推送端点 (/ws)
    ret = register_ws_data_handler(server);
    if (ret != ESP_OK) return ret;

    return ret;
}
