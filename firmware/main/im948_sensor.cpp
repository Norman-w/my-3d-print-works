#include "im948_sensor.h"
#include "im948_sdk.h"
#include "const.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cmath>
#include <cstring>

// ===== 分区：常量/配置 =====

static const char *TAG = "im948_sensor";

// ===== 分区：私有成员 =====

Im948AccelRange Im948Sensor::s_accel_range = Im948AccelRange::G16;
Im948GyroRange  Im948Sensor::s_gyro_range  = Im948GyroRange::DPS2048;
ImuFrame        Im948Sensor::s_latest_frame = {};
volatile bool   Im948Sensor::s_has_new_data = false;
uart_port_t     Im948Sensor::s_uart_num     = UART_NUM_MAX;

// pow2 辅助宏
#define pow2(x) ((x)*(x))

// ===== 分区：公开 API =====

esp_err_t Im948Sensor::init(uart_port_t uart_num, int tx_pin, int rx_pin,
                            int rx_buf_size) {
    s_uart_num = uart_num;

    esp_err_t ret = im948_uart_init(uart_num, tx_pin, rx_pin,
                                    115200, rx_buf_size);
    if (ret != ESP_OK) return ret;

    // 注册数据包回调
    im948_set_rx_callback(on_rx_unpack);
    im948_set_device_address(255);  // 广播模式

    ESP_LOGI(TAG, "IM948 传感器层初始化完成");
    return ESP_OK;
}

esp_err_t Im948Sensor::wake() {
    uint8_t cmd = 0x03;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "唤醒命令发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "唤醒命令已发送，等待 3s 稳定...");
    vTaskDelay(pdMS_TO_TICKS(3000));
    return ESP_OK;
}

esp_err_t Im948Sensor::configure(
    Im948AccelRange accel_range, Im948GyroRange gyro_range,
    uint8_t report_hz, uint16_t subscribe_tags,
    uint8_t gyro_filter, uint8_t accel_filter, uint8_t compass_filter,
    bool enable_compass) {

    s_accel_range = accel_range;
    s_gyro_range  = gyro_range;

    // Cmd_12: 设置设备参数
    {
        uint8_t buf[11] = {};
        buf[0] = 0x12;
        buf[1] = 5;              // accStill: 5 dm/s^2
        buf[2] = 255;            // stillToZero: 立即归零
        buf[3] = 0;              // moveToZero: 不归零
        buf[4] = ((compass_filter & 3) << 1) | (enable_compass ? 1 : 0);
        buf[5] = report_hz;
        buf[6] = gyro_filter;
        buf[7] = accel_filter;
        buf[8] = compass_filter;
        buf[9] = subscribe_tags & 0xFF;
        buf[10] = (subscribe_tags >> 8) & 0xFF;

        if (im948_pack_and_tx(buf, 11) != 0) {
            ESP_LOGE(TAG, "Cmd_12 发送失败");
            return ESP_FAIL;
        }
    }

    vTaskDelay(pdMS_TO_TICKS(100));

    // Cmd_33: 设置加速度和陀螺仪量程
    {
        uint8_t buf[3] = {};
        buf[0] = 0x33;
        buf[1] = static_cast<uint8_t>(accel_range);
        buf[2] = static_cast<uint8_t>(gyro_range);

        if (im948_pack_and_tx(buf, 3) != 0) {
            ESP_LOGE(TAG, "Cmd_33 发送失败");
            return ESP_FAIL;
        }
    }

    vTaskDelay(pdMS_TO_TICKS(100));

    // Cmd_40: 开机后自动载入配置并主动上报
    {
        uint8_t buf[2] = {};
        buf[0] = 0x40;
        buf[1] = 2;  // 载入配置 + 自动开启主动上报

        im948_pack_and_tx(buf, 2);
    }

    ESP_LOGI(TAG, "配置完成: accel=%d gyro=%d hz=%d tags=0x%04X",
             static_cast<int>(accel_range), static_cast<int>(gyro_range),
             report_hz, subscribe_tags);
    return ESP_OK;
}

esp_err_t Im948Sensor::upgrade_baudrate(Im948BaudRate target) {
    // 1. 发送 Cmd_47 让 IM948 切换到目标波特率
    {
        uint8_t buf[2] = {};
        buf[0] = 0x47;
        buf[1] = static_cast<uint8_t>(target);

        if (im948_pack_and_tx(buf, 2) != 0) {
            ESP_LOGE(TAG, "Cmd_47 发送失败");
            return ESP_FAIL;
        }
    }

    // 2. 等待 IM948 处理
    vTaskDelay(pdMS_TO_TICKS(200));

    // 3. 切换 ESP32 UART 波特率
    int target_baud = 115200;
    switch (target) {
        case Im948BaudRate::B9600:   target_baud = 9600;   break;
        case Im948BaudRate::B115200: target_baud = 115200; break;
        case Im948BaudRate::B230400: target_baud = 230400; break;
        case Im948BaudRate::B460800: target_baud = 460800; break;
    }

    return im948_uart_set_baudrate(target_baud);
}

esp_err_t Im948Sensor::start_streaming() {
    uint8_t cmd = 0x19;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "Cmd_19 发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "主动上报已开启");
    return ESP_OK;
}

esp_err_t Im948Sensor::stop_streaming() {
    uint8_t cmd = 0x18;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "Cmd_18 发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "主动上报已关闭");
    return ESP_OK;
}

bool Im948Sensor::poll(ImuFrame &frame) {
    if (!s_has_new_data) {
        return false;
    }

    // 拷贝最新帧（临界区）
    taskDISABLE_INTERRUPTS();
    frame = s_latest_frame;
    s_has_new_data = false;
    taskENABLE_INTERRUPTS();

    return true;
}

esp_err_t Im948Sensor::calibrate_accel_simple() {
    uint8_t cmd = 0x07;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "加速计校准命令发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "加速计简易校准已启动，请保持模块静止 9 秒");
    return ESP_OK;
}

esp_err_t Im948Sensor::set_zero_orientation() {
    uint8_t cmd = 0x05;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "Z轴归零命令发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "Z轴角度已归零");
    return ESP_OK;
}

float Im948Sensor::accel_scale(Im948AccelRange range) {
    // 当前固定 16g 量程
    return IM948_SCALE_ACCEL;
}

float Im948Sensor::gyro_scale(Im948GyroRange range) {
    // 当前固定 2000dps 量程
    return IM948_SCALE_ANGLE_SPEED;
}

// ===== 分区：业务逻辑 =====

void Im948Sensor::on_rx_unpack(const uint8_t *buf, uint8_t dlen) {
    if (dlen == 0) return;

    switch (buf[0]) {
    case 0x10:  // 模块属性和状态（收到回复，不处理数据，仅日志）
        ESP_LOGI(TAG, "收到设备属性和状态");
        break;

    case 0x11: {  // 订阅数据包
        uint16_t ctl = ((uint16_t)buf[2] << 8) | buf[1];
        uint32_t ts_ms = ((uint32_t)buf[6] << 24) |
                         ((uint32_t)buf[5] << 16) |
                         ((uint32_t)buf[4] << 8)  |
                         ((uint32_t)buf[3]);

        ImuFrame frame = {};
        frame.timestamp_ms   = ts_ms;
        frame.subscribe_tags = ctl;

        uint8_t L = 7;  // 从第 7 字节开始解析

        if (ctl & TAG_ACCEL_NO_GRAVITY) {
            frame.accel_lx = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_ly = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_lz = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
        }
        if (ctl & TAG_ACCEL_WITH_GRAVITY) {
            frame.accel_gx = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_gy = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_gz = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
        }
        if (ctl & TAG_ANGULAR_VELOCITY) {
            frame.gyro_x = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE_SPEED; L += 2;
            frame.gyro_y = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE_SPEED; L += 2;
            frame.gyro_z = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE_SPEED; L += 2;
        }
        if (ctl & TAG_MAGNETIC) {
            frame.mag_x = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_MAG; L += 2;
            frame.mag_y = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_MAG; L += 2;
            frame.mag_z = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_MAG; L += 2;
        }
        if (ctl & TAG_TEMP_PRESSURE_HEIGHT) {
            frame.temperature = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_TEMPERATURE; L += 2;

            uint32_t raw_p = ((uint32_t)buf[L+2] << 16) | ((uint32_t)buf[L+1] << 8) | (uint32_t)buf[L];
            raw_p = (raw_p & 0x800000) ? (raw_p | 0xFF000000) : raw_p;
            frame.air_pressure = (int32_t)raw_p * IM948_SCALE_AIR_PRESSURE;
            L += 3;

            uint32_t raw_h = ((uint32_t)buf[L+2] << 16) | ((uint32_t)buf[L+1] << 8) | (uint32_t)buf[L];
            raw_h = (raw_h & 0x800000) ? (raw_h | 0xFF000000) : raw_h;
            frame.height = (int32_t)raw_h * IM948_SCALE_HEIGHT;
            L += 3;
        }
        if (ctl & TAG_QUATERNION) {
            frame.quat_w = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_QUAT; L += 2;
            frame.quat_x = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_QUAT; L += 2;
            frame.quat_y = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_QUAT; L += 2;
            frame.quat_z = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_QUAT; L += 2;
        }
        if (ctl & TAG_EULER_ANGLES) {
            frame.euler_roll  = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE; L += 2;
            frame.euler_pitch = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE; L += 2;
            frame.euler_yaw   = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ANGLE; L += 2;
        }
        if (ctl & TAG_DISPLACEMENT) {
            frame.offset_x = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])); L += 2;
            frame.offset_y = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])); L += 2;
            frame.offset_z = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])); L += 2;
        }
        if (ctl & TAG_ACTIVITY) {
            L += 4;  // 计步数
            L += 1;  // 活动状态
        }
        if (ctl & TAG_ACCEL_NAV_FRAME) {
            frame.accel_nav_x = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_nav_y = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
            frame.accel_nav_z = ((int16_t)(((int16_t)buf[L+1]<<8) | buf[L])) * IM948_SCALE_ACCEL; L += 2;
        }
        if (ctl & TAG_ADC) {
            L += 2;  // ADC 值
        }
        if (ctl & TAG_GPIO1) {
            L += 1;  // GPIO1 状态
        }

        frame.is_valid = true;

        // 更新最新帧（临界区）
        taskDISABLE_INTERRUPTS();
        s_latest_frame = frame;
        s_has_new_data = true;
        taskENABLE_INTERRUPTS();
        break;
    }

    case 0x12: ESP_LOGI(TAG, "参数设置成功"); break;
    case 0x03: ESP_LOGI(TAG, "传感器已唤醒"); break;
    case 0x19: ESP_LOGI(TAG, "主动上报已确认"); break;
    case 0x05: ESP_LOGI(TAG, "Z轴已归零"); break;
    case 0x07: ESP_LOGI(TAG, "加速计校准中，等待 9 秒"); break;

    default:
        break;
    }
}
