$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-pin-retention/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/candidate.scad>
intersection(){pin_axis_envelope();offset_fixed_metal();}
