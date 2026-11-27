#include "point_shot_core.h"

#include <iostream>

// Host-only conformance runner. Each line supplies an entire prior machine
// and sensor sample; no GPIO is accessed and no motor can be energized.
int main() {
    int state, departed, trigger, near_home, full_stroke, zero, idle,
        fresh_stop, power, watchdog;
    while (std::cin >> state >> departed >> trigger >> near_home >> full_stroke >>
           zero >> idle >> fresh_stop >> power >> watchdog) {
        launcher::Machine machine{static_cast<launcher::State>(state),
                                  departed != 0};
        launcher::Input sample{trigger != 0, near_home != 0, full_stroke != 0,
                               zero != 0, idle != 0, fresh_stop != 0, power != 0,
                               watchdog != 0};
        const launcher::Result result = launcher::step(machine, sample);
        std::cout << static_cast<unsigned>(result.machine.state) << ' '
                  << result.machine.departed_near_home << ' '
                  << result.motor_enable << ' ' << result.start_event << ' '
                  << result.completed_cycle_event << '\n';
    }
    return std::cin.eof() ? 0 : 1;
}
