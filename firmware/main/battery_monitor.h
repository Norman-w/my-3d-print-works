#pragma once

#include <cstdint>
#include "esp_err.h"

namespace battery_monitor {

struct Telemetry {
    bool valid;
    bool calibrated;
    int cell_mv;
    uint8_t percent_estimate;
};

// Configure GPIO9 / ADC1 through the IDF GPIO-to-channel map and start a
// low-rate voltage/estimated-capacity telemetry task.  Charging state stays
// on the tail board's physical LED and is intentionally absent from telemetry.
esp_err_t init();

Telemetry read();

// Exposed for deterministic host/unit checks of the documented estimate.
uint8_t percent_from_cell_mv(int cell_mv);

}  // namespace battery_monitor
