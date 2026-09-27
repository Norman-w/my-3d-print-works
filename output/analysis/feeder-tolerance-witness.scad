feeder_support_library_mode=true;
include <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
probe_kind="fixed";
module moved_frame(){multmatrix([[0.999999616981381, -0.0008752354484178834, -3.2585585695891804e-08, 0.21648447597386183], [0.000875211185547896, 0.999972171292421, -0.007408822180454476, -0.11173727088391355], [6.51704848223959e-06, 0.007408819314218366, 0.9999725543003154, 0.0004665768946381377], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(0.85);}
module moved_carrier(){multmatrix([[0.9998700703913594, -0.016112636653816324, 0.00047463211014597877, 25.13102074198688], [0.016099976952147668, 0.9996716639411609, 0.01993376671005518, -0.33004938278841567], [-0.0007956618114505937, -0.019923535157513713, 0.9998011900718607, -0.08786485677525889], [0.0, 0.0, 0.0, 1.0]]) cam_finger_local();}
module moved_pin(){multmatrix([[0.9998700703913594, -0.016112636653816324, 0.00047463211014597877, 25.13102074198688], [0.016099976952147668, 0.9996716639411609, 0.01993376671005518, -0.33004938278841567], [-0.0007956618114505937, -0.019923535157513713, 0.9998011900718607, -0.08786485677525889], [0.0, 0.0, 0.0, 1.0]]) translate([19.827660944646883, 0, 1.6331422824572863e-14]) cam_pin_local();}
module moved_nut(){multmatrix([[0.9998700703913594, -0.016112636653816324, 0.00047463211014597877, 25.13102074198688], [0.016099976952147668, 0.9996716639411609, 0.01993376671005518, -0.33004938278841567], [-0.0007956618114505937, -0.019923535157513713, 0.9998011900718607, -0.08786485677525889], [0.0, 0.0, 0.0, 1.0]]) translate([19.827660944646883, -4.3, 1.6331422824572863e-14])
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
