// Read-only native parameter/pose audit. No model mesh or collision claim.
use <../../cad/cable-trigger-input.scad>
use <../../cad/cable-output-interface.scad>
use <../../cad/cam-study.scad>
use <../../cad/feeder-return-spring.scad>
for(t=[0,.5,1])echo("POSE",[
 t, -ci_angle(20*t),
 ci_local_to_cad([-36*sin(ci_angle(20*t)),-36*cos(ci_angle(20*t)),2]),
 [0,0,20*t],
 [cam_gate_r(false,t),cam_gate_r(true,t)],
 rs_top(t),co_A(t)]);
