cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=0.05;
module moved_frame(){multmatrix([[1.0, 8.389443385187168e-09, -4.167505768750089e-09, 0.00024359040342031757], [-8.430472335196085e-09, 0.9999505521689163, -0.009944506879649633, -0.15026890166367618], [4.083870817168371e-09, 0.009944506879649668, 0.9999505521689163, 4.9447831083737626e-05], [0.0, 0.0, 0.0, 1.0]]) feeder_carriage(t);}
module moved_carrier(){multmatrix([[0.9999366423303966, 0.011256612500068767, 1.8923151145292105e-07, 24.644114279176005], [-0.011256612500104306, 0.9999366423303966, 1.8781188577131206e-07, 0.2151972086373664], [-1.8710539656430496e-07, -1.8993009224514033e-07, 0.9999999999999645, -28.6989939565146], [0.0, 0.0, 0.0, 1.0]])cam_finger_local();}
module moved_pin(){multmatrix([[0.9999366423303966, 0.011256612500068767, 1.8923151145292105e-07, 24.644114279176005], [-0.011256612500104306, 0.9999366423303966, 1.8781188577131206e-07, 0.2151972086373664], [-1.8710539656430496e-07, -1.8993009224514033e-07, 0.9999999999999645, -28.6989939565146], [0.0, 0.0, 0.0, 1.0]])translate([20.17233818791326, 0, -1.5024509665392862e-06])cam_pin_local();}
module moved_nut(){multmatrix([[0.9999366423303966, 0.011256612500068767, 1.8923151145292105e-07, 24.644114279176005], [-0.011256612500104306, 0.9999366423303966, 1.8781188577131206e-07, 0.2151972086373664], [-1.8710539656430496e-07, -1.8993009224514033e-07, 0.9999999999999645, -28.6989939565146], [0.0, 0.0, 0.0, 1.0]])translate([20.17233818791326, -4.3, -1.5024509665392862e-06])
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&rear==true)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);
 translate([side*(cam_gate_r(rear,t)+cam_follower_offset),
     -cam_carrier_width/2+.2,cam_gate_z(rear)])rotate([-90,0,0])
 difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=0.00010321620216422981);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
