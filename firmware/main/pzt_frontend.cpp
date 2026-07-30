#include "pzt_frontend.h"

#include "config.h"
#include "driver/i2c_master.h"
#include "esp_log.h"

#include <algorithm>

namespace pzt_frontend {
namespace {

constexpr char kTag[] = "pzt_frontend";
constexpr uint16_t kInternalReferenceMv = 2048;
constexpr uint32_t kI2cTimeoutMs = 100;

i2c_master_bus_handle_t s_bus = nullptr;
i2c_master_dev_handle_t s_dac = nullptr;
uint16_t s_threshold_mv[kChannelCount] = {};

// Public channel order is TL/TR/BL/BR.  On the PCB, TL/TR deliberately use
// MCP4728 B/A and TLV1814 channels 2/1 so the two top CMP_IN traces do not
// cross at the comparator.  BL/BR retain channels C/D and 3/4.
constexpr uint8_t kDacChannelForLogical[kChannelCount] = {1, 0, 2, 3};

uint16_t mv_to_code(uint16_t millivolts) {
    const uint32_t bounded = std::min<uint32_t>(millivolts, kInternalReferenceMv);
    const uint32_t rounded =
        (bounded * 4096u + kInternalReferenceMv / 2u) / kInternalReferenceMv;
    return static_cast<uint16_t>(std::min<uint32_t>(rounded, 4095u));
}

esp_err_t ensure_bus() {
    if (s_dac != nullptr) {
        return ESP_OK;
    }

    i2c_master_bus_config_t bus_config = {};
    bus_config.i2c_port = I2C_NUM_0;
    bus_config.sda_io_num = PZT_I2C_SDA;
    bus_config.scl_io_num = PZT_I2C_SCL;
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.glitch_ignore_cnt = 7;
    bus_config.flags.enable_internal_pullup = false;

    esp_err_t err = i2c_new_master_bus(&bus_config, &s_bus);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "I2C bus init failed: %s", esp_err_to_name(err));
        return err;
    }

    i2c_device_config_t device_config = {};
    device_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    device_config.device_address = PZT_DAC_I2C_ADDRESS;
    device_config.scl_speed_hz = 400000;
    err = i2c_master_bus_add_device(s_bus, &device_config, &s_dac);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "MCP4728 add-device failed: %s", esp_err_to_name(err));
        return err;
    }
    return ESP_OK;
}

}  // namespace

esp_err_t set_threshold_mv(uint8_t channel, uint16_t millivolts) {
    if (channel >= kChannelCount) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = ensure_bus();
    if (err != ESP_OK) {
        return err;
    }

    const uint16_t bounded = std::min<uint16_t>(millivolts, kInternalReferenceMv);
    const uint16_t code = mv_to_code(bounded);
    const uint8_t dac_channel = kDacChannelForLogical[channel];

    // MCP4728 multi-write command:
    //   byte0 = 01000 DAC1 DAC0 UDAC (UDAC=0; /LDAC is tied low)
    //   byte1 = VREF PD1 PD0 Gx D11..D8 (internal ref, normal, gain x1)
    //   byte2 = D7..D0
    const uint8_t data[3] = {
        static_cast<uint8_t>(0x40u | (dac_channel << 1u)),
        static_cast<uint8_t>(0x80u | ((code >> 8u) & 0x0fu)),
        static_cast<uint8_t>(code & 0xffu),
    };
    err = i2c_master_transmit(s_dac, data, sizeof(data), kI2cTimeoutMs);
    if (err != ESP_OK) {
        ESP_LOGE(kTag, "MCP4728 logical ch%u / DAC ch%u write failed: %s",
                 channel, dac_channel, esp_err_to_name(err));
        return err;
    }
    s_threshold_mv[channel] = bounded;
    return ESP_OK;
}

uint16_t threshold_mv(uint8_t channel) {
    return channel < kChannelCount ? s_threshold_mv[channel] : 0;
}

esp_err_t init() {
    static constexpr uint16_t kDefaults[kChannelCount] = {
        PZT_THRESHOLD_MV_TL,
        PZT_THRESHOLD_MV_TR,
        PZT_THRESHOLD_MV_BL,
        PZT_THRESHOLD_MV_BR,
    };

    esp_err_t err = ensure_bus();
    if (err != ESP_OK) {
        return err;
    }
    for (uint8_t channel = 0; channel < kChannelCount; ++channel) {
        err = set_threshold_mv(channel, kDefaults[channel]);
        if (err != ESP_OK) {
            return err;
        }
    }
    ESP_LOGI(kTag, "MCP4728 @0x%02X ready: TL/TR/BL/BR=%u/%u/%u/%umV",
             PZT_DAC_I2C_ADDRESS, s_threshold_mv[0], s_threshold_mv[1],
             s_threshold_mv[2], s_threshold_mv[3]);
    return ESP_OK;
}

}  // namespace pzt_frontend
