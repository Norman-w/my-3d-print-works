#pragma once

#include <cstdint>

#include "esp_err.h"

namespace pzt_frontend {

constexpr uint8_t kChannelCount = 4;

/** Initialize I2C and program all four MCP4728 thresholds. */
esp_err_t init();

/** Set one channel threshold in millivolts (0..2048mV, internal reference). */
esp_err_t set_threshold_mv(uint8_t channel, uint16_t millivolts);

/** Last successfully programmed threshold, or 0 if not initialized. */
uint16_t threshold_mv(uint8_t channel);

}  // namespace pzt_frontend
