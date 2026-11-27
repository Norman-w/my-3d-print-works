// Independent public-cam Y guide. mm; X1C/.4/PETG. Not yet in final assembly.
// Replaces two old guide caps; adds two gibs and .2mm fixed lower datums.
// No seals or physical fit/strength certification are implied.
cg_library_mode=true;
include <feeder-cam-guide-revision.scad>
use <feeder-return-spring.scad>

yg_part="cap";
yg_probe="motion";
yg_t=.5;
yg_side=1;
yg_face=24.1; // displayed .1 Y gap, not measured; real adjustment 23.8..25
yg_gib_dx=0;
yg_gib_dz=0;
yg_rail_dx=0;
yg_rail_dy=0;
yg_remove=0;
yg_eps=.02;
yg_cap_top=35.5;
yg_lock_top=39; // raised local bosses clear the adjacent mount screw heads
yg_work_min=23.8;
yg_work_max=25;
yg_hard_min=23.7;
yg_hard_max=25.2;
yg_datum_y=support_rail_y0;
yg_datum_x=[53.5,58.5];
yg_bands=[[-33.5,-27.5],[-2.5,3.5]];
yg_gib_x=[53.5,58.5];
yg_tooth_x=[54.2,57.8]; // stays inside the original channel at X float +/- .2
yg_gib_z=[yg_bands[0][0],yg_bands[1][1]];
yg_spine_front=1;
yg_spine_back=3;
yg_ear_x=[58.3,60.5];
yg_ear_z=[-18,-12];
yg_ear_bottom=support_guide_y_split-yg_hard_min; // .5: fixed host is advance stop
yg_ear_top=yg_spine_back; // common flat printing back; front advance stop unchanged
yg_pocket_clear=.2;
yg_jack_x=55.5;
yg_jack_z=[for(b=yg_bands)(b[0]+b[1])/2];
yg_nut_top=31.1;
yg_nut_y=yg_nut_top-2.4; // loaded +Y face seats against pocket roof
yg_mount_length=20;
yg_jack_length=16;
yg_nut_h=2.4;
yg_washer_h=.5;
yg_head_h=3;
yg_head_d=5.5;
yg_tool_d=4;

assert(yg_datum_y==20&&support_rail_y1==24);
assert(yg_hard_min<yg_work_min&&yg_work_min<24&&24<yg_work_max&&yg_work_max<yg_hard_max);
assert(yg_jack_x-yg_gib_x[0]>=2&&yg_gib_x[1]-yg_jack_x>=2);
assert(yg_gib_z[0]-yg_pocket_clear>support_guide_z0);
assert(yg_gib_z[1]+yg_pocket_clear<support_guide_z1);
assert(yg_cap_top+.5-yg_mount_length>=16);
assert(yg_work_max+yg_spine_back+.3<=yg_nut_y);
assert(yg_work_min+yg_spine_back+yg_jack_length>yg_lock_top+.5+yg_nut_h);

module yg_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module yg_at(side=yg_side){scale([side,1,1])children();}
module yg_ycyl(x,z,y,h,d){support_y_hole(x,z,y,h,d);}
module yg_nut(x,z,y){difference(){support_y_hex(x,z,y,yg_nut_h,5.5);
    yg_ycyl(x,z,y-yg_eps,yg_nut_h+2*yg_eps,3.2);}}
module yg_washer(x,z,y){difference(){yg_ycyl(x,z,y,.5,7);
    yg_ycyl(x,z,y-yg_eps,.5+2*yg_eps,3.2);}}

// The .8 overlap is inside the original continuous guide floor. Two real
// bearing bands, not a detached .2mm shim. End stop planes Z=-35,+5 untouched.
module yg_lower_datum_local(){for(b=yg_bands)
    yg_box(yg_datum_x[0],yg_datum_x[1],yg_datum_y-1,yg_datum_y,b[0],b[1]);}
module yg_right_support(){union(){cg_right_support();yg_lower_datum_local();}}
module yg_left_support(){union(){rs_left_support();yg_at(-1)yg_lower_datum_local();}}

module yg_cap_local(sweep=0){difference(){union(){
    for(z=yg_jack_z)yg_ycyl(yg_jack_x,z,yg_cap_top-.2,yg_lock_top-yg_cap_top+.2+sweep,8);
    yg_box(support_guide_x0,support_guide_x1,support_guide_y_split,yg_cap_top+sweep,
        support_guide_z0,support_guide_z1);}
    // Drop the gib through -Y while the cap is off. The HOST closes the
    // opening in service; the loose cap alone does not permanently retain it.
    yg_box(yg_gib_x[0]-yg_pocket_clear,yg_gib_x[1]+yg_pocket_clear,
        support_guide_y_split-yg_eps,yg_hard_max+yg_spine_back,
        yg_gib_z[0]-yg_pocket_clear,yg_gib_z[1]+yg_pocket_clear);
    yg_box(yg_ear_x[0]-yg_pocket_clear,yg_ear_x[1]+yg_pocket_clear,
        support_guide_y_split-yg_eps,yg_hard_max+yg_ear_top,
        yg_ear_z[0]-yg_pocket_clear,yg_ear_z[1]+yg_pocket_clear);
    for(z=support_cap_screw_z)
        yg_ycyl(support_cap_screw_x,z,support_guide_y_split-yg_eps,
            yg_cap_top+sweep-support_guide_y_split+2*yg_eps,fastener_d);
    for(z=yg_jack_z){
        yg_ycyl(yg_jack_x,z,yg_hard_max+yg_spine_back-yg_eps,
            yg_lock_top+sweep-(yg_hard_max+yg_spine_back)+2*yg_eps,fastener_d);
        // Nut enters the loose cap from -Y BEFORE the gib. A full 4.4 mm
        // roof above Y31.1 carries the jack reaction into the bolted cap.
        support_y_hex(yg_jack_x,z,support_guide_y_split-yg_eps,
            yg_nut_top-support_guide_y_split+yg_eps,nut_af);
    }
}}
module yg_gib_local(face=yg_face,dx=yg_gib_dx,dz=yg_gib_dz,travel=0){translate([dx,0,dz])union(){
    yg_box(yg_gib_x[0],yg_gib_x[1],face+yg_spine_front,face+yg_spine_back+travel,
        yg_gib_z[0],yg_gib_z[1]);
    for(b=yg_bands)yg_box(yg_tooth_x[0],yg_tooth_x[1],face,face+yg_spine_front+.2+travel,b[0],b[1]);
    yg_box(yg_ear_x[0],yg_ear_x[1],face+yg_ear_bottom,face+yg_ear_top+travel,
        yg_ear_z[0],yg_ear_z[1]);
}}
module yg_station_hardware_local(z,jack=true,face=yg_face){
    if(!jack){
        under=yg_cap_top+.5;
        yg_ycyl(support_cap_screw_x,z,under-yg_mount_length,yg_mount_length,3);
        yg_ycyl(support_cap_screw_x,z,under,yg_head_h,yg_head_d);
        yg_washer(support_cap_screw_x,z,yg_cap_top);
        yg_nut(support_cap_screw_x,z,18.1);
    }else{
        tip=face+yg_spine_back;
        yg_ycyl(yg_jack_x,z,tip,yg_jack_length,3);
        yg_ycyl(yg_jack_x,z,tip+yg_jack_length,yg_head_h,yg_head_d);
        yg_nut(yg_jack_x,z,yg_nut_y);
        yg_washer(yg_jack_x,z,yg_lock_top);
        yg_nut(yg_jack_x,z,yg_lock_top+.5);
    }
}
module yg_cap_hardware_local(face=yg_face,skip="",skip_z=999){
    for(z=support_cap_screw_z)if(!(skip=="mount"&&z==skip_z))yg_station_hardware_local(z,false,face);
    for(z=yg_jack_z)if(!(skip=="jack"&&z==skip_z))yg_station_hardware_local(z,true,face);
}
module yg_caps(){for(s=[-1,1])yg_at(s)yg_cap_local();}
module yg_gibs(){for(s=[-1,1])yg_at(s)yg_gib_local();}
module yg_added_datums(){for(s=[-1,1])yg_at(s)yg_lower_datum_local();}
module yg_hardware(){for(s=[-1,1])yg_at(s)yg_cap_hardware_local();}
module yg_rail_sweep(){translate([yg_rail_dx,yg_rail_dy,0]){
    cg_rail_sweep();mirror([1,0,0])cg_rail_sweep();}}
module yg_local_tools(z,jack=true,face=yg_face){
    x=jack?yg_jack_x:support_cap_screw_x;
    y=(jack?face+yg_spine_back+yg_jack_length:yg_cap_top+.5)+yg_head_h+.05;
    yg_ycyl(x,z,y,45,yg_tool_d);
    if(jack){
        // Declared service envelope for a 5.5mm wrench: OD11, thickness3.
        // Handle points away from the other axial station, outside X bridges.
        difference(){yg_ycyl(x,z,yg_lock_top+.55,3,11);
            support_y_hex(x,z,yg_lock_top+.5,3.1,5.7);
            yg_box(x-2.85,x+2.85,yg_lock_top+.5,yg_lock_top+3.7,
                z,z+7);}
        yg_box(x-2,x+2,yg_lock_top+.55,yg_lock_top+3.55,
            z< -10?z-35:z,z< -10?z:z+35);
    }
}
// Translation sweeps of each primitive, not a hull around disjoint parts.
module yg_gib_remove_sweep(){yg_gib_local(travel=25);}
module yg_cap_remove_sweep(){yg_cap_local(25);}
module yg_new_nut_feed(){for(z=yg_jack_z)hull(){
    yg_nut(yg_jack_x,z,yg_nut_y);yg_nut(yg_jack_x,z,yg_nut_y-20);}}
if(is_undef(yg_library_mode)||!yg_library_mode){
    if(yg_part=="right-support")yg_right_support();
    else if(yg_part=="left-support")yg_left_support();
    else if(yg_part=="cap")yg_at()yg_cap_local();
    else if(yg_part=="gib")yg_at()yg_gib_local();
    else if(yg_part=="dimensions")echo("YG_DIMENSIONS",[
        ["fixed_y",yg_datum_y],["shown_face_y",yg_face],["work_range",[yg_work_min,yg_work_max]],
        ["hard_range",[yg_hard_min,yg_hard_max]],["bearing_bands_z",yg_bands],
        ["ear_float_xz",yg_pocket_clear],["rail_parallel_dy",[0,yg_face-24]],
        ["cap_outer_y",yg_cap_top],["fixed_stop_z",[support_guide_z0,support_guide_z1]]]);
    else assert(false,"Unknown Y-guide part");
}
