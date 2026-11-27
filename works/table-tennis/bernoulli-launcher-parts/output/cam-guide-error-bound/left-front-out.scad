cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.85;
module moved_frame(){multmatrix([[1.0, 9.817472540569275e-09, -2.627611457920186e-09, 0.0002498043707441682], [-9.843117387324923e-09, 0.9999505521718284, -0.009944506586829, -0.1502768141157142], [2.529851607894609e-09, 0.009944506586829025, 0.9999505521718284, 0.0008406130789175847], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[-0.9999681746922272, 0.00793216526905441, -0.0008546091737927955, -24.83351358863793], [0.00792913619215389, 0.999962469005202, 0.0034913292979512366, -0.2360125034678354], [-0.0008822709004603804, -0.0034844418727917256, 0.9999935401105815, -0.15864239617762899], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[-0.9999681746922272, 0.00793216526905441, -0.0008546091737927955, -24.83351358863793], [0.00792913619215389, 0.999962469005202, 0.0034913292979512366, -0.2360125034678354], [-0.0008822709004603804, -0.0034844418727917256, 0.9999935401105815, -0.15864239617762899], [0.0, 0.0, 0.0, 1.0]])translate([19.850142122292304, 0, -0.03893854189582336])cam_pin_local();}
module moved_nut(){multmatrix([[-0.9999681746922272, 0.00793216526905441, -0.0008546091737927955, -24.83351358863793], [0.00792913619215389, 0.999962469005202, 0.0034913292979512366, -0.2360125034678354], [-0.0008822709004603804, -0.0034844418727917256, 0.9999935401105815, -0.15864239617762899], [0.0, 0.0, 0.0, 1.0]])translate([19.850142122292304, -4.3, -0.03893854189582336])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==-1&&rear==false)){
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
