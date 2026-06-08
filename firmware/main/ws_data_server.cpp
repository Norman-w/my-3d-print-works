#include "ws_data_server.h"
#include "const.h"
#include "esp_log.h"
#include <cstring>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = LOG_TAG_WS_DATA_SERVER;

// WebSocket 客户端状态（单用户模式）
static int s_client_fd = -1;
static httpd_handle_t s_server_handle = NULL;

// 关闭旧的 WebSocket 连接（单用户模式）
static void close_existing_connection(void) {
    if (s_client_fd >= 0 && s_server_handle) {
        ESP_LOGI(TAG, "关闭旧的 WebSocket 连接: fd=%d", s_client_fd);
        httpd_sess_trigger_close(s_server_handle, s_client_fd);
        s_client_fd = -1;
        s_server_handle = NULL;
    }
}

esp_err_t ws_data_handler_fn(httpd_req_t *req) {
    if (req->method == HTTP_GET) {
        // WebSocket 握手
        close_existing_connection();

        s_server_handle = req->handle;
        s_client_fd = httpd_req_to_sockfd(req);

        ESP_LOGI(TAG, "WebSocket 客户端已连接: fd=%d", s_client_fd);

        // WebSocket 握手完成即返回，后续直接通过 ws_data_send_* 推送数据
        return ESP_OK;
    }

    // 不处理从客户端接收的数据（单向推送模式）
    return ESP_OK;
}

esp_err_t ws_data_server_init(void) {
    ESP_LOGI(TAG, "WebSocket 数据推送服务已初始化");
    return ESP_OK;
}

esp_err_t ws_data_send_binary(const uint8_t *data, size_t len) {
    if (!data || len == 0 || s_client_fd < 0 || !s_server_handle) {
        return ESP_ERR_INVALID_ARG;
    }

    httpd_ws_frame_t ws_pkt = {};
    ws_pkt.payload = (uint8_t *)data;
    ws_pkt.len = len;
    ws_pkt.type = HTTPD_WS_TYPE_BINARY;

    return httpd_ws_send_frame_async(s_server_handle, s_client_fd, &ws_pkt);
}

esp_err_t ws_data_send_text(const char *data, size_t len) {
    if (!data || len == 0 || s_client_fd < 0 || !s_server_handle) {
        return ESP_ERR_INVALID_ARG;
    }

    httpd_ws_frame_t ws_pkt = {};
    ws_pkt.payload = (uint8_t *)data;
    ws_pkt.len = len;
    ws_pkt.type = HTTPD_WS_TYPE_TEXT;

    return httpd_ws_send_frame_async(s_server_handle, s_client_fd, &ws_pkt);
}

bool ws_data_has_client(void) {
    return s_client_fd >= 0;
}

static const httpd_uri_t ws_data_uri = {
    .uri = "/ws",
    .method = HTTP_GET,
    .handler = ws_data_handler_fn,
    .user_ctx = nullptr,
    .is_websocket = true,
};

esp_err_t register_ws_data_handler(httpd_handle_t server) {
    httpd_register_uri_handler(server, &ws_data_uri);
    ESP_LOGI(TAG, "WebSocket /ws 端点已注册");
    return ESP_OK;
}
