// ISOLATED SERVICE STUDY, mm, INPUT LOCAL coordinates. No production changes.
use <../current-axis-shoulder-candidate/candidate.scad>
use <../current-axis-through-candidate/candidate.scad>
use <../current-axis-retention-review/candidate.scad>
use <../../cad/cable-trigger-input.scad>
$fn=72;
at_case="head-bench";
at_k=1/cos(180/72);

// Bench assembly excludes ONLY the shoulder-axis group being assembled and
// the four host bolts not yet installed. All side screws, adjuster, stop,
// terminal fasteners, bush/thrust stack, and modeled internal wire remain.
module at_bench_neighbors(){
 shoulder_plastics();ar_rotor(0);other_fixed_metal();ci_local_cable(0,0);
}
// SW5 L-key BUDGET, not purchased tool: long leg 60, short arm <=25,
// transverse/bend radius <=4, straight shank circumscribed OD <=5.8.
// Head-top 17.3..18.75, assumed 2.5 engagement => tip 14.8..16.25.
// Continuous +Z insertion/removal 40 plus complete rotation of short arm.
module at_head_tool_sweep(){
 translate([0,0,14.8])cylinder(h=105.45,d=5.8*at_k);
 translate([0,0,70.8])cylinder(h=49.45,d=58*at_k);
}
// SW10 deep-socket BUDGET, full rotational outer envelope. Mouth stays
// .5 below nut's washer-facing end. Across accepted axis/washer bounds,
// mouth is -15.35..-13.9. Socket 40 long, OD<=14, entry from -Z by 40.
// Back handle swept radius<=70, axial half thickness<=6; no hand envelope.
module at_nut_tool_sweep(){
 translate([0,0,-95.35])cylinder(h=81.45,d=14*at_k);
 translate([0,0,-116.35])cylinder(h=53.45,d=140*at_k);
}
// Exact nominal drive-fit geometries. Target axes/nut may intentionally
// contact under torque, but the nominal clearance geometry must not penetrate.
module at_head_key_nominal(){
 ci_zhex(0,0,15.5,62.5,4.98);
 hull(){translate([0,0,78])sphere(d=5.8);translate([25,0,78])sphere(d=5.8);}
}
module at_nut_socket_nominal(){difference(){
 translate([0,0,-54.6])cylinder(h=40,d=14);
 ci_zhex(0,0,-34.6,20.01,10.2);
 translate([0,0,-54.61])cylinder(h=40.02,d=8);
}}
// Full +Z insertion sweep of shoulder shaft alone. Washer/nut fitted later
// from -Z. Encloses all axial float, L/F/head acceptance and 40 mm travel.
// It deliberately fills the socket: the shoulder itself is not a neighbor.
module at_shoulder_insert_sweep(){
 translate([0,0,-25.55])cylinder(h=66.55,d=6*at_k);
 translate([0,0,-13.05])cylinder(h=65.6,d=7.995*at_k);
 translate([0,0,11.5])cylinder(h=47.25,d=13.2*at_k);
}
module at_host(){ci_from_cad()import("../cable-scene-export/20260927T091627124663Z/feeder__beam-grip.stl");}
if(at_case=="head-bench")intersection(){at_head_tool_sweep();at_bench_neighbors();}
else if(at_case=="nut-bench")intersection(){at_nut_tool_sweep();at_bench_neighbors();}
else if(at_case=="tools-mutual")intersection(){at_head_tool_sweep();at_nut_tool_sweep();}
else if(at_case=="head-drive-fit")intersection(){at_head_key_nominal();shoulder_axis();}
else if(at_case=="nut-drive-fit")intersection(){at_nut_socket_nominal();shoulder_axis();}
else if(at_case=="shaft-insertion")intersection(){at_shoulder_insert_sweep();at_bench_neighbors();}
else if(at_case=="installed-head-positive")intersection(){at_head_tool_sweep();at_host();}
else if(at_case=="display"){
 color([.2,.5,.7,.35])at_bench_neighbors();color("silver")shoulder_axis();
 color([.9,.3,.2,.4])at_head_tool_sweep();color([.2,.8,.4,.3])at_nut_tool_sweep();
}
