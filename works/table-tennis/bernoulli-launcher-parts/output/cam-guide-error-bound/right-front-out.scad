cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.85;
module moved_frame(){multmatrix([[1.0, -2.2523760105738262e-14, 1.0135621981983814e-14, 0.09974999999977113], [2.2623440396164998e-14, 0.9999505518889941, -0.009944535026649397, -0.15027724710318002], [-9.911132473319573e-15, 0.009944535026649397, 0.9999505518889941, 0.0008406178870998815], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.9999687226366685, -0.007866548704374131, 0.0008192434748236872, 24.932582916297378], [0.00786366371709889, 0.9999630701849626, 0.0034671399176039544, -0.2340852295215162], [-0.0008464876453404025, -0.0034605892194205894, 0.9999936538703237, -0.15975120691987868], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[0.9999687226366685, -0.007866548704374131, 0.0008192434748236872, 24.932582916297378], [0.00786366371709889, 0.9999630701849626, 0.0034671399176039544, -0.2340852295215162], [-0.0008464876453404025, -0.0034605892194205894, 0.9999936538703237, -0.15975120691987868], [0.0, 0.0, 0.0, 1.0]])translate([19.84984985447855, 0, -0.038432319192871475])cam_pin_local();}
module moved_nut(){multmatrix([[0.9999687226366685, -0.007866548704374131, 0.0008192434748236872, 24.932582916297378], [0.00786366371709889, 0.9999630701849626, 0.0034671399176039544, -0.2340852295215162], [-0.0008464876453404025, -0.0034605892194205894, 0.9999936538703237, -0.15975120691987868], [0.0, 0.0, 0.0, 1.0]])translate([19.84984985447855, -4.3, -0.038432319192871475])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&rear==false)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=0.0008409277146662425);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
