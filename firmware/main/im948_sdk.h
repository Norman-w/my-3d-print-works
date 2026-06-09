#pragma once

#include <cstdint>
#include "driver/uart.h"
#include "esp_err.h"

// ===== 分区：常量/配置 =====

#define IM948_PREAMBLE_LEN 50  // 发送前导码长度（唤醒可能睡眠的模块）

// ===== 分区：公开 API =====

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 初始化 UART 驱动
 * @param uart_num  UART 端口号
 * @param tx_pin    TX 引脚
 * @param rx_pin    RX 引脚
 * @param baud_rate 波特率
 * @param rx_buf_size 接收缓冲区大小
 * @return ESP_OK 成功
 */
esp_err_t im948_uart_init(uart_port_t uart_num, int tx_pin, int rx_pin,
                          int baud_rate, int rx_buf_size);

/**
 * 更新 UART 波特率
 * @param baud_rate 目标波特率
 * @return ESP_OK 成功
 */
esp_err_t im948_uart_set_baudrate(int baud_rate);

/**
 * 构建并发送命令包
 * 包格式：50字节前导码 | 0x49 | Addr(1B) | Len(1B) | Data(NB) | CS(1B) | 0x4D
 * @param pdat   命令数据体
 * @param dlen   数据体长度
 * @return 0 成功, -1 失败
 */
int im948_pack_and_tx(const uint8_t *pdat, uint8_t dlen);

/**
 * 逐字节喂入解析状态机。当收到完整数据包时，通过回调通知上层。
 * @param byte 接收到的一个字节
 * @return 1 捕获到完整数据包, 0 未完成
 */
uint8_t im948_get_pkt(uint8_t byte);

/**
 * 数据包回调注册。当解析到一个完整 IM948 数据包时调用。
 * @param callback 回调函数 (数据体指针, 数据体长度)
 */
typedef void (*im948_rx_callback_t)(const uint8_t *data, uint8_t len);
void im948_set_rx_callback(im948_rx_callback_t callback);

/**
 * 设置目标设备地址（默认 255 广播）
 * @param addr 设备地址 0-254 为指定设备, 255 为广播
 */
void im948_set_device_address(uint8_t addr);

#ifdef __cplusplus
}
#endif
