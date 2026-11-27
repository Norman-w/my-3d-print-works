#include "point_shot_core.h"

namespace launcher {
namespace {

bool active(State state) {
    return state == State::Outbound || state == State::Return;
}

bool valid(State state) {
    return static_cast<unsigned>(state) <= static_cast<unsigned>(State::Fault);
}

}  // namespace

Result step(Machine machine, Input sample) {
    Machine next = machine;
    if (!valid(machine.state)) {
        next = {State::Fault, false};
    } else if (machine.state == State::Fault) {
        next = machine;
    } else if (!sample.power_good ||
               (sample.verified_mechanical_zero && !sample.near_home_blocked) ||
               (sample.fresh_stop_event &&
                (machine.state != State::Stopping || !sample.motor_idle)) ||
               ((active(machine.state) || machine.state == State::Stopping) &&
                sample.cycle_watchdog_expired)) {
        next = {State::Fault, false};
    } else {
        switch (machine.state) {
            case State::Locked:
                if (!sample.trigger_pressed && sample.near_home_blocked &&
                    sample.verified_mechanical_zero && sample.motor_idle &&
                    !sample.full_stroke_event) {
                    next = {State::Ready, false};
                }
                break;
            case State::Ready:
                if (!sample.near_home_blocked || !sample.verified_mechanical_zero ||
                    !sample.motor_idle || sample.full_stroke_event) {
                    next = {State::Fault, false};
                } else if (sample.trigger_pressed) {
                    next = {State::Outbound, false};
                }
                break;
            case State::Outbound: {
                const bool departed = machine.departed_near_home ||
                                      !sample.near_home_blocked;
                if (sample.full_stroke_event && !departed) {
                    next = {State::Fault, false};
                } else if (sample.full_stroke_event) {
                    next = {State::Return, true};
                } else {
                    next = {State::Outbound, departed};
                }
                break;
            }
            case State::Return:
                if (sample.full_stroke_event) {
                    next = {State::Fault, false};
                } else if (sample.verified_mechanical_zero &&
                           sample.near_home_blocked) {
                    next = {State::Stopping, true};
                }
                break;
            case State::Stopping:
                if (!sample.near_home_blocked || !sample.verified_mechanical_zero ||
                    sample.full_stroke_event) {
                    next = {State::Fault, false};
                } else if (sample.motor_idle && sample.fresh_stop_event) {
                    next = {sample.trigger_pressed ? State::WaitRelease : State::Ready,
                            false};
                }
                break;
            case State::WaitRelease:
                if (!sample.near_home_blocked || !sample.verified_mechanical_zero ||
                    !sample.motor_idle || sample.full_stroke_event) {
                    next = {State::Fault, false};
                } else if (!sample.trigger_pressed) {
                    next = {State::Ready, false};
                }
                break;
            case State::Fault:
                break;
        }
    }
    return {
        next,
        active(next.state),
        machine.state == State::Ready && next.state == State::Outbound,
        machine.state == State::Stopping &&
            (next.state == State::Ready || next.state == State::WaitRelease),
    };
}

}  // namespace launcher
