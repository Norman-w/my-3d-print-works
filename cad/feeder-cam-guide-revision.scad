// Independent right-master X guide candidate. Units mm; X1C/.4/PETG.
// Reuses the existing carrier Y gibs, cam carriage and seam-body candidates.
// Not adopted into the root assembly; no physical/tolerance release implied.
revision_library_mode=true;
include <feeder-guide-revision.scad>
use <feeder-seam-candidate.scad>

cg_part="assembly"; // assembly,section,right_support,gib,cover,probe,dimensions
cg_t=.5;
cg_setting=.9; // advance [0,1]; parallel display, NOT measured printing error
cg_probe="motion";
cg_remove=0;
cg_fault_x=0;
cg_gib_dz=0; // rigid axial float; ear pocket bounds it to +/- .2 nominally
cg_witness_matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
cg_show_body=true;
cg_show_hardware=true;
cg_eps=.02;

// ONE X master on the right. The left guide's original .2 side gaps remain.
cg_datum_x=support_rail_x0;
cg_datum_embed=.8;
cg_contact_y0=21;
cg_contact_y1=support_rail_y1;
cg_contact_z=[[support_guide_z0,support_cap_screw_z[0]-3.1],
              [support_cap_screw_z[1]+3.1,support_guide_z1]];
cg_travel=1;
cg_front_retracted=support_rail_x1+cg_travel;
cg_tooth_length=9.4;
cg_spine_thickness=3;
cg_pocket_gap=.2;
cg_end_recess=.4; // both moving ends stay behind FIXED guide stop planes
cg_jack_y=(cg_contact_y0+cg_contact_y1)/2;
cg_jack_z=[for(b=cg_contact_z)(b[0]+b[1])/2];
cg_case_x0=support_guide_x1-1;
cg_case_face_x=75;
cg_case_y0=10.5;
cg_case_y1=28;
cg_case_z0=support_guide_z0-4;
cg_case_z1=support_guide_z1+4;
cg_cover_thickness=5.5;
cg_cover_outer_x=cg_case_face_x+cg_cover_thickness;
cg_mount_y=15;
cg_mount_z=[-24,-6];
cg_mount_nut_x=68;
cg_ear_z0=-18;
cg_ear_z1=-12;
cg_ear_y0=cg_contact_y1;
cg_ear_y1=cg_contact_y1+2;
cg_ear_x_length=1;
cg_jack_length=16;
cg_mount_length=16;
cg_mount_tip_clearance=1.5;
cg_bolt_d=3;
cg_bolt_hole=fastener_d;
cg_head_d=5.5;
cg_head_h=3;
cg_washer_d=7;
cg_washer_h=.5;
cg_nut_af=5.5;
cg_nut_h=2.4;

function cg_front(s)=cg_front_retracted-s;
function cg_spine(s)=cg_front(s)+cg_tooth_length;
function cg_back(s)=cg_spine(s)+cg_spine_thickness;
function cg_gap(s)=cg_front(s)-support_rail_x1;
function cg_jack_head_x(s)=cg_back(s)+cg_jack_length;
assert(cg_setting>=0&&cg_setting<=cg_travel);
assert(cg_end_recess>cg_pocket_gap,"End recess must exceed ear axial float");
assert(cg_contact_y0-cg_pocket_gap>18+nut_depth,
    "Keep the original guide-cap nut entry corridor completely open");
assert(cg_spine(cg_travel)-cg_pocket_gap>support_guide_x1,
    "The long gib spine must stay outside the original fixed wall");
assert(cg_case_z1<cam_rail_z1-cam_bridge_width,
    "New top must clear the unshifted trigger cross member");
assert(cg_mount_nut_x>support_guide_x1,
    "New nut feed slots must not cut original cap nut channels");

module cg_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module cg_x_hole(x,y,z,length,d){support_x_hole(y,z,x,length,d);}
module cg_x_hex(x,y,z,length,af){
    translate([x,y,z])rotate([0,90,0])rotate([0,0,30])
        cylinder(h=length,d=af/cos(30),$fn=6);
}
module cg_nut(x,y,z){difference(){
    cg_x_hex(x,y,z,cg_nut_h,cg_nut_af);
    cg_x_hole(x-cg_eps,y,z,cg_nut_h+2*cg_eps,3.2);
}}
module cg_washer(x,y,z){difference(){
    cg_x_hole(x,y,z,cg_washer_h,cg_washer_d);
    cg_x_hole(x-cg_eps,y,z,cg_washer_h+2*cg_eps,3.2);
}}

// The datum is integral, with .8 mm overlap into the OLD inner wall.
// Its long exposed face can be dressed with the +Y cap removed. Dressing
// changes the datum: measure/re-enter that offset; never call it self-centering.
module cg_datum(){
    cg_box(cg_datum_x-support_axial_clearance-cg_datum_embed,cg_datum_x,
        cg_contact_y0,cg_contact_y1,support_guide_z0,support_guide_z1);
}
module cg_case_blank(){
    cg_box(cg_case_x0,cg_case_face_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
}
module cg_case_cuts(){
    // Do not merge the original +Y removable cap into the fixed support.
    cg_box(cg_case_x0-cg_eps,support_guide_x1+cg_eps,
        support_guide_y_split-cg_eps,cg_case_y1+cg_eps,
        support_guide_z0-cg_eps,support_guide_z1+cg_eps);
    // Only two windows pass through the original outboard wall.
    for(b=cg_contact_z)
        cg_box(support_rail_x1-cg_pocket_gap,cg_case_face_x+cg_eps,
            cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
            b[0]-cg_pocket_gap,b[1]+cg_pocket_gap);
    // Continuous spine is wholly outside the original wall.
    cg_box(cg_spine(cg_travel)-cg_pocket_gap,cg_case_face_x+cg_eps,
        cg_contact_y0-cg_pocket_gap,cg_contact_y1+cg_pocket_gap,
        support_guide_z0-cg_pocket_gap,support_guide_z1+cg_pocket_gap);
    // Ear pocket: its inner X wall is the positive advance stop.
    cg_box(cg_spine(cg_travel),cg_case_face_x+cg_eps,
        cg_ear_y0-cg_pocket_gap,cg_ear_y1+cg_pocket_gap,
        cg_ear_z0-cg_pocket_gap,cg_ear_z1+cg_pocket_gap);
    for(z=cg_mount_z){
        cg_x_hole(cg_cover_outer_x+.5-cg_mount_length-cg_mount_tip_clearance,cg_mount_y,z,
            cg_mount_length+cg_mount_tip_clearance+cg_eps,cg_bolt_hole);
        // Nut loads against the +X pocket floor; feed from +Y BEFORE gib.
        cg_x_hex(cg_mount_nut_x,cg_mount_y,z,nut_depth,nut_af);
        cg_box(cg_mount_nut_x,cg_mount_nut_x+nut_depth,
            cg_mount_y,cg_case_y1+cg_eps,z-nut_af/2,z+nut_af/2);
    }
}
module cg_right_support(){difference(){
    union(){revision_side_support_local();cg_datum();cg_case_blank();}
    cg_case_cuts();
}}

module cg_gib(s=cg_setting,dz=cg_gib_dz,recess=cg_end_recess){translate([0,0,dz])union(){
    cg_box(cg_spine(s),cg_back(s),cg_contact_y0,cg_contact_y1,
        support_guide_z0+recess,support_guide_z1-recess);
    for(b=cg_contact_z)
        cg_box(cg_front(s),cg_spine(s)+cg_eps,cg_contact_y0,cg_contact_y1,
            max(b[0],support_guide_z0+recess),min(b[1],support_guide_z1-recess));
    cg_box(cg_spine(s),cg_spine(s)+cg_ear_x_length,
        cg_ear_y0-cg_eps,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}}
module cg_cover(){difference(){union(){
    cg_box(cg_case_face_x,cg_cover_outer_x,cg_case_y0,cg_case_y1,
        cg_case_z0,cg_case_z1);
    // Back stop leaves with the cover, so the gib can be pulled out +X.
    cg_box(cg_spine(0)+cg_ear_x_length,cg_case_face_x+cg_eps,
        cg_ear_y0,cg_ear_y1,cg_ear_z0,cg_ear_z1);
}
    for(z=cg_mount_z)cg_x_hole(cg_case_face_x-cg_eps,cg_mount_y,z,
        cg_cover_thickness+2*cg_eps,cg_bolt_hole);
    for(z=cg_jack_z){
        cg_x_hole(cg_case_face_x-cg_eps,cg_jack_y,z,
            cg_cover_thickness+2*cg_eps,cg_bolt_hole);
        // Insert nuts from the loose cover's -X face; 2.9 mm bearing web.
        cg_x_hex(cg_case_face_x-cg_eps,cg_jack_y,z,nut_depth+cg_eps,nut_af);
    }
}}
module cg_new_hardware(s=cg_setting,skip_z=undef){
    for(z=cg_mount_z)if(is_undef(skip_z)||z!=skip_z){
        under=cg_cover_outer_x+cg_washer_h;
        cg_x_hole(under-cg_mount_length,cg_mount_y,z,cg_mount_length,cg_bolt_d);
        cg_x_hole(under,cg_mount_y,z,cg_head_h,cg_head_d);
        cg_washer(cg_cover_outer_x,cg_mount_y,z);
        cg_nut(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y,z);
    }
    for(z=cg_jack_z)if(is_undef(skip_z)||z!=skip_z){
        cg_x_hole(cg_back(s),cg_jack_y,z,cg_jack_length,cg_bolt_d);
        cg_x_hole(cg_jack_head_x(s),cg_jack_y,z,cg_head_h,cg_head_d);
        cg_nut(cg_case_face_x+nut_depth-cg_nut_h,cg_jack_y,z);
        cg_washer(cg_cover_outer_x,cg_jack_y,z);
        cg_nut(cg_cover_outer_x+cg_washer_h,cg_jack_y,z);
    }
}
module cg_fixed(include_new_cover=true,include_y_caps=true){
    cg_right_support();
    mirror([1,0,0])revision_side_support_local();
    if(include_y_caps)for(side=[-1,1])scale([side,1,1])feeder_guide_cap_local();
    for(side=[-1,1],g=[0,-gate_spacing])
        scale([side,1,1])translate([0,0,g])revision_keeper_local();
    feeder_spring_fixed_interface();
    if(include_new_cover)cg_cover();
}
module cg_body(){seam_candidate_half(false);seam_candidate_half(true);seam_pins();}
module cg_old_hardware(include_caps=true){
    if(include_caps)feeder_cap_hardware();
    feeder_mount_hardware();
    for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g,.9);
}
module cg_moving(t=cg_t){feeder_carriage(t);revision_followers(t);}
module cg_station_tools(z,s=cg_setting,jack=true){
    if(!jack)cg_x_hole(cg_cover_outer_x+.5+cg_head_h,cg_mount_y,z,40,4);
    else{
        cg_x_hole(cg_jack_head_x(s)+cg_head_h,cg_jack_y,z,40,4);
        // 5.5 open wrench outer envelope, with handle directed +Y.
        cg_x_hole(cg_cover_outer_x+.5,cg_jack_y,z,2.8,9);
        cg_box(cg_cover_outer_x+.5,cg_cover_outer_x+3.3,
            cg_jack_y,cg_jack_y+35,z-3,z+3);
    }
}
module cg_tools(s=cg_setting){
    for(z=cg_mount_z)cg_station_tools(z,s,false);
    for(z=cg_jack_z)cg_station_tools(z,s,true);
}
// Exact swept primitives of the unmodified RIGHT rail + its endpoint stops.
// These are the only moving members able to touch the new bearing faces.
module cg_rail_sweep(dx=0){translate([dx,0,0]){
    cg_box(support_rail_x0,support_rail_x1,support_rail_y0,support_rail_y1,
        cam_rail_z0,cam_rail_z1+cam_stroke);
    for(z=[support_guide_z0-cam_stroke-support_stop_thickness,support_guide_z1])
        cg_box(support_stop_x0,support_stop_x1,support_stop_y0,support_stop_y1,
            z,z+support_stop_thickness+cam_stroke);
}}
module cg_new_contact_solids(s=cg_setting){cg_datum();cg_gib(s);}
module cg_new_only_fixed(){difference(){cg_right_support();revision_side_support_local();}cg_cover();}

module cg_probe_geometry(){
    if(cg_probe=="motion")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_old_hardware();cg_new_hardware();}
        cg_moving();}
    else if(cg_probe=="cam_followers")intersection(){feeder_carriage(cg_t);revision_followers(cg_t);}
    else if(cg_probe=="hardware")intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_new_hardware();}
    else if(cg_probe=="old_hardware")intersection(){
        cg_new_only_fixed();cg_old_hardware();}
    else if(cg_probe=="tools")union(){intersection(){
        union(){cg_fixed();cg_gib();revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        cg_tools();}
        for(z=cg_mount_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=false);}
        for(z=cg_jack_z)intersection(){cg_new_hardware(skip_z=z);cg_station_tools(z,jack=true);}
    }
    else if(cg_probe=="old_tools")intersection(){cg_new_only_fixed();union(){revision_tools();feeder_follower_tools(cg_t);}}
    else if(cg_probe=="gib_fit")intersection(){cg_fixed();cg_gib();}
    else if(cg_probe=="legacy_gib_endpoint")intersection(){
        cg_gib(dz=cg_gib_dz,recess=0);feeder_carriage(cg_t);}
    else if(cg_probe=="fixed_stop_bearing")intersection(){
        // Exact rectangular subset of the FIXED datum's stop-bearing face.
        // 0.01 mm inside the plane makes area measurable as volume/.01.
        cg_datum();
        z=(cg_t==0?support_guide_z1-.01:support_guide_z0);
        cg_box(support_stop_x0+cg_fault_x,support_stop_x1+cg_fault_x,
            support_stop_y0,support_stop_y1,z,z+.01);}
    else if(cg_probe=="sweep")intersection(){cg_new_contact_solids();cg_rail_sweep(cg_fault_x);}
    else if(cg_probe=="old_witness")intersection(){
        cg_new_contact_solids();multmatrix(cg_witness_matrix)feeder_carriage(cg_t);}
    else if(cg_probe=="gib_remove")intersection(){
        union(){cg_fixed(false);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_gib(0);}
    else if(cg_probe=="cover_remove")intersection(){
        union(){cg_fixed(false);cg_gib(0);revision_gibs();cg_body();cg_moving();cg_old_hardware();}
        translate([cg_remove,0,0])cg_cover();}
    else if(cg_probe=="lift_frame")intersection(){
        union(){cg_fixed(true,false);cg_gib(0);revision_gibs();cg_body();
            for(side=[-1,1],rear=[false,true])cam_finger(side,rear,cg_t);}
        feeder_carriage(cg_t,cg_remove);}
    else if(cg_probe=="mount_nut_insert")intersection(){
        cg_right_support();
        for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="jack_nut_insert")intersection(){
        cg_cover();
        for(z=cg_jack_z)hull()for(dx=[0,-10])
            cg_x_hex(cg_case_face_x+nut_depth-cg_nut_h+dx,cg_jack_y,z,cg_nut_h,cg_nut_af);}
    else if(cg_probe=="old_nut_insert")intersection(){
        cg_right_support();
        for(z=support_cap_screw_z)hull()for(from=[support_nut_entry_z-4,z])
            support_y_hex(support_cap_screw_x,from,18.1,2.4,5.5);}
    else if(cg_probe=="advance_stop")intersection(){cg_fixed();cg_gib(cg_travel+.1);}
    else if(cg_probe=="retract_stop")intersection(){cg_fixed();cg_gib(-.1);}
    else if(cg_probe=="datum_embed")intersection(){cg_datum();revision_side_support_local();}
    else if(cg_probe=="case_embed")intersection(){
        difference(){cg_case_blank();cg_case_cuts();}revision_side_support_local();}
    else if(cg_probe=="bad_nut_sequence")intersection(){
        cg_gib();for(z=cg_mount_z)hull()for(dy=[0,25])
            cg_x_hex(cg_mount_nut_x+nut_depth-cg_nut_h,cg_mount_y+dy,z,cg_nut_h,cg_nut_af);}
    else assert(false,"Unknown cg_probe");
}
module cg_display(section=false){
    if(cg_show_body)color([.6,.68,.75]){
        if(section)seam_candidate_half(false);else cg_body();
    }
    color([.70,.72,.76])cg_fixed();
    color([.95,.63,.12]){cg_gib();revision_gibs();}
    color([.12,.43,.78])feeder_carriage(cg_t);
    color([.15,.65,.39])revision_followers(cg_t);
    if(cg_show_hardware)color([.28,.29,.31]){cg_old_hardware();cg_new_hardware();}
}
module cg_working_section(){
    // Local horizontal XY section through the upper bearing and jack axis.
    // Color outside each boolean preserves the mechanical interfaces in F6.
    module clip(){intersection(){children();
        cg_box(48,94,16,31,cg_jack_z[1]-.65,cg_jack_z[1]+.65);}}
    color([.70,.72,.76])clip()cg_fixed();
    color([.95,.63,.12])clip()cg_gib();
    color([.12,.43,.78])clip()feeder_carriage(cg_t);
    if(cg_show_hardware)color([.28,.29,.31])clip()cg_new_hardware();
}
module cg_dimensions(){echo("CG_DIMENSIONS",[
    ["datum_x",cg_datum_x],["rail_x0",support_rail_x0],["rail_x1",support_rail_x1],
    ["old_half_gap",support_axial_clearance],["contact_y",[cg_contact_y0,cg_contact_y1]],
    ["contact_z",cg_contact_z],["front_x",cg_front(cg_setting)],["setting",cg_setting],
    ["travel",cg_travel],["parallel_x_interval",[0,cg_gap(cg_setting)]],
    ["gib_end_recess",cg_end_recess],["gib_axial_float_limit",cg_pocket_gap],
    ["worst_axial_end_clearance",cg_end_recess-cg_pocket_gap],
    ["active_contact_z",[for(b=cg_contact_z)
        [max(b[0],support_guide_z0+cg_end_recess),min(b[1],support_guide_z1-cg_end_recess)]]],
    ["known_gib_limit_planes",[[0,cg_spine(cg_travel)],
        [2,cg_ear_z0-cg_pocket_gap],[2,cg_ear_z1+cg_pocket_gap],
        [2,cg_contact_z[0][1]+cg_pocket_gap],[2,cg_contact_z[1][0]-cg_pocket_gap]]],
    ["stroke",cam_stroke],["spine_front_min",cg_spine(cg_travel)],
    ["datum_overlap",cg_datum_embed],["nut_channel_y_max",18+nut_depth],
    ["new_pocket_y_min",cg_contact_y0-cg_pocket_gap],
    ["jack_z",cg_jack_z],["jack_y",cg_jack_y],["mount_z",cg_mount_z],
    ["nut_bearing_web",cg_cover_thickness-nut_depth],
    ["mount_tip_clearance",cg_mount_tip_clearance],
    ["max_new_hardware_x",cg_jack_head_x(0)+cg_head_h],
    ["guide_z",[support_guide_z0,support_guide_z1]]]);}

if(is_undef(cg_library_mode)||!cg_library_mode){
    if(cg_part=="assembly")cg_display();
    else if(cg_part=="section")cg_working_section();
    else if(cg_part=="right_support")cg_right_support();
    else if(cg_part=="gib")cg_gib(0);
    else if(cg_part=="cover")cg_cover();
    else if(cg_part=="probe")cg_probe_geometry();
    else if(cg_part=="dimensions")cg_dimensions();
    else assert(false,"Unknown cg_part");
}
