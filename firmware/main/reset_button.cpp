#include "reset_button.h"
#include "device_storage.h"
#include "config.h"
#include "esp_log.h"
#include "esp_system.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "const.h"

// ===== 常量/配置 =====
// 工程用 BOOT 键（GPIO9）；日常电源/长按关机见 power_control（GPIO18）
#define RESET_BUTTON_GPIO          BOOT_BTN_GPIO
#define RESET_BUTTON_ACTIVE_LEVEL  0
#define SHORT_PRESS_MAX_MS         500     // 短按判定阈值(ms)
#define LONG_PRESS_DURATION_MS     10000   // 长按触发重置的持续时间(ms)
#define COMBO_WINDOW_MS            3000    // 短按后必须在3秒内开始长按
#define DEBOUNCE_TIME_MS           50

static const char *TAG = LOG_TAG_RESET_BUTTON;

static QueueHandle_t gpio_evt_queue = NULL;

// ===== 私有两种状态机阶段 =====
enum class ResetPhase {
    IDLE,               // 等待短按
    SHORT_PRESSED,      // 已检测到短按，等待放开
    WAITING_LONG,       // 短按已确认释放，等待长按
    LONG_PRESSING,      // 正在长按中（计时）
    TRIGGERED           // 已触发重置
};

// ISR: GPIO 中断 → 队列
static void IRAM_ATTR gpio_isr_handler(void *arg) {
    uint32_t gpio_num = (uint32_t)arg;
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, NULL);
}

static void reset_button_task(void *arg) {
    uint32_t io_num;
    ResetPhase phase = ResetPhase::IDLE;
    uint32_t press_start_time = 0;
    uint32_t release_time = 0;
    bool is_pressed = false;

    ESP_LOGI(TAG, "Reset 按钮任务已启动 (组合键: 短按<%ums → 长按>%us)",
             SHORT_PRESS_MAX_MS, LONG_PRESS_DURATION_MS / 1000);

    while (1) {
        if (xQueueReceive(gpio_evt_queue, &io_num, portMAX_DELAY)) {
            if (io_num != RESET_BUTTON_GPIO) continue;

            int level = gpio_get_level(RESET_BUTTON_GPIO);
            uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;

            if (level == RESET_BUTTON_ACTIVE_LEVEL && !is_pressed) {
                // 按钮按下
                is_pressed = true;
                press_start_time = now;

                switch (phase) {
                    case ResetPhase::IDLE:
                        // 第一次按下
                        phase = ResetPhase::SHORT_PRESSED;
                        ESP_LOGD(TAG, "检测到按下...");
                        break;

                    case ResetPhase::WAITING_LONG:
                        // 短按后再次按下 = 进入长按阶段
                        if (now - release_time < COMBO_WINDOW_MS) {
                            phase = ResetPhase::LONG_PRESSING;
                            ESP_LOGI(TAG, "长按已开始，请保持按住 %us 以重置设备...",
                                     LONG_PRESS_DURATION_MS / 1000);
                        } else {
                            // 超时，回到初始状态
                            ESP_LOGD(TAG, "组合键窗口超时，重置状态");
                            phase = ResetPhase::IDLE;
                        }
                        break;

                    default:
                        break;
                }

            } else if (level != RESET_BUTTON_ACTIVE_LEVEL && is_pressed) {
                // 按钮释放
                uint32_t press_duration = now - press_start_time;
                is_pressed = false;

                switch (phase) {
                    case ResetPhase::SHORT_PRESSED:
                        if (press_duration < SHORT_PRESS_MAX_MS) {
                            // 短按确认
                            phase = ResetPhase::WAITING_LONG;
                            release_time = now;
                            ESP_LOGI(TAG, "短按已确认，请在 %us 内长按 %us 以重置",
                                     COMBO_WINDOW_MS / 1000, LONG_PRESS_DURATION_MS / 1000);
                        } else {
                            // 按得太久，不是短按，回到 IDLE
                            ESP_LOGD(TAG, "按下时间 %lums 超过短按阈值, 忽略", press_duration);
                            phase = ResetPhase::IDLE;
                        }
                        break;

                    case ResetPhase::LONG_PRESSING:
                        if (press_duration >= LONG_PRESS_DURATION_MS) {
                            // 长按达标!
                            phase = ResetPhase::TRIGGERED;
                            ESP_LOGI(TAG, "长按达标 (%lums)! 触发设备重置!", press_duration);

                            // 清空所有存储数据
                            device_storage_clear_all();

                            ESP_LOGI(TAG, "设备将在 3 秒后重启...");
                            vTaskDelay(pdMS_TO_TICKS(3000));

                            esp_restart();
                        } else {
                            // 长按不足，放弃
                            ESP_LOGW(TAG, "长按时间 %lums 不足 %ums，重置取消",
                                     press_duration, LONG_PRESS_DURATION_MS);
                            phase = ResetPhase::IDLE;
                        }
                        break;

                    default:
                        phase = ResetPhase::IDLE;
                        break;
                }
            }
        }
    }
}

esp_err_t reset_button_init(void) {
    ESP_LOGI(TAG, "初始化 Reset 按钮 (GPIO%d)", RESET_BUTTON_GPIO);

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << RESET_BUTTON_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };

    esp_err_t err = gpio_config(&io_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "配置 Reset 按钮 GPIO 失败: %s", esp_err_to_name(err));
        return err;
    }

    gpio_evt_queue = xQueueCreate(10, sizeof(uint32_t));
    if (!gpio_evt_queue) {
        ESP_LOGE(TAG, "创建 GPIO 事件队列失败");
        return ESP_ERR_NO_MEM;
    }

    err = gpio_install_isr_service(0);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "安装 GPIO ISR 服务失败: %s", esp_err_to_name(err));
        return err;
    }

    err = gpio_isr_handler_add(RESET_BUTTON_GPIO, gpio_isr_handler, (void*)RESET_BUTTON_GPIO);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "添加 GPIO ISR 处理函数失败: %s", esp_err_to_name(err));
        return err;
    }

    xTaskCreate(reset_button_task, "reset_button", 2048, NULL, 5, NULL);

    ESP_LOGI(TAG, "Reset 按钮初始化完成 (组合键模式)");
    return ESP_OK;
}

void reset_button_deinit(void) {
    ESP_LOGI(TAG, "反初始化 Reset 按钮");

    gpio_isr_handler_remove(RESET_BUTTON_GPIO);
    gpio_uninstall_isr_service();

    if (gpio_evt_queue) {
        vQueueDelete(gpio_evt_queue);
        gpio_evt_queue = NULL;
    }

    ESP_LOGI(TAG, "Reset 按钮反初始化完成");
}
