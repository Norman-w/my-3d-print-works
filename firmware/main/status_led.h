/*
 * RGB 状态灯控制接口。
 */
#pragma once

#include <cstdint>

#include "esp_err.h"

namespace status_led {

esp_err_t init();
void deinit();

void set_boot();                 // 上电，白色常亮
void set_ap_mode();              // 作为 AP，粉色常亮
void set_sta_connecting();       // STA 连接中，蓝色闪烁
void set_sta_connected();        // STA 已连接，蓝色常亮
void set_off();                  // 关闭灯光

void flash_connect_start();      // 开始连接时快速闪烁提醒

// 数据活动时调用，绿色保持一段时间后恢复底色
void notify_data_activity(uint32_t hold_ms = 300);

} // namespace status_led

