use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-eclip-adoption/20260927T151752917841Z/cad-review/frozen-baseline/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-eclip-adoption/20260927T151752917841Z/cad-review/frozen-baseline/output/current-axis-offset-candidate/route/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-eclip-adoption/20260927T151752917841Z/cad-review/frozen-baseline/cad/cable-contract-codec.scad>
echo(cc_pack([ci_spec(),[for(d=[-2,0,2])for(u=[0,10,20,22])[d,u,ci_angle(u,d),ci_path_length(ci_angle(u,d),d),ci_takeup(ci_angle(u,d),d),ci_B(ci_angle(u,d)),ci_T(ci_angle(u,d))]]]));
