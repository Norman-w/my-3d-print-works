cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.15;
module moved_frame(){multmatrix([[0.9999998449637312, 0.0005568223318514619, 4.626476501273647e-06, -0.011382440465648165], [-0.0005568415514037054, 0.9999651382810237, 0.008331395447321591, 0.12421218855427403], [1.2791826204252551e-08, -0.00833139673186748, 0.9999652933119709, 0.00010412006408699881], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[-0.9999679475954327, 0.007957675202188663, 0.000882715783520568, -24.8322033174524], [0.00795457299576878, 0.9999623622890517, -0.003463924617306263, -0.23661463724695064], [0.0009102473471484472, 0.003456791963058507, 0.9999936109991359, -28.342016804734236], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[-0.9999679475954327, 0.007957675202188663, 0.000882715783520568, -24.8322033174524], [0.00795457299576878, 0.9999623622890517, -0.003463924617306263, -0.23661463724695064], [0.0009102473471484472, 0.003456791963058507, 0.9999936109991359, -28.342016804734236], [0.0, 0.0, 0.0, 1.0]])translate([19.850128226156766, 0, 0.03891447308286008])cam_pin_local();}
module moved_nut(){multmatrix([[-0.9999679475954327, 0.007957675202188663, 0.000882715783520568, -24.8322033174524], [0.00795457299576878, 0.9999623622890517, -0.003463924617306263, -0.23661463724695064], [0.0009102473471484472, 0.003456791963058507, 0.9999936109991359, -28.342016804734236], [0.0, 0.0, 0.0, 1.0]])translate([19.850128226156766, -4.3, 0.03891447308286008])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==-1&&rear==true)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=0.0008535265686656438);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
