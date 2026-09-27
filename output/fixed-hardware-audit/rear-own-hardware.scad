include <../../cad/parameters.scad>
use <../../cad/feeder-hardware-clearance.scad>
use <../../cad/feeder-guide-revision.scad>
use <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
use <../../cad/feeder-complete-hardware.scad>
use <../../cad/review-launcher-baseline33.scad>
module audit_shafts(){
 for(y=[-40,40],z=[-72,-46,-10,16])
  translate([-8.2,y,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
 for(s=[-1,1],z=[-45,16])scale([s,1,1])
  translate([32,-14,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
}
module audit_bosses(){difference(){union(){body_split_bosses();body_mount_bosses();}
 body_split_fastener_cuts();body_side_cuts();}}
module audit_protected(){
 // Keep the three holes and full outer washer bearing footprints unchanged.
 for(z=[-10,0,10])translate([51,-17.51,z])rotate([-90,0,0])cylinder(h=4.02,d=7,$fn=72);
 // Both positive rear gib stroke stops remain exactly the old geometry.
 translate([45.9,-13.51,-6.6])cube([9.2,3,13.2]);
}
module audit_hex_key_drivers(){
 for(s=[-1,1],z=[-45,16])scale([s,1,1])
  hc_x_cylinder(47.05,-14,z,45,3/cos(180/72));
}
module audit_mount_withdrawal(){
 for(s=[-1,1])scale([s,1,1])hc_mount_sweep_local(false,0,35);
}
intersection(){hc_keeper_local(true);revision_hardware_local(0,.9);}
