// Pure inlet clamp library: parameters, parts and hardware only.
// mm, +Z ball feed. Public: ir_rear(), ir_front(closure),
// ir_backplate(), ir_hardware(closure). Review/exports are separate.
// Soft liner and smooth hose are nominal reference envelopes, NOT purchased parts.
include <parameters.scad>

ir_closure=0;
ir_z0=-123;
ir_z1=-101;
ir_z=-112;
ir_id=61;
ir_od=73;
ir_split=1.2;
ir_travel=2;
ir_pad_t=3; // Undeformed display ONLY; no hardness/force assumption.
ir_ear_x=43;
ir_key_x=10.5;
ir_key_z=-142;
ir_key_w=2.6;
ir_key_h=21.2;
ir_key_depth=5.8;
ir_eps=.02;
$fn=72;
assert(ir_closure>=0&&ir_closure<=ir_travel);
assert(ir_z0>=-126&&ir_z1<=-98);
assert(abs(2*ir_split-ir_travel-.4)<1e-9);

module ir_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module ir_ycyl(x,z,y0,h,d,fn=72){translate([x,y0,z])rotate([-90,0,0])cylinder(h=h,d=d,$fn=fn);}
module ir_yhex(x,z,y0,h,af){translate([x,y0,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module ir_ring(od,id,z0=ir_z0,z1=ir_z1){difference(){translate([0,0,z0])cylinder(h=z1-z0,d=od);translate([0,0,z0-ir_eps])cylinder(h=z1-z0+2*ir_eps,d=id);}}
module ir_half(positive=false){ir_box(-100,100,positive?ir_split:-100,positive?100:-ir_split,-180,0);}
module ir_collar_blank(){union(){
 intersection(){ir_ring(ir_od,ir_id);ir_half(false);}
 for(s=[-1,1])hull(){
  translate([s*30,-6,ir_z])cube([8,8,ir_z1-ir_z0],center=true);
  translate([s*ir_ear_x,-6.6,ir_z])cube([12,10.8,ir_z1-ir_z0],center=true);
 }
}}
module ir_collar_rear(){difference(){
 ir_collar_blank();
 translate([0,0,ir_z0-ir_eps])cylinder(h=ir_z1-ir_z0+2*ir_eps,d=ir_id);
 for(x=[-ir_ear_x,ir_ear_x]){
  ir_ycyl(x,ir_z,-20,45,4.5);
  // Axial -Y insertion: actual M4 AF7 x3.2 sits against Y=-8.4.
  ir_yhex(x,ir_z,-12-ir_eps,3.6+ir_eps,7.4);
 }
}}
module ir_front_raw(){difference(){
 union(){
  mirror([0,1,0])ir_collar_blank();
  // Broad 0.4 mm raised stops on the ear face. They contact rear Y=-1.2
  // at closure=2; this is a physical stop, not only a parameter assertion.
  for(x=[-ir_ear_x,ir_ear_x])ir_box(x-6,x+6,.8,1.21,ir_z0,ir_z1);
 }
 translate([0,0,ir_z0-ir_eps])cylinder(h=ir_z1-ir_z0+2*ir_eps,d=ir_id);
 for(x=[-ir_ear_x,ir_ear_x])ir_ycyl(x,ir_z,-20,45,4.5);
}}
module ir_front(closure=ir_closure){translate([0,-closure,0])ir_front_raw();}
module ir_anchor_blank(){union(){
 ir_box(-32,32,-48,-42,-156,-128);
 for(x=[-ir_key_x,ir_key_x])ir_box(x-ir_key_w/2,x+ir_key_w/2,
  -48-ir_key_depth,-47.8,ir_key_z-ir_key_h/2,ir_key_z+ir_key_h/2);
}}
module ir_anchor_cuts(){
 for(x=[-ir_key_x,ir_key_x])ir_ycyl(x,ir_key_z,-60,30,2.9);
 // Replacement SINGLE-LAYER textile paths; old slots now carry the keys.
 for(x=[-20.5,20.5])ir_box(x-1.5,x+1.5,-49,-41,-153,-131);
}
module ir_rear(){difference(){union(){
 ir_collar_rear();ir_anchor_blank();
 // Move braces outboard of the REAL M2.5 nuts and wrench approach.
 // Their X23..31 roots also leave the X19..22 strap slots open.
 for(x=[-27,27])hull(){
  ir_box(x-4,x+4,-31,-23,-121,-105);
  ir_box(x-4,x+4,-48,-42,-150,-134);
 }
}ir_anchor_cuts();}}
module ir_backplate(){difference(){
 ir_box(-14,14,-57,-54,-156,-128);
 for(x=[-ir_key_x,ir_key_x])ir_ycyl(x,ir_key_z,-58,5,2.9);
}}
module ir_printed(closure=ir_closure){ir_rear();ir_front(closure);ir_backplate();}
module ir_washer(x,z,y,od,id,t){difference(){ir_ycyl(x,z,y,t,od);ir_ycyl(x,z,y-ir_eps,t+2*ir_eps,id);}}
module ir_nut(x,z,y,af,h,d){difference(){ir_yhex(x,z,y,h,af);ir_ycyl(x,z,y-ir_eps,h+2*ir_eps,d);}}
module ir_m4_nuts(){for(x=[-ir_ear_x,ir_ear_x])ir_nut(x,ir_z,-11.6,7,3.2,4);}
module ir_clamp_hardware(closure=ir_closure){
 ir_m4_nuts();
 for(x=[-ir_ear_x,ir_ear_x]){
  ir_ycyl(x,ir_z,12.8-closure-30,30,4);
  difference(){ir_ycyl(x,ir_z,12.8-closure,4,7);ir_yhex(x,ir_z,14.8-closure,2.1,3);}
  ir_washer(x,ir_z,12-closure,12,4.3,.8);
 }
}
// M2.5 hardware envelope requirements; commercial SKU not yet frozen.
module ir_anchor_hardware(){for(x=[-ir_key_x,ir_key_x]){
 ir_ycyl(x,ir_key_z,-57.5,20,2.5);
 difference(){ir_ycyl(x,ir_key_z,-60.5,3,5);ir_yhex(x,ir_key_z,-60.6,1.6,2);}
 ir_washer(x,ir_key_z,-57.5,6,2.7,.5);
 ir_washer(x,ir_key_z,-42,6,2.7,.5);
 ir_nut(x,ir_key_z,-41.5,5,2,2.5);
}}
module ir_hardware(closure=ir_closure){ir_clamp_hardware(closure);ir_anchor_hardware();}

// Nominal display envelopes only; neither is a validated material/component.
module ir_hose_reference(){ir_ring(hose_od,hose_id,-166,-98);}
module ir_pad_reference(front=false,closure=ir_closure){translate([0,front?-closure:0,0])intersection(){ir_ring(ir_id,ir_id-2*ir_pad_t);ir_half(front);}}
