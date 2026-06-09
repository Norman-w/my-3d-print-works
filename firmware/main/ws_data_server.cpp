#include "ws_data_server.h"
#include "const.h"
#include "esp_log.h"
#include "esp_timer.h"
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

// ===== 二进制帧构建辅助宏 =====

#define IMU_FRAME_MAX_SIZE 256  // 16 字节头 + 最多约 120 字节 float 数据

// 大端序写入辅助函数
static inline void write_be16(uint8_t *buf, uint16_t val) {
    buf[0] = (val >> 8) & 0xFF;
    buf[1] = val & 0xFF;
}
static inline void write_be32(uint8_t *buf, uint32_t val) {
    buf[0] = (val >> 24) & 0xFF;
    buf[1] = (val >> 16) & 0xFF;
    buf[2] = (val >> 8) & 0xFF;
    buf[3] = val & 0xFF;
}
static inline void write_be64(uint8_t *buf, uint64_t val) {
    buf[0] = (val >> 56) & 0xFF;
    buf[1] = (val >> 48) & 0xFF;
    buf[2] = (val >> 40) & 0xFF;
    buf[3] = (val >> 32) & 0xFF;
    buf[4] = (val >> 24) & 0xFF;
    buf[5] = (val >> 16) & 0xFF;
    buf[6] = (val >> 8) & 0xFF;
    buf[7] = val & 0xFF;
}

esp_err_t ws_data_send_imu_frame(const ImuFrame *frame) {
    if (!frame || !frame->is_valid) return ESP_ERR_INVALID_ARG;
    if (s_client_fd < 0 || !s_server_handle) return ESP_ERR_INVALID_ARG;

    uint8_t buf[IMU_FRAME_MAX_SIZE] = {};
    size_t pos = 0;

    // Byte 0: 帧类型
    buf[pos++] = 'I';

    // Byte 1-4: timestamp_ms (uint32_t, big-endian)
    write_be32(&buf[pos], frame->timestamp_ms);
    pos += 4;

    // Byte 5-12: esp_timestamp_us (uint64_t, big-endian)
    write_be64(&buf[pos], esp_timer_get_time());
    pos += 8;

    // Byte 13-14: subscribe_tags (uint16_t, big-endian)
    write_be16(&buf[pos], frame->subscribe_tags);
    pos += 2;

    // Byte 15: 标志位
    uint8_t flags = 0x01;  // bit0=1: 有效数据
    buf[pos++] = flags;

    // Byte 16+: 按 tag 位序排列的 float 数组

    if (frame->subscribe_tags & TAG_ACCEL_NO_GRAVITY) {
        memcpy(&buf[pos], &frame->accel_lx, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_ly, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_lz, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_ACCEL_WITH_GRAVITY) {
        memcpy(&buf[pos], &frame->accel_gx, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_gy, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_gz, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_ANGULAR_VELOCITY) {
        memcpy(&buf[pos], &frame->gyro_x, 4); pos += 4;
        memcpy(&buf[pos], &frame->gyro_y, 4); pos += 4;
        memcpy(&buf[pos], &frame->gyro_z, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_MAGNETIC) {
        memcpy(&buf[pos], &frame->mag_x, 4); pos += 4;
        memcpy(&buf[pos], &frame->mag_y, 4); pos += 4;
        memcpy(&buf[pos], &frame->mag_z, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_TEMP_PRESSURE_HEIGHT) {
        memcpy(&buf[pos], &frame->temperature, 4); pos += 4;
        memcpy(&buf[pos], &frame->air_pressure, 4); pos += 4;
        memcpy(&buf[pos], &frame->height, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_QUATERNION) {
        memcpy(&buf[pos], &frame->quat_w, 4); pos += 4;
        memcpy(&buf[pos], &frame->quat_x, 4); pos += 4;
        memcpy(&buf[pos], &frame->quat_y, 4); pos += 4;
        memcpy(&buf[pos], &frame->quat_z, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_EULER_ANGLES) {
        memcpy(&buf[pos], &frame->euler_roll, 4); pos += 4;
        memcpy(&buf[pos], &frame->euler_pitch, 4); pos += 4;
        memcpy(&buf[pos], &frame->euler_yaw, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_DISPLACEMENT) {
        memcpy(&buf[pos], &frame->offset_x, 4); pos += 4;
        memcpy(&buf[pos], &frame->offset_y, 4); pos += 4;
        memcpy(&buf[pos], &frame->offset_z, 4); pos += 4;
    }
    if (frame->subscribe_tags & TAG_ACCEL_NAV_FRAME) {
        memcpy(&buf[pos], &frame->accel_nav_x, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_nav_y, 4); pos += 4;
        memcpy(&buf[pos], &frame->accel_nav_z, 4); pos += 4;
    }

    return ws_data_send_binary(buf, pos);
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
