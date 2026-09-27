revision_library_mode=true;
include <../../../cad/feeder-guide-revision.scad>
probe_kind="fixed";
t=0.85;
module moving_frame(){multmatrix([[1.0, 1.1891946735691472e-14, -8.587686681016685e-15, 0.19900000000012097], [-1.1976759252386256e-14, 0.9999505518889943, -0.009944535026624271, -0.1502772471030619], [8.469002155284566e-15, 0.009944535026624271, 0.9999505518889943, 0.0008406178870963288], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.9999692761786577, -0.007799648916353577, 0.0007824164575485615, 25.031656819862324], [0.007796908814584149, 0.9999636657628905, 0.003446065434538564, -0.23193348170337233], [-0.0008092661295756567, -0.003439859128465283, 0.9999937562092615, -0.16088628334308194], [0.0, 0.0, 0.0, 1.0]]) cam_finger_local();}
module moved_pin(){multmatrix([[0.9999692761786577, -0.007799648916353577, 0.0007824164575485615, 25.031656819862324], [0.007796908814584149, 0.9999636657628905, 0.003446065434538564, -0.23193348170337233], [-0.0008092661295756567, -0.003439859128465283, 0.9999937562092615, -0.16088628334308194], [0.0, 0.0, 0.0, 1.0]]) translate([19.849567190183038, 0, -0.0379427302715518]) cam_pin_local();}
module moved_nut(){multmatrix([[0.9999692761786577, -0.007799648916353577, 0.0007824164575485615, 25.031656819862324], [0.007796908814584149, 0.9999636657628905, 0.003446065434538564, -0.23193348170337233], [-0.0008092661295756567, -0.003439859128465283, 0.9999937562092615, -0.16088628334308194], [0.0, 0.0, 0.0, 1.0]]) translate([19.849567190183038, -4.3, -0.0379427302715518])
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
