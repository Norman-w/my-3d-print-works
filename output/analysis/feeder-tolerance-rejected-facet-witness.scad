feeder_support_library_mode=true;
include <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
probe_kind="fixed";
module moved_frame(){multmatrix([[0.9999996268479527, -0.000863888855261989, -3.230596093151613e-08, 0.21625807482653242], [0.0008638646939171782, 0.999971937030679, -0.007441699328956503, -0.11223613197910307], [6.461106168826471e-06, 0.007441696524163184, 0.9999723101721849, 0.00047072707285522597], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(0.85);}
module moved_carrier(){multmatrix([[0.9998682075096877, -0.016229916105295606, 0.00039678026524663955, 25.13190168803672], [0.016218946601223513, 0.999674220865666, 0.019707813368563552, -0.33248825757815526], [-0.0007165071601059164, -0.019698780668826646, 0.9998057034532515, -0.09107443591708234], [0.0, 0.0, 0.0, 1.0]]) cam_finger_local();}
module moved_pin(){multmatrix([[0.9998682075096877, -0.016229916105295606, 0.00039678026524663955, 25.13190168803672], [0.016218946601223513, 0.999674220865666, 0.019707813368563552, -0.33248825757815526], [-0.0007165071601059164, -0.019698780668826646, 0.9998057034532515, -0.09107443591708234], [0.0, 0.0, 0.0, 1.0]]) translate([19.827660944647047, 0, -1.6422401723570468e-13]) cam_pin_local();}
module moved_nut(){multmatrix([[0.9998682075096877, -0.016229916105295606, 0.00039678026524663955, 25.13190168803672], [0.016218946601223513, 0.999674220865666, 0.019707813368563552, -0.33248825757815526], [-0.0007165071601059164, -0.019698780668826646, 0.9998057034532515, -0.09107443591708234], [0.0, 0.0, 0.0, 1.0]]) translate([19.827660944647047, -4.3, -1.6422401723570468e-13])
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
