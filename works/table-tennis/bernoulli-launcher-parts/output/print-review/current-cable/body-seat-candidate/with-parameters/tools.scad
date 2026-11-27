include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-service-contract.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/body-seat-candidate/candidate.scad>
module added(){difference(){cip_body();ci_body();}}
intersection(){added();union(){cs_input_mount_tools();cs_input_adjuster_tools();cs_input_stop_locknut_tool();for(s=[16,20,22])cs_input_stop_tools(s);}}
