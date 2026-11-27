#include "battery_monitor.h"

#include <cstdio>

#include "config.h"
#include "const.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ws_data_server.h"

namespace battery_monitor {

// ===== 常量/配置 =====
static const char *TAG = LOG_TAG_MAIN;
static constexpr adc_atten_t kAttenuation = ADC_ATTEN_DB_12;
static constexpr adc_bitwidth_t kBitWidth = ADC_BITWIDTH_DEFAULT;
static constexpr int kAverageSamples = 32;
static constexpr int kPublishPeriodMs = 5000;
static constexpr float kDividerRatio = 2.0f;  // 1M top / 1M bottom

// ===== 私有状态 =====
static adc_oneshot_unit_handle_t s_adc = nullptr;
static adc_cali_handle_t s_calibration = nullptr;
static adc_channel_t s_channel = ADC_CHANNEL_0;
static bool s_ready = false;

static void release_adc() {
    if (s_calibration) {
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
        (void)adc_cali_delete_scheme_curve_fitting(s_calibration);
#endif
        s_calibration = nullptr;
    }
    if (s_adc) {
        (void)adc_oneshot_del_unit(s_adc);
        s_adc = nullptr;
    }
}

struct CurvePoint {
    int mv;
    uint8_t percent;
};

// Coarse 1S Li-ion open-circuit curve.  It is deliberately reported as an
// estimate because load, temperature, cell chemistry and the 1% divider all
// move the result.  It is not a fuel gauge and is never used for protection.
static constexpr CurvePoint kCurve[] = {
    {3300, 0}, {3500, 5}, {3600, 10}, {3700, 25}, {3800, 45},
    {3900, 65}, {4000, 80}, {4100, 90}, {4200, 100},
};

// ===== 私有成员 =====
static void telemetry_task(void *) {
    while (true) {
        const Telemetry sample = read();
        if (sample.valid && ws_data_has_client()) {
            char json[160];
            const int length = std::snprintf(
                json, sizeof(json),
                "{\"type\":\"power\",\"battery_mv\":%d,"
                "\"battery_percent\":%u,\"percent_is_estimate\":true,"
                "\"adc_calibrated\":%s}",
                sample.cell_mv,
                static_cast<unsigned>(sample.percent_estimate),
                sample.calibrated ? "true" : "false");
            if (length > 0 && static_cast<size_t>(length) < sizeof(json)) {
                (void)ws_data_send_text(json, static_cast<size_t>(length));
            }
        }
        vTaskDelay(pdMS_TO_TICKS(kPublishPeriodMs));
    }
}

// ===== 公开 API =====
uint8_t percent_from_cell_mv(int cell_mv) {
    if (cell_mv <= kCurve[0].mv) return kCurve[0].percent;
    const size_t count = sizeof(kCurve) / sizeof(kCurve[0]);
    if (cell_mv >= kCurve[count - 1].mv) return kCurve[count - 1].percent;
    for (size_t i = 1; i < count; ++i) {
        if (cell_mv <= kCurve[i].mv) {
            const CurvePoint lo = kCurve[i - 1];
            const CurvePoint hi = kCurve[i];
            const int numerator =
                (cell_mv - lo.mv) * (static_cast<int>(hi.percent) - lo.percent);
            return static_cast<uint8_t>(
                lo.percent + numerator / (hi.mv - lo.mv));
        }
    }
    return 100;
}

Telemetry read() {
    Telemetry result = {};
    result.calibrated = s_calibration != nullptr;
    if (!s_ready || !s_adc || !s_calibration) return result;

    int discarded = 0;
    (void)adc_oneshot_read(s_adc, s_channel, &discarded);
    int64_t raw_sum = 0;
    int accepted = 0;
    for (int i = 0; i < kAverageSamples; ++i) {
        int raw = 0;
        if (adc_oneshot_read(s_adc, s_channel, &raw) == ESP_OK) {
            raw_sum += raw;
            ++accepted;
        }
    }
    if (accepted < kAverageSamples / 2) return result;

    const int raw_average = static_cast<int>(raw_sum / accepted);
    int sense_mv = 0;
    if (adc_cali_raw_to_voltage(s_calibration, raw_average, &sense_mv) != ESP_OK) {
        return result;
    }
    const int cell_mv = static_cast<int>(sense_mv * kDividerRatio + 0.5f);
    // A powered board with no battery can leave the divider near zero.  Values
    // outside a plausible 1S range are marked invalid rather than dressed up
    // as a state-of-charge number.
    if (cell_mv < 2500 || cell_mv > 4500) return result;

    result.valid = true;
    result.cell_mv = cell_mv;
    result.percent_estimate = percent_from_cell_mv(cell_mv);
    return result;
}

esp_err_t init() {
    adc_unit_t unit = ADC_UNIT_1;
    esp_err_t error = adc_oneshot_io_to_channel(
        static_cast<int>(BAT_SENSE_GPIO), &unit, &s_channel);
    if (error != ESP_OK) {
        ESP_LOGE(TAG, "BAT_SENSE GPIO%d 不是 ADC 引脚: %s",
                 static_cast<int>(BAT_SENSE_GPIO), esp_err_to_name(error));
        return error;
    }
    if (unit != ADC_UNIT_1 || s_channel != ADC_CHANNEL_8) {
        ESP_LOGE(TAG, "BAT_SENSE 映射异常: unit=%d channel=%d (期望 ADC1_CH8)",
                 static_cast<int>(unit), static_cast<int>(s_channel));
        return ESP_ERR_INVALID_STATE;
    }

    const adc_oneshot_unit_init_cfg_t unit_config = {
        .unit_id = unit,
        .clk_src = ADC_RTC_CLK_SRC_DEFAULT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    error = adc_oneshot_new_unit(&unit_config, &s_adc);
    if (error != ESP_OK) return error;

    const adc_oneshot_chan_cfg_t channel_config = {
        .atten = kAttenuation,
        .bitwidth = kBitWidth,
    };
    error = adc_oneshot_config_channel(s_adc, s_channel, &channel_config);
    if (error != ESP_OK) {
        release_adc();
        return error;
    }

#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    const adc_cali_curve_fitting_config_t calibration_config = {
        .unit_id = unit,
        .chan = s_channel,
        .atten = kAttenuation,
        .bitwidth = kBitWidth,
    };
    error = adc_cali_create_scheme_curve_fitting(
        &calibration_config, &s_calibration);
#else
    error = ESP_ERR_NOT_SUPPORTED;
#endif
    if (error != ESP_OK) {
        ESP_LOGE(TAG, "BAT_SENSE ADC 校准不可用，拒绝发布伪精确电压: %s",
                 esp_err_to_name(error));
        release_adc();
        return error;
    }

    s_ready = true;
    const BaseType_t created = xTaskCreate(
        telemetry_task, "battery", 3072, nullptr, 4, nullptr);
    if (created != pdPASS) {
        s_ready = false;
        release_adc();
        return ESP_ERR_NO_MEM;
    }
    ESP_LOGI(TAG, "BAT_SENSE GPIO%d = ADC1_CH8，1M/1M 分压，已启用校准",
             static_cast<int>(BAT_SENSE_GPIO));
    return ESP_OK;
}

}  // namespace battery_monitor
