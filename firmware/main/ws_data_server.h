#ifndef WS_DATA_SERVER_H
#define WS_DATA_SERVER_H

#include "esp_http_server.h"
#include "esp_err.h"
#include <cstdint>
#include <cstddef>
#include "im948_data.h"

#ifdef __cplusplus
extern "C" {
#endif

// WebSocket 数据推送初始化
esp_err_t ws_data_server_init(void);

// WebSocket 事件处理函数
esp_err_t ws_data_handler_fn(httpd_req_t *req);

// 向已连接的 WebSocket 客户端推送二进制数据
esp_err_t ws_data_send_binary(const uint8_t *data, size_t len);

// 向已连接的 WebSocket 客户端推送文本数据
esp_err_t ws_data_send_text(const char *data, size_t len);

// 注册 WebSocket URI 处理器
esp_err_t register_ws_data_handler(httpd_handle_t server);

// 检查是否有客户端连接
bool ws_data_has_client(void);

// 推送 IMU 数据帧（紧凑二进制格式）
esp_err_t ws_data_send_imu_frame(const ImuFrame *frame);

#ifdef __cplusplus
}
#endif

#endif // WS_DATA_SERVER_H
