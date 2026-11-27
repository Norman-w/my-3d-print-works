$fn=72;
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-eclip-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-retention-review/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/route/candidate.scad>
intersection(){ci_to_cad()ec_clip_space();union(){cr_housing();cr_wire();}}