#include "im948_sensor.h"
#include "im948_sdk.h"
#include "const.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cmath>
#include <cstdio>
#include <cstring>

// ===== 分区：常量/配置 =====

static const char *TAG = "im948_sensor";

// ===== 分区：私有成员 =====

Im948AccelRange Im948Sensor::s_accel_range = Im948AccelRange::G16;
Im948GyroRange  Im948Sensor::s_gyro_range  = Im948GyroRange::DPS2048;
ImuFrame        Im948Sensor::s_latest_frame = {};
volatile bool   Im948Sensor::s_has_new_data = false;
uart_port_t     Im948Sensor::s_uart_num     = UART_NUM_MAX;
volatile uint32_t Im948Sensor::s_rx_pkt_count = 0;
static uint8_t s_dump_left = 0;
static volatile bool s_status_fresh = false;
static volatile bool s_sensor_on = false;
static volatile bool s_report_on = false;
static volatile uint16_t s_status_bat_mv = 0;

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
    ESP_LOGI(TAG, "唤醒命令已发送，等待稳定...");
    vTaskDelay(pdMS_TO_TICKS(500));
    return ESP_OK;
}

esp_err_t Im948Sensor::wake_quick() {
    uint8_t cmd = 0x03;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "快速唤醒发送失败");
        return ESP_FAIL;
    }
    vTaskDelay(pdMS_TO_TICKS(50));
    return ESP_OK;
}

esp_err_t Im948Sensor::soft_reset() {
    uint8_t cmd = 0x2A;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "Cmd_2A 软复位发送失败");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "IM948 软复位已发送，等待模块重启...");
    vTaskDelay(pdMS_TO_TICKS(1500));
    return ESP_OK;
}

bool Im948Sensor::is_sensor_on() {
    return s_sensor_on;
}

esp_err_t Im948Sensor::refresh_status(uint32_t timeout_ms) {
    s_status_fresh = false;
    if (request_status() != ESP_OK) {
        return ESP_FAIL;
    }
    const TickType_t deadline =
        xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);
    while (!s_status_fresh) {
        if (xTaskGetTickCount() >= deadline) {
            return ESP_ERR_TIMEOUT;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
    return ESP_OK;
}

esp_err_t Im948Sensor::ensure_sensor_on(int max_attempts) {
    for (int i = 0; i < max_attempts; ++i) {
        (void)wake_quick();
        vTaskDelay(pdMS_TO_TICKS(200));
        if (refresh_status(400) == ESP_OK && s_sensor_on) {
            ESP_LOGI(TAG, "传感器已确认开启 (attempt %d, bat=%umV report=%u)",
                     i + 1, (unsigned)s_status_bat_mv,
                     (unsigned)s_report_on);
            return ESP_OK;
        }
        ESP_LOGW(TAG, "唤醒后 sensor_on 仍为 0，重试 (%d/%d)",
                 i + 1, max_attempts);
    }
    ESP_LOGE(TAG, "无法打开传感器（查 VBUS/模块供电）");
    return ESP_ERR_INVALID_STATE;
}

esp_err_t Im948Sensor::configure(
    Im948AccelRange accel_range, Im948GyroRange gyro_range,
    uint8_t report_hz, uint16_t subscribe_tags,
    uint8_t gyro_filter, uint8_t accel_filter, uint8_t compass_filter,
    bool enable_compass) {

    s_accel_range = accel_range;
    s_gyro_range  = gyro_range;

    // 对齐厂商例程：只发 Cmd_12（量程用模块默认；Cmd_33 非必需）
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

    ESP_LOGI(TAG, "配置完成: hz=%d tags=0x%04X (默认量程)",
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

    esp_err_t ret = im948_uart_set_baudrate(target_baud);
    if (ret != ESP_OK) {
        return ret;
    }
    // 升波特后模块侧会话仍在；稍等再发后续 Cmd_12/19
    vTaskDelay(pdMS_TO_TICKS(50));
    return ESP_OK;
}

esp_err_t Im948Sensor::apply_subscribe(uint16_t subscribe_tags, uint8_t report_hz) {
    uint8_t buf[11] = {};
    buf[0] = 0x12;
    buf[1] = 5;
    buf[2] = 255;
    buf[3] = 0;
    buf[4] = 0;  // 不融合磁场
    buf[5] = report_hz;
    buf[6] = 0;
    buf[7] = 0;
    buf[8] = 9;
    buf[9] = subscribe_tags & 0xFF;
    buf[10] = (subscribe_tags >> 8) & 0xFF;

    if (im948_pack_and_tx(buf, 11) != 0) {
        ESP_LOGE(TAG, "重发 Cmd_12 失败");
        return ESP_FAIL;
    }
    vTaskDelay(pdMS_TO_TICKS(50));
    ESP_LOGI(TAG, "已重申订阅 tags=0x%04X hz=%u", subscribe_tags,
             (unsigned)report_hz);
    return ESP_OK;
}

esp_err_t Im948Sensor::request_status() {
    uint8_t cmd = 0x10;
    if (im948_pack_and_tx(&cmd, 1) != 0) {
        ESP_LOGE(TAG, "Cmd_10 发送失败");
        return ESP_FAIL;
    }
    return ESP_OK;
}

uint32_t Im948Sensor::rx_packet_count() {
    return s_rx_pkt_count;
}

void Im948Sensor::reset_rx_packet_count() {
    s_rx_pkt_count = 0;
}

void Im948Sensor::request_hex_dumps(uint8_t count) {
    s_dump_left = count;
}

static int baud_of(Im948BaudRate b) {
    switch (b) {
        case Im948BaudRate::B9600:   return 9600;
        case Im948BaudRate::B115200: return 115200;
        case Im948BaudRate::B230400: return 230400;
        case Im948BaudRate::B460800: return 460800;
    }
    return 115200;
}

esp_err_t Im948Sensor::ensure_baud_115200() {
    const Im948BaudRate candidates[] = {
        Im948BaudRate::B115200,
        Im948BaudRate::B230400,
        Im948BaudRate::B460800,
    };

    for (Im948BaudRate cand : candidates) {
        const int baud = baud_of(cand);
        ESP_LOGI(TAG, "探测 IM948 波特率 %d ...", baud);
        esp_err_t err = im948_uart_set_baudrate(baud);
        if (err != ESP_OK) {
            continue;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
        reset_rx_packet_count();
        (void)request_status();
        vTaskDelay(pdMS_TO_TICKS(300));
        if (rx_packet_count() == 0) {
            // 再试一次唤醒+状态
            (void)wake_quick();
            (void)request_status();
            vTaskDelay(pdMS_TO_TICKS(300));
        }
        if (rx_packet_count() > 0) {
            ESP_LOGI(TAG, "IM948 在 %d 有应答 (pkts=%lu)", baud,
                     (unsigned long)rx_packet_count());
            if (cand != Im948BaudRate::B115200) {
                ESP_LOGW(TAG, "模块滞留在 %d，Cmd_47 拉回 115200", baud);
                uint8_t buf[2] = {0x47, static_cast<uint8_t>(Im948BaudRate::B115200)};
                if (im948_pack_and_tx(buf, 2) != 0) {
                    ESP_LOGE(TAG, "Cmd_47→115200 发送失败");
                    return ESP_FAIL;
                }
                vTaskDelay(pdMS_TO_TICKS(200));
                err = im948_uart_set_baudrate(115200);
                if (err != ESP_OK) {
                    return err;
                }
                vTaskDelay(pdMS_TO_TICKS(50));
                reset_rx_packet_count();
                (void)request_status();
                vTaskDelay(pdMS_TO_TICKS(300));
                if (rx_packet_count() == 0) {
                    ESP_LOGE(TAG, "拉回 115200 后仍无应答");
                    return ESP_FAIL;
                }
                ESP_LOGI(TAG, "已恢复 115200 通信");
            }
            return ESP_OK;
        }
    }

    ESP_LOGE(TAG, "115200/230400/460800 均无 IM948 应答（查接线/供电）");
    // 回到默认
    (void)im948_uart_set_baudrate(115200);
    return ESP_ERR_NOT_FOUND;
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
    ++s_rx_pkt_count;

    switch (buf[0]) {
    case 0x10: {  // 模块属性和状态
        if (dlen >= 11) {
            const uint8_t flags = buf[4];
            const uint16_t tags =
                (uint16_t)(((uint16_t)buf[10] << 8) | buf[9]);
            const uint16_t bat_mv = (dlen >= 15)
                ? (uint16_t)(((uint16_t)buf[14] << 8) | buf[13])
                : 0;
            s_sensor_on = ((flags >> 3) & 1) != 0;
            s_report_on = ((flags >> 4) & 1) != 0;
            s_status_bat_mv = bat_mv;
            s_status_fresh = true;
            ESP_LOGI(TAG,
                     "设备状态: sensor_on=%u report_on=%u hz=%u tags=0x%04X "
                     "charge=%u bat=%u%% %umV",
                     (unsigned)s_sensor_on,
                     (unsigned)s_report_on,
                     (unsigned)buf[5], tags,
                     (unsigned)buf[11],
                     dlen >= 13 ? (unsigned)buf[12] : 0u,
                     (unsigned)bat_mv);
        } else {
            ESP_LOGI(TAG, "收到设备属性和状态 dlen=%u", dlen);
        }
        break;
    }

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

        // 仅在 request_hex_dumps() 后打印若干帧
        if (s_dump_left > 0) {
            --s_dump_left;
            const uint8_t dump_n = dlen < 40 ? dlen : 40;
            char hex[3 * 40 + 1];
            size_t hp = 0;
            for (uint8_t i = 0; i < dump_n && hp + 3 < sizeof(hex); ++i) {
                hp += (size_t)snprintf(hex + hp, sizeof(hex) - hp, "%02X ", buf[i]);
            }
            int16_t raw_ax = 0, raw_ay = 0, raw_az = 0;
            if (dlen >= 13 && (ctl & TAG_ACCEL_WITH_GRAVITY)) {
                raw_ax = (int16_t)(((int16_t)buf[8] << 8) | buf[7]);
                raw_ay = (int16_t)(((int16_t)buf[10] << 8) | buf[9]);
                raw_az = (int16_t)(((int16_t)buf[12] << 8) | buf[11]);
            }
            ESP_LOGI(TAG,
                     "0x11 dump dlen=%u ctl=0x%04X ts=%lu rawA=%d,%d,%d "
                     "temp=%.2f | %s",
                     dlen, ctl, (unsigned long)ts_ms,
                     (int)raw_ax, (int)raw_ay, (int)raw_az,
                     frame.temperature, hex);
        }

        // 更新最新帧（临界区）
        taskDISABLE_INTERRUPTS();
        s_latest_frame = frame;
        s_has_new_data = true;
        taskENABLE_INTERRUPTS();
        break;
    }

    case 0x12: ESP_LOGI(TAG, "参数设置成功"); break;
    case 0x03:
        ESP_LOGI(TAG, "传感器已唤醒(ACK)");
        s_sensor_on = true;
        break;
    case 0x19: ESP_LOGI(TAG, "主动上报已确认"); break;
    case 0x18: ESP_LOGI(TAG, "主动上报已关闭"); break;
    case 0x2A: ESP_LOGI(TAG, "模块将重启"); break;
    case 0x40: ESP_LOGI(TAG, "开机工作模式已设置"); break;
    case 0x05: ESP_LOGI(TAG, "Z轴已归零"); break;
    case 0x07: ESP_LOGI(TAG, "加速计校准中，等待 9 秒"); break;

    default:
        break;
    }
}
