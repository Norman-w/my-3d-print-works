// Independent load harness. Nominal packaging only; not a load certification.
// +Z feed; root seam stays X=0. No new cut enters the ID64 air chamber.
cg_library_mode=true;
include <feeder-cam-guide-revision.scad>
use <feeder-seam-candidate.scad>

sh_part="assembly";
sh_probe="fixed";
sh_t=0;
sh_remove=0;
sh_fault=0;
sh_eps=.02;
sh_bolt_x=[-16,16];
sh_bolt_z=[-60,3];
sh_ear_face_y=-48;
sh_beam_back_y=-54;
sh_nut_y=-39;
sh_nut_t=3.4;
sh_grip_x=76;
sh_grip_y=-52;
sh_grip_r=11;
sh_grip_z0=-60;
sh_grip_z1=10;
sh_finger_d=16;
sh_strap_z=-142;

module sh_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module sh_y_cyl(x,z,y0,h,d,fn=64){translate([x,y0,z])rotate([-90,0,0])cylinder(h=h,d=d,$fn=fn);}
module sh_y_hex(x,z,y0,h,af){translate([x,y0,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}

// Parent integration: union additions AFTER seam_candidate_half, then cuts.
// Both modules are half-local and never depend on the assembly selector.
module sh_host_additions(positive=true){
    x=positive?16:-16;
    difference(){
        union()for(z=sh_bolt_z)
            sh_box(x-6,x+6,sh_ear_face_y,-26,z-6,z+6);
        translate([0,0,guide_start_z-1])cylinder(h=guide_length+2,d=body_id+.4,$fn=72);
    }
}
module sh_host_cuts(positive=true){
    x=positive?16:-16;
    for(z=sh_bolt_z){
        sh_y_cyl(x,z,-55,22,4.5);
        sh_y_hex(x,z,sh_nut_y,sh_nut_t,7.3);
        // Captive nut enters radially OUTWARD in X before beam installation.
        sh_box(positive?x:x-10,positive?x+10:x,
            sh_nut_y,sh_nut_y+sh_nut_t,z-4.25,z+4.25);
    }
}
module sh_host_half(positive=true){difference(){
    union(){seam_candidate_half(positive);sh_host_additions(positive);}
    sh_host_cuts(positive);
}}
module sh_ears(){for(p=[false,true])difference(){sh_host_additions(p);sh_host_cuts(p);}}
module sh_host(){sh_host_half(false);sh_host_half(true);}

module sh_beam_blank(sweep=0){
    union(){
        sh_box(-24,24,sh_beam_back_y-sweep,sh_ear_face_y,-68,28);
        // Hose strain relief: a channel section reaches FREE hose before spigot.
        sh_box(-18,18,-54-sweep,-48,-156,-66);
        for(s=[-1,1])sh_box(s==1?15:-18,s==1?18:-15,-62-sweep,-48,-156,-66);
        // Lower arm crosses below all carrier-adjuster tool corridors.
        sh_box(22,78,-58-sweep,-48,-66,-54);
        // Upper arm passes above X51 adjuster, then descends below finger path.
        hull(){sh_box(20,49,-58-sweep,-46,18,26);sh_box(48,53,-58-sweep,-46,18,26);}
        hull(){sh_box(48,53,-58-sweep,-46,18,26);sh_box(72,80,-58-sweep,-46,0,8);}
        // Fixed rounded rectangular grip: 22 diameter, 70 axial extent.
        hull()for(dy=[0,-sweep])translate([sh_grip_x,sh_grip_y+dy,sh_grip_z0])
            cylinder(h=sh_grip_z1-sh_grip_z0,r=sh_grip_r,$fn=72);
    }
}
module sh_beam(sweep=0){difference(){
    sh_beam_blank(sweep);
    for(x=sh_bolt_x,z=sh_bolt_z)sh_y_cyl(x,z,-56-sweep,10+sweep,4.5);
    // Two 3 x 22 slots accept a nominal 20 x 1.5 textile strap, not a rigid clamp.
    for(x=[-10.5,10.5])sh_box(x-1.5,x+1.5,-65-sweep,-45,sh_strap_z-11,sh_strap_z+11);
}}
module sh_bolts(){for(x=sh_bolt_x,z=sh_bolt_z){
    sh_y_cyl(x,z,-54.8,20,4);
    sh_y_cyl(x,z,-58.8,4,7);
    difference(){sh_y_cyl(x,z,-54.8,.8,9);sh_y_cyl(x,z,-54.9,1,4.3);}
}}
module sh_nuts(){for(x=sh_bolt_x,z=sh_bolt_z)difference(){
    sh_y_hex(x,z,sh_nut_y,3.2,7);
    sh_y_cyl(x,z,sh_nut_y-.1,3.4,3.4);
}}
module sh_tools(){for(x=sh_bolt_x,z=sh_bolt_z)sh_y_cyl(x,z,-105,46.2,5);}
module sh_nut_sweep(){for(x=sh_bolt_x,z=sh_bolt_z)hull(){
    sh_y_hex(x,z,sh_nut_y,3.2,7);
    sh_y_hex(x+(x>0?18:-18),z,sh_nut_y,3.2,7);
}}
module sh_finger_sweep(){hull()for(t=[0,1])
    sh_y_cyl(support_trigger_x,support_trigger_z+t*cam_stroke,-85,91,sh_finger_d);
}
module sh_frame_sweep(){hull()for(t=[0,1])feeder_carriage(t);}
module sh_original_fixed(){cg_fixed();cg_gib();revision_gibs();cg_old_hardware();cg_new_hardware();}
module sh_added(){sh_ears();sh_beam();sh_bolts();sh_nuts();}
module sh_existing_tools(){
    revision_tools();cg_tools();
    for(t=[0,.5,1])feeder_follower_tools(t);
    for(y=[-40,40],z=[-72,-46,-10,16])
        translate([-45,y,z])rotate([0,90,0])cylinder(h=90,d=5,$fn=32);
}
module sh_body_bore(){translate([0,0,guide_start_z])cylinder(h=guide_length,d=body_id,$fn=72);}
module sh_probe_geometry(){
    if(sh_probe=="fixed")intersection(){sh_added();sh_original_fixed();}
    else if(sh_probe=="motion")intersection(){sh_added();union(){feeder_carriage(sh_t);revision_followers(sh_t);}}
    else if(sh_probe=="frame_sweep")intersection(){sh_added();sh_frame_sweep();}
    else if(sh_probe=="finger")intersection(){sh_added();sh_finger_sweep();}
    else if(sh_probe=="old_tools")intersection(){sh_added();sh_existing_tools();}
    else if(sh_probe=="new_tools")intersection(){union(){sh_host();sh_beam();sh_original_fixed();}sh_tools();}
    else if(sh_probe=="hardware")intersection(){union(){sh_host();sh_beam();}union(){sh_bolts();sh_nuts();}}
    else if(sh_probe=="nuts_insert")intersection(){sh_host();sh_nut_sweep();}
    else if(sh_probe=="keeper_remove")intersection(){sh_added();
        for(side=[-1,1],g=[0,-gate_spacing])hull()for(dy=[0,-50])
            scale([side,1,1])translate([0,dy,g])revision_keeper_local();}
    else if(sh_probe=="keeper_remove_beam_off")intersection(){sh_ears();
        for(side=[-1,1],g=[0,-gate_spacing])hull()for(dy=[0,-50])
            scale([side,1,1])translate([0,dy,g])revision_keeper_local();}
    else if(sh_probe=="carrier_gib_remove")intersection(){sh_added();
        for(side=[-1,1],g=[0,-gate_spacing])hull()for(dy=[0,-50])
            scale([side,1,1])translate([0,dy,g])revision_gib_local(0);}
    else if(sh_probe=="frame_lift")intersection(){sh_added();
        hull()for(dy=[0,50])feeder_carriage(0,dy);}
    else if(sh_probe=="finger_remove")intersection(){sh_added();
        for(side=[-1,1],rear=[false,true])hull()for(dx=[0,35])
            translate([side*dx,0,0])cam_finger(side,rear,1);}
    else if(sh_probe=="cam_cover_remove")intersection(){sh_added();
        hull()for(dx=[0,40])translate([dx,0,0])cg_cover();}
    else if(sh_probe=="cam_gib_remove")intersection(){sh_added();
        hull()for(dx=[0,40])translate([dx,0,0])cg_gib(0);}
    else if(sh_probe=="beam_remove")intersection(){union(){sh_host();sh_original_fixed();}sh_beam(40);}
    else if(sh_probe=="bore")intersection(){sh_added();sh_body_bore();}
    else if(sh_probe=="root")intersection(){sh_ears();union(){seam_candidate_half(false);seam_candidate_half(true);}}
    else if(sh_probe=="mount_contact")intersection(){sh_host();sh_beam();}
    else if(sh_probe=="bolt_control")intersection(){sh_host();translate([1,0,0])sh_bolts();}
    else if(sh_probe=="finger_control")intersection(){translate([0,0,10])sh_beam();sh_finger_sweep();}
    else if(sh_probe=="body_remove")intersection(){sh_beam();translate([sh_remove,0,0])sh_host_half(true);}
    else assert(false,"Unknown harness probe");
}
module sh_assembly(exploded=false){
    color([.63,.72,.8,.7])sh_host();
    color([.13,.38,.55])translate([0,exploded?-32:0,0])sh_beam();
    color([.75,.75,.75]){sh_bolts();sh_nuts();}
    color([.7,.7,.7,.65])sh_original_fixed();
    color([.93,.57,.12]){feeder_carriage(sh_t);revision_followers(sh_t);}
    if(sh_part=="finger_view")color([.95,.32,.32,.3])sh_finger_sweep();
}

if(is_undef(sh_library_mode)||!sh_library_mode){
    if(sh_part=="assembly"||sh_part=="finger_view")sh_assembly();
    else if(sh_part=="exploded")sh_assembly(true);
    else if(sh_part=="positive_half")sh_host_half(true);
    else if(sh_part=="negative_half")sh_host_half(false);
    else if(sh_part=="beam")sh_beam();
    else if(sh_part=="probe")sh_probe_geometry();
    else assert(false,"Unknown harness part");
}
