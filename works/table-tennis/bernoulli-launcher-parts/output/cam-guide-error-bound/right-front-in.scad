cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.95;
module moved_frame(){multmatrix([[0.9999999999999997, 2.5109338847122556e-08, -6.046713379263137e-10, 0.000249451679823405], [-2.510208414152387e-08, 0.9999505528094291, 0.009944442473883658, 0.1480905064348269], [8.543398143498971e-10, -0.00994444247388364, 0.9999505528094295, 0.0009394966208411404], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.9999366614349929, 0.01125491529245479, 5.397995670808856e-09, 24.64547190938564], [-0.011254915292454806, 0.9999366614349929, 2.8759238347989206e-09, 0.2151501156033447], [-5.365285490360938e-09, -2.9364956619341464e-09, 1.0, 0.19900005653431257], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[0.9999366614349929, 0.01125491529245479, 5.397995670808856e-09, 24.64547190938564], [-0.011254915292454806, 0.9999366614349929, 2.8759238347989206e-09, 0.2151501156033447], [-5.365285490360938e-09, -2.9364956619341464e-09, 1.0, 0.19900005653431257], [0.0, 0.0, 0.0, 1.0]])translate([20.172339054571886, 0, 1.3484075294621854e-09])cam_pin_local();}
module moved_nut(){multmatrix([[0.9999366614349929, 0.01125491529245479, 5.397995670808856e-09, 24.64547190938564], [-0.011254915292454806, 0.9999366614349929, 2.8759238347989206e-09, 0.2151501156033447], [-5.365285490360938e-09, -2.9364956619341464e-09, 1.0, 0.19900005653431257], [0.0, 0.0, 0.0, 1.0]])translate([20.172339054571886, -4.3, 1.3484075294621854e-09])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&rear==false)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=0.0);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
