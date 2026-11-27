#pragma once

#include <cstdint>

// Hardware-independent control logic. Inputs must be debounced and proved by
// the board adapter; this file does not select a motor driver or sensor pins.
namespace launcher {

enum class State : std::uint8_t {
    Locked = 0,
    Ready = 1,
    Outbound = 2,
    Return = 3,
    Stopping = 4,
    WaitRelease = 5,
    Fault = 6,
};

struct Input {
    bool trigger_pressed = false;
    bool near_home_blocked = false;
    // A one-sample rising event, not the held level of a limit switch.
    bool full_stroke_event = false;
    // Independent proof of the feeder's mechanical zero, not the optical bit.
    bool verified_mechanical_zero = false;
    // Proved stopped after motor disable, not simply "output commanded off".
    bool motor_idle = false;
    // One-sample proof minted only after this cycle's drive-disable command.
    // A held/stuck-high idle level cannot stand in for a fresh stop event.
    bool fresh_stop_event = false;
    bool power_good = false;
    bool cycle_watchdog_expired = false;
};

struct Machine {
    State state = State::Locked;
    bool departed_near_home = false;
};

struct Result {
    Machine machine;
    bool motor_enable = false;
    bool start_event = false;
    bool completed_cycle_event = false;
};

// Pure transition function; a new boot begins from Machine{} with drive off.
// Fault is latched until an external reset. No PWM, braking, power-stage, or
// watchdog time is inferred from the seller's motor listing.
Result step(Machine machine, Input sample);

}  // namespace launcher
