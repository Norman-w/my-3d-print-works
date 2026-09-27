$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-pin-retention/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/route/candidate.scad>
intersection(){ci_to_cad()pin_axis_envelope();union(){cr_housing();cr_core();}}
