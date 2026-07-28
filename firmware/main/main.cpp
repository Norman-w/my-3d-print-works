#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "piezo_capture.h"
#include "config.h"
#include "const.h"
#include "wifi_manager.h"
#include "dns_server.h"
#include "web_server.h"
#include "esp_mac.h"
#include "status_led.h"
#include "power_control.h"
#include "ws_data_server.h"
#include "im948_sensor.h"
#include "im948_data.h"

static const char* TAG = LOG_TAG_MAIN;

// ===== 全局状态（供 wifi_manager / http handlers 访问） =====
extern "C" {
    char device_id[32] = {0};
    bool is_sta_connected = false;
    bool is_sta_connecting = false;
    bool is_connection_error = false;
}

static httpd_handle_t s_server = NULL;


// ===== 初始化顺序：外设 → WiFi → 网络服务 → 传感器 =====
static void init_peripherals(void) {
    // 默认设备 ID（基于 MAC 地址）
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    snprintf(device_id, sizeof(device_id), "SP-%02X%02X", mac[4], mac[5]);
    ESP_LOGI(TAG, "设备 ID: %s", device_id);

    // 状态 LED
    status_led::init();
    status_led::set_boot();

    // 用户键手势（关机 / 恢复出厂）已在 power_control_init 中启动
}

static void init_network(void) {
    // 初始化 TCP/IP 协议栈
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // 启动 SoftAP + 尝试连接已保存的 STA
    wifi_init_softap_and_sta();

    // DNS 劫持（Captive Portal）
    dns_server_start();

    // HTTP 服务器
    s_server = start_webserver();

    // WebSocket 数据推送
    ws_data_server_init();
}

// ===== IMU 初始化 =====
static void init_imu(void) {
    esp_err_t ret = Im948Sensor::init(IMU_UART_NUM, IMU_UART_TX, IMU_UART_RX,
                                      IMU_RX_BUF_SIZE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 Sensor 初始化失败: %d", ret);
        return;
    }

    ret = Im948Sensor::ensure_baud_115200();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "波特率探测失败，仍按 115200 继续（可断电重试）");
    }

    // 先停掉「传感器睡眠却仍上报」的空流，再确认真正唤醒
    (void)Im948Sensor::stop_streaming();
    vTaskDelay(pdMS_TO_TICKS(50));

    ret = Im948Sensor::ensure_sensor_on(6);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 传感器未能开启 — 请测 IMU VBUS(≈5V) 与半孔焊接");
        return;
    }

    ret = Im948Sensor::configure(
        Im948AccelRange::G16,
        Im948GyroRange::DPS2048,
        IMU_REPORT_HZ,
        IM948_TAGS_STREAM,
        0,
        0,
        9,
        false
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 配置失败: %d", ret);
        return;
    }

    // 配置后再次确认仍处于唤醒（防止被冲掉）
    if (Im948Sensor::refresh_status(400) != ESP_OK ||
        !Im948Sensor::is_sensor_on()) {
        ESP_LOGW(TAG, "配置后 sensor_on 丢失，再次唤醒");
        (void)Im948Sensor::ensure_sensor_on(3);
    }

    ret = Im948Sensor::start_streaming();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 主动上报启动失败: %d", ret);
        return;
    }

    Im948Sensor::request_hex_dumps(5);
    (void)Im948Sensor::refresh_status(400);
    vTaskDelay(pdMS_TO_TICKS(200));

    ESP_LOGI(TAG, "IM948 初始化完成，%dHz tags=0x%04X @115200 sensor_on=%d",
             IMU_REPORT_HZ, IM948_TAGS_STREAM,
             Im948Sensor::is_sensor_on() ? 1 : 0);
}

// ===== IMU 数据轮询任务（独立 FreeRTOS 任务） =====
static void imu_loop(void *arg) {
    ImuFrame frame;
    uint32_t ws_ok = 0;
    uint32_t ws_fail = 0;
    uint32_t poll_ok = 0;
    int64_t last_frame_us = esp_timer_get_time();
    int64_t last_idle_log_us = 0;
#if IMU_UART_REPORT_HZ > 0
    const int64_t report_us = 1000000 / IMU_UART_REPORT_HZ;
    int64_t last_report_us = 0;
#endif
    while (true) {
        if (Im948Sensor::poll(frame)) {
            ++poll_ok;
            last_frame_us = esp_timer_get_time();
            if (ws_data_has_client()) {
                if (ws_data_send_imu_frame(&frame) == ESP_OK) {
                    ++ws_ok;
                } else {
                    ++ws_fail;
                }
            }
#if IMU_UART_REPORT_HZ > 0
            const int64_t now = esp_timer_get_time();
            if (now - last_report_us >= report_us) {
                last_report_us = now;
                ESP_LOGI(TAG,
                         "IMU tags=0x%04X rpy=%.1f,%.1f,%.1f quat=%.3f,%.3f,%.3f,%.3f "
                         "gyro=%.1f,%.1f,%.1f ag=%.2f,%.2f,%.2f | poll=%lu ws_ok=%lu ws_fail=%lu client=%d",
                         frame.subscribe_tags,
                         frame.euler_roll, frame.euler_pitch, frame.euler_yaw,
                         frame.quat_w, frame.quat_x, frame.quat_y, frame.quat_z,
                         frame.gyro_x, frame.gyro_y, frame.gyro_z,
                         frame.accel_gx, frame.accel_gy, frame.accel_gz,
                         (unsigned long)poll_ok, (unsigned long)ws_ok,
                         (unsigned long)ws_fail, ws_data_has_client() ? 1 : 0);
                poll_ok = 0;
                ws_ok = 0;
                ws_fail = 0;
            }
#endif
        } else {
            const int64_t now = esp_timer_get_time();
            if (now - last_frame_us > 2000000 && now - last_idle_log_us > 2000000) {
                last_idle_log_us = now;
                ESP_LOGW(TAG, "IMU 超过 2s 无帧，重探波特率并重新配置开流");
                (void)Im948Sensor::ensure_baud_115200();
                (void)Im948Sensor::stop_streaming();
                (void)Im948Sensor::ensure_sensor_on(3);
                (void)Im948Sensor::configure(
                    Im948AccelRange::G16, Im948GyroRange::DPS2048,
                    IMU_REPORT_HZ, IM948_TAGS_STREAM, 0, 0, 9, false);
                (void)Im948Sensor::start_streaming();
                (void)Im948Sensor::refresh_status(400);
                last_frame_us = now;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ===== 主入口 =====
extern "C" void app_main() {
    // 0. 电源自锁必须最先拉高（松手尾键前完成）
    ESP_ERROR_CHECK(power_control_init());

    // 1. NVS 初始化
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    ESP_LOGI(TAG, "SmartPaddle 固件启动");
    ESP_LOGI(TAG, "压电: 4 通道 GPIO ISR + CPU cycle TDOA");

    // 2. 外设初始化（LED；用户键已在 power_control_init）
    init_peripherals();

    // 3. 网络初始化（WiFi AP → DNS → HTTP → WebSocket）
    init_network();

    // 4. IMU 初始化（IM948 传感器）
#if SKIP_IMU_INIT
    ESP_LOGW(TAG, "SKIP_IMU_INIT=1：跳过 IM948 / UART1(GPIO23/22)，仅验证是否还 POWERON 循环");
#else
    init_imu();
#endif

    // 5. 压电传感器初始化（失败不阻断 IMU/网络）
    bool piezo_ok = false;
    ret = PiezoCapture::init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PiezoCapture 初始化失败: %d（继续运行 IMU）", ret);
    } else {
        piezo_ok = true;
    }

    ESP_LOGI(TAG, "等待击球事件... 连接到 SmartPaddle WiFi 或通过 IP 访问");

#if !SKIP_IMU_INIT
    // 6. 启动 IMU 轮询任务（高优先级、绑定核心 0）
    xTaskCreatePinnedToCore(imu_loop, "imu_task", 4096, nullptr, 10, nullptr, 0);
#endif

    // 7. 主循环：采集压电事件 + WebSocket 推送
    while (true) {
        if (!piezo_ok) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        PiezoEvent first;
        ret = PiezoCapture::wait_for_impact(first, portMAX_DELAY);
        if (ret != ESP_OK) continue;

        // 10ms 窗口收集所有相关事件
        uint64_t window_start = first.timestamp_us;
        uint64_t window_end = window_start + 10000;
        uint64_t cycles_base = first.timestamp_cycles;

        PiezoEvent batch[16];
        size_t count = 1;
        batch[0] = first;

        // 短暂等待其余通道首边沿到达再 drain
        vTaskDelay(pdMS_TO_TICKS(10));

        PiezoEvent pending[16];
        size_t pending_count = PiezoCapture::drain_events(pending, 16);
        for (size_t i = 0; i < pending_count && count < 16; i++) {
            if (pending[i].timestamp_us <= window_end) {
                batch[count++] = pending[i];
            }
        }

        // 串口输出 TDOA 数据（相对 ns 来自 CPU cycle）
        printf("=== IMPACT === ts_base=%" PRIu64 "\n", window_start);
        for (size_t i = 0; i < count; i++) {
            printf("  ch%" PRIu32 ": ts=%" PRIu64 " (+%" PRId64 " ns) edges=%" PRIu32 "\n",
                batch[i].channel,
                batch[i].timestamp_us,
                PiezoCapture::delta_ns(batch[i].timestamp_cycles, cycles_base),
                batch[i].edge_count);
        }

        if (count >= 2) {
            printf("  TDOA (ns):");
            for (size_t i = 1; i < count; i++) {
                if (batch[i].channel != batch[0].channel) {
                    printf(" ch%" PRIu32 "=%+" PRId64, batch[i].channel,
                           PiezoCapture::delta_ns(batch[i].timestamp_cycles,
                                                  batch[0].timestamp_cycles));
                }
            }
            printf("\n");
        }

        // WebSocket 推送（如果有客户端连接）
        if (ws_data_has_client()) {
            status_led::notify_data_activity(300);
            char json_buf[256];
            snprintf(json_buf, sizeof(json_buf),
                "{\"type\":\"impact\",\"ts_base\":%" PRIu64 ",\"channels\":%zu}",
                window_start, count);
            ws_data_send_text(json_buf, strlen(json_buf));
        }

        PiezoCapture::start_capture();
    }
}
