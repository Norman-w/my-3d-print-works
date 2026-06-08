#include "status_led.h"

#include "led_strip.h"
#include <esp_log.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

namespace status_led {

namespace {

struct Color {
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

constexpr char kTag[] = "status_led";
constexpr int kLedGpio = 8; // 板载 RGB LED 数据脚
constexpr uint32_t kBlinkPeriodUs = 500'000; // 500ms
constexpr float kBrightness = 0.05f; // 亮度控制因子 (0.0-1.0)，最低亮度，减少刺眼感

led_strip_handle_t s_strip = nullptr;
esp_timer_handle_t s_blink_timer = nullptr;
esp_timer_handle_t s_override_timer = nullptr;

Color s_base_color{0, 0, 0};
bool s_base_blink = false;
volatile bool s_blink_on = true;

Color s_override_color{0, 0, 0};
bool s_override_active = false;

void apply_color(const Color &color) {
    if (!s_strip) {
        return;
    }
    // 应用亮度控制因子
    uint8_t r = (uint8_t)(color.r * kBrightness);
    uint8_t g = (uint8_t)(color.g * kBrightness);
    uint8_t b = (uint8_t)(color.b * kBrightness);

    if (led_strip_set_pixel(s_strip, 0, r, g, b) != ESP_OK) {
        ESP_LOGW(kTag, "Failed to set pixel");
    }
    if (led_strip_refresh(s_strip) != ESP_OK) {
        ESP_LOGW(kTag, "Failed to refresh strip");
    }
}

Color current_display_color() {
    if (s_override_active) {
        return s_override_color;
    }
    if (s_base_blink && !s_blink_on) {
        return Color{0, 0, 0};
    }
    return s_base_color;
}

void update_output() {
    apply_color(current_display_color());
}

void blink_timer_cb(void *) {
    if (!s_base_blink) {
        return;
    }
    s_blink_on = !s_blink_on;
    update_output();
}

void override_timer_cb(void *) {
    s_override_active = false;
    update_output();
}

void ensure_timers_created() {
    if (!s_blink_timer) {
        esp_timer_create_args_t blink_args = {};
        blink_args.callback = &blink_timer_cb;
        blink_args.arg = nullptr;
        blink_args.dispatch_method = ESP_TIMER_TASK;
        blink_args.name = "status_led_blink";
        ESP_ERROR_CHECK(esp_timer_create(&blink_args, &s_blink_timer));
    }

    if (!s_override_timer) {
        esp_timer_create_args_t override_args = {};
        override_args.callback = &override_timer_cb;
        override_args.arg = nullptr;
        override_args.dispatch_method = ESP_TIMER_TASK;
        override_args.name = "status_led_override";
        ESP_ERROR_CHECK(esp_timer_create(&override_args, &s_override_timer));
    }
}

void start_blink_timer() {
    if (s_blink_timer && !esp_timer_is_active(s_blink_timer)) {
        ESP_ERROR_CHECK(esp_timer_start_periodic(s_blink_timer, kBlinkPeriodUs));
    }
}

void stop_blink_timer() {
    if (s_blink_timer && esp_timer_is_active(s_blink_timer)) {
        ESP_ERROR_CHECK(esp_timer_stop(s_blink_timer));
    }
    s_blink_on = true;
}

} // namespace

esp_err_t init() {
    if (s_strip) {
        return ESP_OK;
    }

    led_strip_config_t strip_config = {};
    strip_config.strip_gpio_num = kLedGpio;
    strip_config.max_leds = 1;
    strip_config.led_pixel_format = LED_PIXEL_FORMAT_GRB;
    strip_config.led_model = LED_MODEL_WS2812;
    strip_config.flags.invert_out = false;

    led_strip_rmt_config_t rmt_config = {};
    rmt_config.clk_src = RMT_CLK_SRC_DEFAULT;
    rmt_config.resolution_hz = 10 * 1000 * 1000;
    rmt_config.flags.with_dma = false;

    esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &s_strip);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "Failed to create led strip: %s", esp_err_to_name(err));
        return err;
    }

    ensure_timers_created();
    s_base_color = Color{0, 0, 0};
    s_base_blink = false;
    s_override_active = false;
    s_blink_on = true;
    update_output();

    ESP_LOGI(kTag, "Status LED initialized on GPIO%d", kLedGpio);
    return ESP_OK;
}

void deinit() {
    if (s_blink_timer) {
        if (esp_timer_is_active(s_blink_timer)) {
            esp_timer_stop(s_blink_timer);
        }
        esp_timer_delete(s_blink_timer);
        s_blink_timer = nullptr;
    }
    if (s_override_timer) {
        if (esp_timer_is_active(s_override_timer)) {
            esp_timer_stop(s_override_timer);
        }
        esp_timer_delete(s_override_timer);
        s_override_timer = nullptr;
    }

    if (s_strip) {
        apply_color(Color{0, 0, 0});
        led_strip_del(s_strip);
        s_strip = nullptr;
    }
}

void set_boot() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }
    s_base_color = Color{255, 255, 255};
    s_base_blink = false;
    stop_blink_timer();
    update_output();
}

void set_ap_mode() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }
    s_base_color = Color{255, 105, 180}; // 粉色
    s_base_blink = false;
    stop_blink_timer();
    update_output();
}

void set_sta_connecting() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }
    s_base_color = Color{0, 0, 255}; // 蓝色
    s_base_blink = true;
    start_blink_timer();
    update_output();
}

void set_sta_connected() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }
    s_base_color = Color{0, 0, 255};
    s_base_blink = false;
    stop_blink_timer();
    update_output();
}

void set_off() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }
    s_base_color = Color{0, 0, 0};
    s_base_blink = false;
    stop_blink_timer();
    update_output();
}

void flash_connect_start() {
    if (!s_strip) {
        ESP_LOGW(kTag, "Status LED not initialized");
        return;
    }

    // 快速闪烁3次，每次100ms on/off
    for (int i = 0; i < 3; ++i) {
        apply_color(Color{0, 0, 255}); // 蓝色 on
        vTaskDelay(pdMS_TO_TICKS(100));
        apply_color(Color{0, 0, 0});   // off
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    // 完成后恢复到STA连接中的蓝色慢闪状态
    set_sta_connecting();
}

void notify_data_activity(uint32_t hold_ms) {
    if (!s_strip) {
        return;
    }
    s_override_color = Color{0, 255, 0}; // 绿色
    s_override_active = true;
    update_output();

    if (s_override_timer) {
        if (esp_timer_is_active(s_override_timer)) {
            esp_timer_stop(s_override_timer);
        }
        ESP_ERROR_CHECK(esp_timer_start_once(s_override_timer, hold_ms * 1000));
    }
}

} // namespace status_led

