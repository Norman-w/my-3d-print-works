#pragma once

#include "im948_data.h"
#include "driver/uart.h"
#include "esp_err.h"

// ===== 分区：公开 API =====

/**
 * IM948 传感器业务封装。
 * 使用方式：init() → wait 3s → wake() → configure() → start_streaming()
 *           然后在 FreeRTOS 任务中调用 poll() 获取数据。
 */
class Im948Sensor {
public:
    // ---- 生命周期 ----

    /**
     * 初始化 UART 驱动并注册数据回调
     * @param uart_num    UART 端口号
     * @param tx_pin      TX 引脚
     * @param rx_pin      RX 引脚
     * @param rx_buf_size 接收缓冲区大小
     * @return ESP_OK 成功
     */
    static esp_err_t init(uart_port_t uart_num, int tx_pin, int rx_pin,
                          int rx_buf_size = 4096);

    /**
     * 唤醒传感器（发送 Cmd_03）
     * 调用后请等待 3000ms 让模块稳定上电
     * @return ESP_OK 成功
     */
    static esp_err_t wake();

    // ---- 配置 ----

    /**
     * 一站式配置工作参数
     * @param accel_range    加速度量程
     * @param gyro_range     陀螺仪量程
     * @param report_hz      主动上报频率 (0-250, 0=0.5Hz)
     * @param subscribe_tags  订阅字段位掩码
     * @param gyro_filter    陀螺仪滤波 (0-2, 0=最快)
     * @param accel_filter   加速度滤波 (0-4, 0=最快)
     * @param compass_filter 磁力计滤波 (0-9)
     * @param enable_compass 是否融合磁场
     * @return ESP_OK 成功
     */
    static esp_err_t configure(
        Im948AccelRange accel_range   = Im948AccelRange::G16,
        Im948GyroRange gyro_range     = Im948GyroRange::DPS2048,
        uint8_t report_hz            = 250,
        uint16_t subscribe_tags      = Im948ReportTag::TAG_ALL,
        uint8_t gyro_filter          = 0,
        uint8_t accel_filter         = 0,
        uint8_t compass_filter       = 9,
        bool enable_compass          = false);

    /**
     * 升级波特率（同时设置 IM948 模块和 ESP32 UART）
     * @param target 目标波特率
     * @return ESP_OK 成功
     */
    static esp_err_t upgrade_baudrate(Im948BaudRate target = Im948BaudRate::B230400);

    // ---- 数据流 ----

    /**
     * 开启主动上报
     * @return ESP_OK 成功
     */
    static esp_err_t start_streaming();

    /**
     * 关闭主动上报
     * @return ESP_OK 成功
     */
    static esp_err_t stop_streaming();

    /**
     * 轮询最新数据帧。非阻塞，有新数据时填充 frame 并返回 true。
     * @param frame 输出参数，填充最新数据
     * @return true 有新数据, false 无新数据
     */
    static bool poll(ImuFrame &frame);

    // ---- 校准 ----

    /**
     * 加速计简易校准（模块需置于水平面，等待 9 秒）
     * @return ESP_OK 成功
     */
    static esp_err_t calibrate_accel_simple();

    /**
     * Z 轴角度归零
     * @return ESP_OK 成功
     */
    static esp_err_t set_zero_orientation();

    // ---- 查询 ----

    /**
     * 获取当前加速度量程对应的比例因子
     */
    static float accel_scale(Im948AccelRange range);

    /**
     * 获取当前陀螺仪量程对应的比例因子
     */
    static float gyro_scale(Im948GyroRange range);

private:
    // ---- 内部 ----

    static void on_rx_unpack(const uint8_t *data, uint8_t len);

    // 当前量程
    static Im948AccelRange s_accel_range;
    static Im948GyroRange s_gyro_range;

    // 最新解析帧
    static ImuFrame s_latest_frame;
    static volatile bool s_has_new_data;

    // UART 端口
    static uart_port_t s_uart_num;
};
