cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.95;
module moved_frame(){multmatrix([[1.0, -3.634301149266899e-15, 5.596848947678868e-15, 0.09974999999987368], [3.578463379541218e-15, 0.9999505518889941, 0.009944535026643223, 0.14809147806155226], [-5.632713629147074e-15, -0.009944535026643223, 0.9999505518889941, 0.0009395141091133041], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[-0.9999351880852734, -0.01138506165415621, 4.505995038696053e-17, -24.544954466760068], [-0.01138506165415621, 0.9999351880852734, -1.0672248936960382e-14, 0.21878753774557633], [-7.64471821704986e-17, 1.0672070258385629e-14, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[-0.9999351880852734, -0.01138506165415621, 4.505995038696053e-17, -24.544954466760068], [-0.01138506165415621, 0.9999351880852734, -1.0672248936960382e-14, 0.21878753774557633], [-7.64471821704986e-17, 1.0672070258385629e-14, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]])translate([20.172339055353103, 0, 1.6872973741367915e-16])cam_pin_local();}
module moved_nut(){multmatrix([[-0.9999351880852734, -0.01138506165415621, 4.505995038696053e-17, -24.544954466760068], [-0.01138506165415621, 0.9999351880852734, -1.0672248936960382e-14, 0.21878753774557633], [-7.64471821704986e-17, 1.0672070258385629e-14, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]])translate([20.172339055353103, -4.3, 1.6872973741367915e-16])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==-1&&rear==false)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=0.0009922185944664483);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
