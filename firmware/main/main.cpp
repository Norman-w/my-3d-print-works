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
#include "reset_button.h"
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

    // Reset 按钮
    reset_button_init();
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

    // 唤醒传感器（发送 Cmd_03 后等待 3 秒）
    ret = Im948Sensor::wake();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 唤醒失败: %d", ret);
        return;
    }

    // 配置传感器参数
    ret = Im948Sensor::configure(
        Im948AccelRange::G16,
        Im948GyroRange::DPS2048,
        IMU_REPORT_HZ,
        Im948ReportTag::TAG_ALL,
        0,   // gyro_filter=0: 最小滤波
        0,   // accel_filter=0: 最小滤波
        9,   // compass_filter=9: 默认
        false // 不融合磁场
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 配置失败: %d", ret);
        return;
    }

    // 升级波特率：115200 → 230400
    ret = Im948Sensor::upgrade_baudrate(Im948BaudRate::B230400);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "IM948 波特率升级失败，继续使用 115200");
    }

    // 开启主动上报
    ret = Im948Sensor::start_streaming();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IM948 主动上报启动失败: %d", ret);
        return;
    }

    ESP_LOGI(TAG, "IM948 初始化完成，%dHz 主动上报中", IMU_REPORT_HZ);
}

// ===== IMU 数据轮询任务（独立 FreeRTOS 任务） =====
static void imu_loop(void *arg) {
    ImuFrame frame;
    while (true) {
        if (Im948Sensor::poll(frame)) {
            if (ws_data_has_client()) {
                ws_data_send_imu_frame(&frame);
            }
        }
        // 适当让出 CPU，避免 busy-wait 饿死压电任务
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ===== 主入口 =====
extern "C" void app_main() {
    // 1. NVS 初始化
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    ESP_LOGI(TAG, "SmartPaddle 固件启动");
    ESP_LOGI(TAG, "RMT 分辨率: 12.5ns @ 80MHz APB");

    // 2. 外设初始化（LED、Reset 按钮）
    init_peripherals();

    // 3. 网络初始化（WiFi AP → DNS → HTTP → WebSocket）
    init_network();

    // 4. IMU 初始化（IM948 传感器）
    init_imu();

    // 5. 压电传感器初始化
    ret = PiezoCapture::init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PiezoCapture 初始化失败: %d", ret);
        return;
    }

    ESP_LOGI(TAG, "等待击球事件... 连接到 SmartPaddle WiFi 或通过 IP 访问");

    // 6. 启动 IMU 轮询任务（高优先级、绑定核心 0）
    xTaskCreatePinnedToCore(imu_loop, "imu_task", 4096, nullptr, 10, nullptr, 0);

    // 7. 主循环：采集压电事件 + WebSocket 推送
    while (true) {
        PiezoEvent first;
        ret = PiezoCapture::wait_for_impact(first, portMAX_DELAY);
        if (ret != ESP_OK) continue;

        // 10ms 窗口收集所有相关事件
        uint64_t window_start = first.timestamp_us;
        uint64_t window_end = window_start + 10000;

        PiezoEvent batch[16];
        size_t count = 1;
        batch[0] = first;

        PiezoEvent pending[16];
        size_t pending_count = PiezoCapture::drain_events(pending, 16);
        for (size_t i = 0; i < pending_count && count < 16; i++) {
            if (pending[i].timestamp_us <= window_end) {
                batch[count++] = pending[i];
            }
        }

        // 串口输出 TDOA 数据
        printf("=== IMPACT === ts_base=%" PRIu64 "\n", window_start);
        for (size_t i = 0; i < count; i++) {
            printf("  ch%" PRIu32 ": ts=%" PRIu64 " (+%" PRIu64 " ns) edges=%" PRIu32 "\n",
                batch[i].channel,
                batch[i].timestamp_us,
                (batch[i].timestamp_us - window_start) * 1000,
                batch[i].edge_count);
        }

        if (count >= 2) {
            printf("  TDOA (ns):");
            for (size_t i = 1; i < count; i++) {
                int64_t diff = (int64_t)(batch[i].timestamp_us - batch[0].timestamp_us) * 1000;
                if (batch[i].channel != batch[0].channel) {
                    printf(" ch%" PRIu32 "=%+" PRId64, batch[i].channel, diff);
                }
            }
            printf("\n");
        }

        // WebSocket 推送（如果有客户端连接）
        if (ws_data_has_client()) {
            status_led::notify_data_activity(300);
            // TODO: Phase 1 定义具体的二进制帧格式
            // 当前先推送简单的冲击事件通知
            char json_buf[256];
            snprintf(json_buf, sizeof(json_buf),
                "{\"type\":\"impact\",\"ts_base\":%" PRIu64 ",\"channels\":%zu}",
                window_start, count);
            ws_data_send_text(json_buf, strlen(json_buf));
        }

        // 重新启动采集
        PiezoCapture::start_capture();
    }
}
