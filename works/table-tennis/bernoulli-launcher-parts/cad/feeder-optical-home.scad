// EE-SX675-WR 1M optical home candidate for the adopted cable-feeder geometry.
// mm, +Z = nominal 20 mm feeder travel. This replaces ONLY the left Y cap
// and moving spring spacer; it is not an actuator or a production release.
// The sensor reference follows Omron's EE-SX675-WR outline, 5 mm slot,
// 2 x diameter 3.2 mm holes on 19.5 mm centres (EE-series databook p.63).
include <parameters.scad>
use <feeder-frame-y-guide.scad>
use <feeder-return-spring.scad>
use <feeder-pin-seat-revision.scad>
use <launcher-final-assembly.scad>
use <cable-output-interface.scad>
use <cable-trigger-input.scad>
use <cable-trigger-system.scad>

oh_part = "local-assembly"; // left-cap, moving-spacer, sensor-reference, local-assembly, context, system, probe
oh_probe = "flag-sensor";
oh_t = 0;
oh_sensor_dz = 0; // 0..2 mm upward optical-edge trim after assembly
oh_eps = .02;

oh_sensor_x = -84;
oh_sensor_front = 18.8;
oh_sensor_back = 35.5;
oh_sensor_top = 16;
oh_hole_z = 0;
oh_optical_z = 13;
oh_optical_y = 21.5;
oh_slot = 5;
oh_slot_bottom = 7;
oh_slot_top = 16;
oh_flag_thickness = 1.2;
oh_flag_y0 = 19.5;
oh_flag_y1 = 28.5;

assert(oh_hole_z==0 && oh_optical_z==13);
assert(oh_sensor_dz>=0 && oh_sensor_dz<=2);
assert(oh_slot_top-oh_slot_bottom==9);
assert(oh_flag_thickness<oh_slot-2*1.5);
assert(oh_flag_y0<oh_optical_y && oh_flag_y1>oh_optical_y);

module oh_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module oh_ycyl(x,z,y0,length,d){
    translate([x,y0,z]) rotate([-90,0,0]) cylinder(h=length,d=d,$fn=48);
}
module oh_yhex(x,z,y0,length,af){
    translate([x,y0,z]) rotate([-90,0,0]) rotate([0,0,30])
        cylinder(h=length,d=af/cos(30),$fn=6);
}

// Print the actual LEFT guide cap with its original bearing, jack and mount
// holes. The added boss grows outboard of the left cap, with its root between
// the two old screw heads. No original screw stack or rail geometry changes.
module oh_cap_added(){difference(){union(){
    oh_box(-67,-64,31,38,-24,-5);      // overlap into cap; clears spring head
    oh_box(-76,-66,35.5,39.5,-8,-4);  // arm under the sensor mounting ears
    oh_box(-108,-68,35.5,39.5,-6,6);  // 4 mm face + outboard cable-tie eye
}
    // 2 mm of upward trim without putting the optical gate in the feeder
    // load path. OD10 rear washers cover the entire 5.5 mm slots.
    for(x=[oh_sensor_x-9.75,oh_sensor_x+9.75])
        hull() for(dz=[0,2]) oh_ycyl(x,oh_hole_z+dz,35.3,4.4,3.5);
    oh_ycyl(-104,0,35.3,4.4,4); // tie the fixed 1 m cable away from the fork
}}
module oh_left_cap(){union(){
    yg_at(-1)yg_cap_local();
    oh_cap_added();
}}

// Replace the original 7.5 OD / 4.4 ID moving spacer rather than clamping
// a loose part to it. The old shoulder-pin bore remains continuous. The
// flag travels through the fork while its crossbar runs above the sensor.
module oh_flag_added_rest(){difference(){union(){
    oh_box(-76,-73.5,24.5,oh_flag_y1,13,29);
    oh_box(-84.6,-74.5,oh_flag_y0,oh_flag_y1,26,29);
    oh_box(oh_sensor_x-oh_flag_thickness/2,
           oh_sensor_x+oh_flag_thickness/2,
           oh_flag_y0,oh_flag_y1,11,29);
}
    oh_ycyl(-72,13,24.3,7.6,4.4);
}}
module oh_flag_extension(t=oh_t){
    translate([0,0,cam_stroke*t]) oh_flag_added_rest();
}
module oh_moving_spacer(t=oh_t){union(){
    rs_spacer(false,t);
    oh_flag_extension(t);
}}

// Envelope proxy with documented outer dimensions and datum locations. The
// wide transverse ears put both screw axes 9.75 mm from the sensing plane;
// their entire head/washer stack lies below the moving flag. The vendor's
// exact fillets and cable boot are deliberately not claimed by this proxy.
module oh_sensor_reference(){translate([0,0,oh_sensor_dz]) difference(){union(){
    oh_box(oh_sensor_x-6.7,oh_sensor_x+6.7,
        oh_sensor_front,oh_sensor_back,oh_sensor_top-26.2,oh_slot_bottom);
    for(side=[-1,1])
        oh_box(side<0?oh_sensor_x-6.7:oh_sensor_x+oh_slot/2,
               side<0?oh_sensor_x-oh_slot/2:oh_sensor_x+6.7,
               oh_sensor_front,oh_sensor_back-4,oh_slot_bottom,oh_slot_top);
    oh_box(oh_sensor_x-13,oh_sensor_x+13,
           oh_sensor_back-4,oh_sensor_back,-3,3);
}
    for(x=[oh_sensor_x-9.75,oh_sensor_x+9.75])
        oh_ycyl(x,oh_hole_z,oh_sensor_back-4.2,4.4,3.2);
}}
module oh_sensor_fasteners(){translate([0,0,oh_sensor_dz]){
    for(x=[oh_sensor_x-9.75,oh_sensor_x+9.75]){
        // M3 x 16 through the 4 mm factory tab + 4 mm printed plate.
        // OD5.5 head seats directly on the 6 mm-wide factory ear; an OD7
        // front washer would cross into the sensor's central body. The OD10
        // washer on the rear spans the 5.5 mm-long adjustment slot.
        oh_ycyl(x,oh_hole_z,31.5,16,3);
        oh_ycyl(x,oh_hole_z,28.5,3,5.5);
        difference(){oh_ycyl(x,oh_hole_z,39.5,1,10);
            oh_ycyl(x,oh_hole_z,39.48,1.04,3.2);}
        // M3 nylon-insert nut envelope, four millimetres high.
        difference(){oh_yhex(x,oh_hole_z,40.5,4,5.5);
            oh_ycyl(x,oh_hole_z,40.48,4.04,3.2);}
    }
}}
module oh_sensor_heads(){translate([0,0,oh_sensor_dz])
    for(x=[oh_sensor_x-9.75,oh_sensor_x+9.75])
        oh_ycyl(x,oh_hole_z,28.5,3,5.5);
}
module oh_optical_point(){
    translate([oh_sensor_x,oh_optical_y,oh_optical_z+oh_sensor_dz]) sphere(d=.8,$fn=20);
}
module oh_optical_window(){
    // 2 x 0.8 mm specified minimum opaque target, swept across the 5 mm gap.
    oh_box(oh_sensor_x-oh_slot/2,oh_sensor_x+oh_slot/2,
        oh_optical_y-.4,oh_optical_y+.4,
        oh_optical_z+oh_sensor_dz-1,oh_optical_z+oh_sensor_dz+1);
}

// The original cap/spacer are display-only subtractions. The shop assembly
// replaces those two printed instances; it never adds four parts on top.
module oh_other_fixed(){difference(){ct_fixed_printed();yg_at(-1)yg_cap_local();}}
module oh_other_moving(t=oh_t){
    // Expanded from ct_moving_printed(); do not subtract a coincident old
    // spacer from a union and mistake zero-volume boundary triangles for a
    // collision with the replacement spacer.
    ps_carriers(t);ps_blocks(t);co_frame(t);co_lug_cap(t);
    ci_lever(cam_stroke*t);ci_terminal_cap(cam_stroke*t);
}
module oh_system(t=oh_t){
    color([.62,.71,.77,.38]) oh_other_fixed();
    color([.19,.46,.61]) oh_left_cap();
    color([.92,.59,.15]) {oh_other_moving(t);oh_moving_spacer(t);}
    color([.11,.11,.12]) oh_sensor_reference();
    color([.70,.71,.73]) oh_sensor_fasteners();
    color([.9,.1,.1]) oh_optical_point();
}
module oh_local_assembly(t=oh_t){
    color([.19,.46,.61]) oh_left_cap();
    color([.92,.59,.15]) oh_moving_spacer(t);
    color([.10,.10,.11]) oh_sensor_reference();
    color([.70,.71,.73]) oh_sensor_fasteners();
    color([.95,.15,.15]) oh_optical_point();
    color([.65,.67,.7]) rs_endpoint_hardware(false,t);
}
module oh_context(t=oh_t){
    region=[-115,-42,9,50,-44,56];
    color([.62,.71,.77,.28]) intersection(){
        oh_other_fixed();oh_box(region[0],region[1],region[2],region[3],region[4],region[5]);
    }
    color([.92,.59,.15,.65]) intersection(){
        oh_other_moving(t);oh_box(region[0],region[1],region[2],region[3],region[4],region[5]);
    }
    oh_local_assembly(t);
    color([.26,.70,.42]) rs_spring(t);
    color([.63,.65,.67]) rs_endpoint_hardware(true,0);
}
module oh_probe_geometry(){
    if(oh_probe=="cap-other-fixed") intersection(){
        oh_cap_added();oh_other_fixed();
    }
    else if(oh_probe=="cap-fixed-hardware") intersection(){
        oh_cap_added();ct_original_fixed_hardware();
    }
    else if(oh_probe=="cap-service-tools") intersection(){
        oh_cap_added();yg_at(-1){
            for(z=[-29,-1]) yg_local_tools(z,false);
            for(z=[-30.5,.5]) yg_local_tools(z,true);
        }
    }
    else if(oh_probe=="sensor-existing") intersection(){
        oh_sensor_reference();union(){oh_other_fixed();oh_other_moving(oh_t);
            ct_original_fixed_hardware();la_moving_hardware(oh_t);}
    }
    else if(oh_probe=="sensor-fasteners-existing") intersection(){
        oh_sensor_fasteners();union(){oh_other_fixed();oh_other_moving(oh_t);
            ct_original_fixed_hardware();la_moving_hardware(oh_t);}
    }
    else if(oh_probe=="sensor-head-body") intersection(){
        oh_sensor_heads();oh_sensor_reference();
    }
    else if(oh_probe=="flag-sensor") intersection(){
        oh_moving_spacer(oh_t);oh_sensor_reference();
    }
    else if(oh_probe=="beam-blocked") intersection(){
        oh_moving_spacer(oh_t);oh_optical_window();
    }
    else if(oh_probe=="flag-new-cap") intersection(){
        oh_moving_spacer(oh_t);oh_left_cap();
    }
    else if(oh_probe=="flag-other") intersection(){
        oh_moving_spacer(oh_t);union(){oh_other_fixed();oh_other_moving(oh_t);
            ct_original_fixed_hardware();la_moving_hardware(oh_t);}
    }
    else if(oh_probe=="flag-other-moving") intersection(){
        oh_moving_spacer(oh_t);oh_other_moving(oh_t);
    }
    else if(oh_probe=="flag-other-moving-hardware") intersection(){
        oh_moving_spacer(oh_t);la_moving_hardware(oh_t);
    }
    else if(oh_probe=="flag-extension-hardware") intersection(){
        oh_flag_extension(oh_t);la_moving_hardware(oh_t);
    }
    else if(oh_probe=="flag-extension-existing") intersection(){
        oh_flag_extension(oh_t);union(){oh_other_fixed();oh_other_moving(oh_t);
            ct_original_fixed_hardware();la_moving_hardware(oh_t);}
    }
    else if(oh_probe=="flag-other-fixed") intersection(){
        oh_moving_spacer(oh_t);oh_other_fixed();
    }
    else if(oh_probe=="flag-sensor-screws") intersection(){
        oh_moving_spacer(oh_t);oh_sensor_fasteners();
    }
    else if(oh_probe=="sensor-bolts") intersection(){
        oh_sensor_fasteners();union(){oh_left_cap();oh_sensor_reference();}
    }
    else if(oh_probe=="positive-control") intersection(){
        oh_moving_spacer(oh_t);oh_moving_spacer(oh_t);
    }
    else assert(false,"Unknown optical-home probe");
}

if(oh_part=="left-cap") oh_left_cap();
else if(oh_part=="moving-spacer") oh_moving_spacer();
else if(oh_part=="sensor-reference") oh_sensor_reference();
else if(oh_part=="sensor-hardware") oh_sensor_fasteners();
else if(oh_part=="local-assembly") oh_local_assembly();
else if(oh_part=="context") oh_context();
else if(oh_part=="system") oh_system();
else if(oh_part=="probe") oh_probe_geometry();
else assert(false,"Unknown optical-home part");
