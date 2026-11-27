$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-eclip-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-retention-review/candidate.scad>
intersection(){ec_clip_space();offset_fixed_metal();}