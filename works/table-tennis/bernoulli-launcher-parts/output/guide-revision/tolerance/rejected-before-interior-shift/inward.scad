revision_library_mode=true;
include <../../../cad/feeder-guide-revision.scad>
probe_kind="fixed";
t=0.95;
module moving_frame(){multmatrix([[1.0, -8.314853809202986e-16, -1.2370012804159423e-14, -0.19899999999977297], [9.544582911498902e-16, 0.9999505518889941, 0.009944535026644736, 0.14809147806147732], [1.2361132394898433e-14, -0.009944535026644736, 0.9999505518889941, 0.0009395141091133041], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.999933662373574, 0.011518283386491652, 1.7715382971813877e-15, 24.44441383777459], [-0.011518283386491652, 0.999933662373574, 3.732089086350766e-16, 0.2227118435838444], [-1.7671220515636075e-15, -3.9358923097887476e-16, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]]) cam_finger_local();}
module moved_pin(){multmatrix([[0.999933662373574, 0.011518283386491652, 1.7715382971813877e-15, 24.44441383777459], [-0.011518283386491652, 0.999933662373574, 3.732089086350766e-16, 0.2227118435838444], [-1.7671220515636075e-15, -3.9358923097887476e-16, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]]) translate([20.172339055353103, 0, 1.0433845235996837e-16]) cam_pin_local();}
module moved_nut(){multmatrix([[0.999933662373574, 0.011518283386491652, 1.7715382971813877e-15, 24.44441383777459], [-0.011518283386491652, 0.999933662373574, 3.732089086350766e-16, 0.2227118435838444], [-1.7671220515636075e-15, -3.9358923097887476e-16, 1.0, 0.1989999999999999], [0.0, 0.0, 0.0, 1.0]]) translate([20.172339055353103, -4.3, 1.0433845235996837e-16])
 rotate([-90,0,0]) difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02]) cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&!rear)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);cam_follower_nut(side,rear,t);}}
module fixed(){feeder_body_full();revision_fixed();revision_gibs();
 feeder_cap_hardware();feeder_mount_hardware();
 for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g);}
if(probe_kind=="fixed")intersection(){fixed();union(){moving_frame();followers();}}
else if(probe_kind=="cam")intersection(){moving_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){revision_fixed();revision_gibs(revision_travel+.1);}
else assert(false,"unknown probe");
