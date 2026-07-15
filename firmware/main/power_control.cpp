#include "power_control.h"

#include "config.h"
#include "const.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// ===== 常量/配置 =====
static const char *TAG = LOG_TAG_POWER;

// ===== 私有成员 =====
static void power_button_task(void *arg) {
    (void)arg;
    bool was_pressed = false;
    TickType_t press_start = 0;

    while (true) {
        const int level = gpio_get_level(USER_BTN_GPIO);
        const bool pressed = (level == USER_BTN_ACTIVE_LEVEL);
        const TickType_t now = xTaskGetTickCount();

        if (pressed && !was_pressed) {
            was_pressed = true;
            press_start = now;
        } else if (pressed && was_pressed) {
            const uint32_t held_ms =
                (now - press_start) * portTICK_PERIOD_MS;
            if (held_ms >= POWER_OFF_HOLD_MS) {
                ESP_LOGW(TAG, "尾键长按 %lu ms → 关机", (unsigned long)held_ms);
                power_control_shutdown();
            }
        } else if (!pressed && was_pressed) {
            was_pressed = false;
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

// ===== 公开 API =====
esp_err_t power_control_init(void) {
    gpio_config_t latch_cfg = {
        .pin_bit_mask = (1ULL << PWR_LATCH_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&latch_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "配置 PWR_LATCH GPIO%d 失败: %s", PWR_LATCH_GPIO,
                 esp_err_to_name(err));
        return err;
    }
    gpio_set_level(PWR_LATCH_GPIO, 1);
    ESP_LOGI(TAG, "PWR_LATCH GPIO%d 已拉高（保持开机）", PWR_LATCH_GPIO);

    gpio_config_t btn_cfg = {
        .pin_bit_mask = (1ULL << USER_BTN_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&btn_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "配置 USER_BTN GPIO%d 失败: %s", USER_BTN_GPIO,
                 esp_err_to_name(err));
        return err;
    }

    BaseType_t ok = xTaskCreate(power_button_task, "power_btn", 2048, NULL, 5,
                                 NULL);
    if (ok != pdPASS) {
        ESP_LOGE(TAG, "创建电源键任务失败");
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

void power_control_shutdown(void) {
    ESP_LOGW(TAG, "释放 PWR_LATCH，即将断电");
    gpio_set_level(PWR_LATCH_GPIO, 0);
    // 按键仍按住时二极管会继续拉低门极；等松手后才真正掉电
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/*
 * 复位行为（刻意故障安全）：
 * 电池供电时 GPIO10 复位后变高阻，PWR_LATCH 被 100k 下拉 → 锁存释放 → 关机。
 * esp_restart / WDT / panic / 恢复出厂后的重启都不会自动保持开机，需再按尾键。
 * 若产品要“复位后仍开机”，需改硬件保持，不能只改固件。
 */
