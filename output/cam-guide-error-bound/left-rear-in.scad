cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.05;
module moved_frame(){multmatrix([[1.0, -4.9305124158782164e-14, 2.2746043511539218e-14, 0.0997499999879982], [4.952888493994637e-14, 0.9999505518889946, -0.009944535026585568, -0.1502693260445578], [-2.2254602228467568e-14, 0.009944535026585568, 0.9999505518889946, 4.944811100537905e-05], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[-0.9999351679500228, -0.011386829969734648, -3.480886776282356e-11, -24.543604847492233], [-0.011386829969734648, 0.9999351679500228, 3.036837548350446e-09, 0.21883695703353614], [-2.2665822379676483e-13, -3.037037026605393e-09, 1.0, -28.698999981898076], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[-0.9999351679500228, -0.011386829969734648, -3.480886776282356e-11, -24.543604847492233], [-0.011386829969734648, 0.9999351679500228, 3.036837548350446e-09, 0.21883695703353614], [-2.2665822379676483e-13, -3.037037026605393e-09, 1.0, -28.698999981898076], [0.0, 0.0, 0.0, 1.0]])translate([20.172339031694655, 0, -4.0979125434657434e-08])cam_pin_local();}
module moved_nut(){multmatrix([[-0.9999351679500228, -0.011386829969734648, -3.480886776282356e-11, -24.543604847492233], [-0.011386829969734648, 0.9999351679500228, 3.036837548350446e-09, 0.21883695703353614], [-2.2665822379676483e-13, -3.037037026605393e-09, 1.0, -28.698999981898076], [0.0, 0.0, 0.0, 1.0]])translate([20.172339031694655, -4.3, -4.0979125434657434e-08])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==-1&&rear==true)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=-4.918419677452476e-07);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
