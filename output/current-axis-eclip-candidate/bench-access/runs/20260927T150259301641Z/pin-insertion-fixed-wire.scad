$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-eclip-candidate/bench-access/probes.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-eclip-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-retention-review/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
intersection(){eb_pin_insertion();union(){eb_fixed();ci_local_cable(0);}}