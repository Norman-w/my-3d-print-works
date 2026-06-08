#ifndef RESET_BUTTON_H
#define RESET_BUTTON_H

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 初始化硬件Reset按钮
 * @return ESP_OK 表示成功，其他值表示错误
 */
esp_err_t reset_button_init(void);

/**
 * 反初始化Reset按钮功能
 */
void reset_button_deinit(void);

#ifdef __cplusplus
}
#endif

#endif // RESET_BUTTON_H
