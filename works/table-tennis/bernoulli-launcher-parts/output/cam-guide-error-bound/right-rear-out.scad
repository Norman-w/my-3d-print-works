cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.15;
module moved_frame(){multmatrix([[0.9999999335482407, -0.0003645449413533053, -3.2403715551979967e-06, 0.10735329162584827], [0.0003645593425960999, 0.9999604303979158, 0.00888846077230171, 0.13246127238454425], [-7.597492924714262e-14, -0.008888461362955577, 0.9999604968470501, 0.00011850945884983588], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.99996856449045, -0.007884569631365789, -0.0008388042899495519, 24.931256694376884], [0.007881633477118693, 0.9999629950858581, -0.0034479432496183422, -0.23451125968000802], [0.0008659587987054338, 0.003441223713792974, 0.9999937040275356, -28.340707042234783], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[0.99996856449045, -0.007884569631365789, -0.0008388042899495519, 24.931256694376884], [0.007881633477118693, 0.9999629950858581, -0.0034479432496183422, -0.23451125968000802], [0.0008659587987054338, 0.003441223713792974, 0.9999937040275356, -28.340707042234783], [0.0, 0.0, 0.0, 1.0]])translate([19.84983953807359, 0, 0.03841445065271303])cam_pin_local();}
module moved_nut(){multmatrix([[0.99996856449045, -0.007884569631365789, -0.0008388042899495519, 24.931256694376884], [0.007881633477118693, 0.9999629950858581, -0.0034479432496183422, -0.23451125968000802], [0.0008659587987054338, 0.003441223713792974, 0.9999937040275356, -28.340707042234783], [0.0, 0.0, 0.0, 1.0]])translate([19.84983953807359, -4.3, 0.03841445065271303])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&rear==true)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=4.224573485073587e-07);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
