#include "im948_sdk.h"
#include "im948_data.h"
#include "const.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cstring>

// ===== 分区：常量/配置 =====

static const char *TAG = "im948_sdk";
#define IM948_PKT_TX_BUF_SIZE (IM948_PREAMBLE_LEN + 5 + IM948_PKT_MAX_TX_DATA)

// ===== 分区：私有成员 =====

static uart_port_t s_uart_num = UART_NUM_MAX;
static uint8_t s_device_addr = 255;  // 默认广播地址
static im948_rx_callback_t s_rx_callback = nullptr;

// 接收状态机变量
static uint8_t s_rx_cs = 0;
static uint8_t s_rx_idx = 0;
static uint8_t s_rx_buf[5 + IM948_PKT_MAX_RX_DATA];

// 内部便捷宏
#define RX_BEGIN    s_rx_buf[0]
#define RX_ADDRESS  s_rx_buf[1]
#define RX_LEN      s_rx_buf[2]
#define RX_DAT      (&s_rx_buf[3])
#define RX_CS       s_rx_buf[3 + RX_LEN]
#define RX_END      s_rx_buf[4 + RX_LEN]

// 计算校验和（从地址码开始算到数据体结束）
static uint8_t calc_sum1(const uint8_t *buf, int len) {
    uint8_t sum = 0;
    while (len-- > 0) {
        sum += buf[len];
    }
    return sum;
}

// 内存拷贝（兼容原 Arduino 实现）
static void mem_cpy(void *dst, const void *src, unsigned int n) {
    char *d = (char *)dst;
    const char *s = (const char *)src;
    if (n) {
        n++;
        while (--n > 0) {
            *d++ = *s++;
        }
    }
}

// ===== 分区：公开 API =====

esp_err_t im948_uart_init(uart_port_t uart_num, int tx_pin, int rx_pin,
                          int baud_rate, int rx_buf_size) {
    s_uart_num = uart_num;

    uart_config_t uart_config = {};
    uart_config.baud_rate = baud_rate;
    uart_config.data_bits = UART_DATA_8_BITS;
    uart_config.parity = UART_PARITY_DISABLE;
    uart_config.stop_bits = UART_STOP_BITS_1;
    uart_config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    uart_config.source_clk = UART_SCLK_DEFAULT;

    ESP_ERROR_CHECK(uart_driver_install(uart_num, rx_buf_size, 0, 0, nullptr, 0));
    ESP_ERROR_CHECK(uart_param_config(uart_num, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(uart_num, tx_pin, rx_pin,
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    ESP_LOGI(TAG, "UART%d 初始化: TX=GPIO%d RX=GPIO%d baud=%d",
             uart_num, tx_pin, rx_pin, baud_rate);
    return ESP_OK;
}

esp_err_t im948_uart_set_baudrate(int baud_rate) {
    if (s_uart_num >= UART_NUM_MAX) {
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t ret = uart_set_baudrate(s_uart_num, baud_rate);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "UART%d 波特率升级到 %d", s_uart_num, baud_rate);
    }
    return ret;
}

int im948_pack_and_tx(const uint8_t *pdat, uint8_t dlen) {
    if (s_uart_num >= UART_NUM_MAX) {
        return -1;
    }
    if ((dlen == 0) || (dlen > IM948_PKT_MAX_TX_DATA) || (pdat == nullptr)) {
        return -1;
    }

    uint8_t buf[IM948_PKT_TX_BUF_SIZE];
    memset(buf, 0x00, IM948_PREAMBLE_LEN);
    // 前导码最后两字节填充 0xFF（帮助模块检测起始）
    buf[IM948_PREAMBLE_LEN - 2] = 0xFF;
    buf[IM948_PREAMBLE_LEN - 1] = 0xFF;

    buf[IM948_PREAMBLE_LEN]     = IM948_PKT_BEGIN;
    buf[IM948_PREAMBLE_LEN + 1] = s_device_addr;
    buf[IM948_PREAMBLE_LEN + 2] = dlen;
    mem_cpy(&buf[IM948_PREAMBLE_LEN + 3], pdat, dlen);

    uint8_t cs_idx = IM948_PREAMBLE_LEN + 3 + dlen;
    buf[cs_idx]     = calc_sum1(&buf[IM948_PREAMBLE_LEN + 1], dlen + 2);
    buf[cs_idx + 1] = IM948_PKT_END;

    int total_len = IM948_PREAMBLE_LEN + dlen + 5;
    int written = uart_write_bytes(s_uart_num, buf, total_len);
    return (written == total_len) ? 0 : -1;
}

uint8_t im948_get_pkt(uint8_t byte) {
    s_rx_cs += byte;

    switch (s_rx_idx) {
    case 0:  // 等待起始码
        if (byte == IM948_PKT_BEGIN) {
            s_rx_buf[0] = IM948_PKT_BEGIN;
            s_rx_cs = 0;  // 从下一字节开始计算校验和
            s_rx_idx = 1;
        }
        break;

    case 1:  // 地址码
        s_rx_buf[1] = byte;
        if (byte == 255) {
            // 广播地址，不应作为从机地址出现
            s_rx_idx = 0;
            break;
        }
        s_rx_idx++;
        break;

    case 2:  // 长度
        s_rx_buf[2] = byte;
        if ((byte > IM948_PKT_MAX_RX_DATA) || (byte == 0)) {
            s_rx_idx = 0;
            break;
        }
        s_rx_idx++;
        break;

    case 3: {  // 数据体
        uint8_t data_pos = s_rx_idx - 2;  // 相对于数据体起始的索引
        s_rx_buf[3 + data_pos] = byte;
        if (data_pos + 1 >= RX_LEN) {
            s_rx_idx++;  // 数据体收完
        }
    } break;

    case 4:  // 校验码
        s_rx_cs -= byte;
        if (s_rx_cs == byte) {
            s_rx_buf[3 + RX_LEN] = byte;
            s_rx_idx++;
        } else {
            s_rx_idx = 0;
        }
        break;

    case 5:  // 结束码
        s_rx_idx = 0;
        if (byte == IM948_PKT_END) {
            uint8_t total = 4 + RX_LEN;
            s_rx_buf[total] = byte;

            if ((s_device_addr == RX_ADDRESS) || (s_device_addr == 255)) {
                if (s_rx_callback) {
                    s_rx_callback(RX_DAT, RX_LEN);
                }
                return 1;
            }
        }
        break;

    default:
        s_rx_idx = 0;
        break;
    }
    return 0;
}

void im948_set_rx_callback(im948_rx_callback_t callback) {
    s_rx_callback = callback;
}

void im948_set_device_address(uint8_t addr) {
    s_device_addr = addr;
}
