feeder_support_library_mode=true;
include <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
probe_kind="fixed";
module moved_frame(){multmatrix([[1.0, -4.12907358305693e-15, -1.654080050109058e-15, 0.19500000000007206], [4.14499596690361e-15, 0.9999525197586501, 0.009744651267568724, 0.1472143343232304], [1.6137651318640464e-15, -0.009744651267568724, 0.9999525197586501, 0.21367012426626353], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(0.85);}
module moved_carrier(){multmatrix([[0.9998803627581198, -0.015464905373111544, -0.000311243460284351, 25.164686629156417], [0.015468037066507958, 0.9996779247424976, 0.02011930942757191, -0.31709410304180485], [-3.016652751733294e-15, -0.02012171673426385, 0.9997975377623541, -0.10528320496088095], [0.0, 0.0, 0.0, 1.0]]) cam_finger_local();}
module moved_pin(){multmatrix([[0.9998803627581198, -0.015464905373111544, -0.000311243460284351, 25.164686629156417], [0.015468037066507958, 0.9996779247424976, 0.02011930942757191, -0.31709410304180485], [-3.016652751733294e-15, -0.02012171673426385, 0.9997975377623541, -0.10528320496088095], [0.0, 0.0, 0.0, 1.0]]) translate([19.915562523131005, 0, -0.14625000000001037]) cam_pin_local();}
module moved_nut(){multmatrix([[0.9998803627581198, -0.015464905373111544, -0.000311243460284351, 25.164686629156417], [0.015468037066507958, 0.9996779247424976, 0.02011930942757191, -0.31709410304180485], [-3.016652751733294e-15, -0.02012171673426385, 0.9997975377623541, -0.10528320496088095], [0.0, 0.0, 0.0, 1.0]]) translate([19.915562523131005, -4.4, -0.14625000000001037])
 rotate([-90,0,0]) difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02]) cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&!rear)){
 cam_finger(side,rear,0.85);cam_pin(side,rear,0.85,0);cam_follower_nut(side,rear,0.85);}}
module fixed(){feeder_body_full();feeder_support_fixed();feeder_cap_hardware();feeder_mount_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="view"){color([.6,.65,.68,.16])feeder_body_full();
 color([.72,.72,.72])feeder_support_fixed();color([.1,.4,.8])moved_frame();
 color([1,.4,.1])followers();}
