$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-pin-retention/bench-access/probes.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-pin-retention/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-retention-review/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
intersection(){bench_pin_insertion();union(){bench_fixed();ci_local_cable(0);}}
