// Independent return-spring candidate. mm; +Z is the 20 mm trigger stroke.
// Manufacturer spring + metal hardware are REFERENCES, never print them.
// Source interface revision is NOT installed into ic_fixed().
cg_library_mode=true;
include <feeder-cam-guide-revision.scad>
use <feeder-integrated-candidate.scad>

rs_part="assembly";
rs_probe="spring-neighbors";
rs_t=0;
rs_remove=0;
rs_fault=0;
rs_spring_dy=0; // eye axial float within the two retaining washers
rs_relief=true;
rs_eps=.02;
rs_x=support_spring_x;
// Bias M3 shaft onto the upper end of the existing 3.4 mm slot.
// 0.02 display take-up avoids substituting a finely faceted pin for the
// existing 32-sided slot's exact loaded contact; assemble biased to upper end.
rs_fixed_z=support_spring_fixed_slot_z[1]+(fastener_d-3)/2-.02;
rs_moving_z=support_spring_moving_z;
rs_y=33.1;
rs_head_y=34.5;
rs_spacer_end_y=31.7;
rs_washer_od=8; // DIN 433 M4, ID4.3 x .5, not a generic M4 OD9 washer.
rs_nut_h=2.4; // Standard full-height M3 nut; thin-nut workaround superseded.
rs_thread_length=9; // MISUMI HDMSB4-16-F9-M3 / HDMSB4-10-F9-M3.
rs_spring_od=7;
rs_wire=.63;
rs_spring_L0=25.6;
rs_spring_F0=1.67;
rs_spring_k=.25;
rs_spring_Fmax=12.2;
rs_spring_Lmax=67.21;
rs_spring_check_od=7.5; // explicit provisional envelope, not DIN tolerance.
rs_pin_d=4;
rs_loop_id=rs_spring_od-2*rs_wire;
rs_hook_offset=(rs_loop_id-rs_pin_d)/2;
rs_coil_offset=rs_hook_offset+rs_spring_od/2;
$fn=72;

function rs_top(t)=rs_moving_z+cam_stroke*t;
function rs_L(t)=rs_top(t)-rs_fixed_z+rs_pin_d;
module rs_ycyl(z,y,h,d){translate([rs_x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module rs_yhex(z,y,h,af){translate([rs_x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module rs_nut_relief(){
    translate([rs_x-nut_af/2,11.4-rs_eps,-11])cube([nut_af,2.6+rs_eps,.8]);
}
// Public replacement module; the parent must explicitly replace its OLD left
// support. Never union this replacement over the old support (it refills cut).
module rs_left_support(){difference(){
    union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
    rs_nut_relief();
}}
module rs_fixed(){difference(){ic_fixed();if(rs_relief)rs_nut_relief();}}
module rs_neighbors(t=rs_t){rs_fixed();cg_moving(t);}
module rs_spacer(fixed=true,t=rs_t){
    z=fixed?rs_fixed_z:rs_top(t);y=fixed?18.5:24.5;
    difference(){rs_ycyl(z,y,rs_spacer_end_y-y,7.5);rs_ycyl(z,y-rs_eps,rs_spacer_end_y-y+2*rs_eps,4.4);}
}
module rs_washer(z,y){difference(){rs_ycyl(z,y,.5,rs_washer_od);rs_ycyl(z,y-rs_eps,.5+2*rs_eps,4.3);}}
module rs_nut(z,y){difference(){rs_yhex(z,y,rs_nut_h,5.5);rs_ycyl(z,y-rs_eps,rs_nut_h+2*rs_eps,3);}}
module rs_pin(fixed=true,t=rs_t){
    z=fixed?rs_fixed_z:rs_top(t);seat=fixed?18.5:24.5;
    rs_ycyl(z,seat-rs_thread_length,rs_thread_length,3);
    rs_ycyl(z,seat,rs_head_y-seat,4);
    rs_ycyl(z,rs_head_y,3,7);
}
// Public, disjoint fixed/moving hardware for the final assembly's partitions.
module rs_endpoint_hardware(fixed=true,t=0){
        z=fixed?rs_fixed_z:rs_top(t);
        rs_pin(fixed,t);rs_washer(z,rs_spacer_end_y);rs_washer(z,rs_head_y-.5);
        // M3 metal bearing washer spreads the shoulder load onto the host.
        difference(){rs_ycyl(z,fixed?18:24,.5,7);rs_ycyl(z,(fixed?18:24)-rs_eps,.5+2*rs_eps,3.2);}
        rs_nut(z,(fixed?14:20)-rs_nut_h);
}
module rs_fasteners(t=rs_t){for(f=[true,false])rs_endpoint_hardware(f,t);}
module rs_spacers(t=rs_t){rs_spacer(true,t);rs_spacer(false,t);}
// Conservative rectangular wire section around full-diameter INLINE loops.
// The small hook mouth and exact end crossover are intentionally NOT invented.
// This reconstructed outline is a fit candidate, not a factory wire/CAD model.
module rs_loop(z){difference(){
    rs_ycyl(z,rs_y-rs_wire/2,rs_wire,rs_spring_od);
    rs_ycyl(z,rs_y-rs_wire/2-rs_eps,rs_wire+2*rs_eps,rs_loop_id);
}}
module rs_spring(t=rs_t,clearance=false,dy=rs_spring_dy){translate([0,dy,0])union(){
    rs_loop(rs_fixed_z+rs_hook_offset);
    rs_loop(rs_top(t)-rs_hook_offset);
    translate([rs_x,rs_y,rs_fixed_z+rs_coil_offset])difference(){
        cylinder(h=rs_top(t)-rs_fixed_z-2*rs_coil_offset,d=clearance?rs_spring_check_od:rs_spring_od);
        if(!clearance)translate([0,0,-rs_eps])cylinder(h=100,d=rs_loop_id);
    }
}}
module rs_spring_sweep(){
    // Convex hull is a conservative continuous envelope; it fills the eye holes.
    // Legacy diagnostic only: it also fills the lower hook/coil concavity.
    hull()for(t=[0,1],dy=[-.585,.585])rs_spring(t,true,dy);
}
module rs_loop_sweep(z0,z1,pad=0){
    // Axial float expands only Y extrusion. A stationary ring keeps its hole.
    y0=rs_y-rs_wire/2-.585-pad;thickness=rs_wire+2*.585+2*pad;
    if(abs(z1-z0)<rs_eps)difference(){
        rs_ycyl(z0,y0,thickness,rs_spring_od+2*pad);
        rs_ycyl(z0,y0-rs_eps,thickness+2*rs_eps,rs_loop_id-2*pad);
    }else{
        // For stroke >= inner diameter, the translating ring's two Z
        // intervals overlap at every X: its TRUE union is the outer capsule.
        assert(abs(z1-z0)>=rs_loop_id,"Short ring strokes require another sweep construction");
        hull()for(z=[z0,z1])rs_ycyl(z,y0,thickness,rs_spring_od+2*pad);
    }
}
// Contains every catalog-envelope pose t=[0,1], dy=[-.585,.585].
// In moving_frame=true, express poses after translation [0,0,-cam_stroke*t]
// and compare ONLY with the moving endpoint/frame at t=0.
module rs_spring_continuous_sweep(moving_frame=false,numerical_cover_pad=0){
    // Pad is ONLY for coincident-boundary coverage DIFFERENCE diagnostics.
    // All collision probes use the default zero pad; it is not print allowance.
    pad=numerical_cover_pad;
    f=rs_fixed_z+rs_hook_offset;m=rs_top(0)-rs_hook_offset;
    rs_loop_sweep(moving_frame?f-cam_stroke:f,f,pad);
    rs_loop_sweep(m,moving_frame?m:m+cam_stroke,pad);
    z0=rs_fixed_z+rs_coil_offset-(moving_frame?cam_stroke:0);
    z1=rs_top(moving_frame?0:1)-rs_coil_offset;
    hull()for(dy=[-.585,.585])translate([rs_x,rs_y+dy,z0-pad])
        cylinder(h=z1-z0+2*pad,d=rs_spring_check_od+2*pad);
}
module rs_tools_legacy_solid(t=rs_t){
    for(z=[rs_fixed_z,rs_top(t)])rs_ycyl(z,rs_head_y+3.1,45,4);
    rs_ycyl(rs_top(t),-20,39.9-rs_nut_h,9);
}
module rs_socket_outer(t=rs_t){
    // GEDORE 2133 5.5: head OD8, shaft OD5, blade125. OD9 throughout
    // is a conservative access budget, not a claimed factory contour.
    rs_ycyl(rs_top(t),19.9-125,125,9);
}
module rs_socket_cavity(t=rs_t,depth=25){
    // Official 25 mm head depth; AF5.5 matches the nut. The centre is OPEN
    // for its 2.1 mm projecting screw. No blind-solid tool through that screw.
    rs_yhex(rs_top(t),19.9-depth,depth+rs_eps,5.5);
}
module rs_tools(t=rs_t){
    for(z=[rs_fixed_z,rs_top(t)])rs_ycyl(z,rs_head_y+3.1,45,4);
    difference(){rs_socket_outer(t);rs_socket_cavity(t);}
}
module rs_nut_feed(){
    hull(){rs_yhex(rs_fixed_z,-5,rs_nut_h,5.5);rs_yhex(rs_fixed_z,14-rs_nut_h,rs_nut_h,5.5);}
}
module rs_pin_feed(t=rs_t){
    for(f=[true,false]){
        z=f?rs_fixed_z:rs_top(t);seat=f?18.5:24.5;
        // Exact +Y translational sweep of each coaxial primitive, rather than
        // a hull that would incorrectly extend the head through the M3 hole.
        rs_ycyl(z,seat-rs_thread_length,rs_thread_length+35,3);
        rs_ycyl(z,seat,rs_head_y-seat+35,4);
        rs_ycyl(z,rs_head_y,38,7);
    }
}
module rs_show(){
    color([.65,.7,.74,.35])rs_fixed();
    color([.22,.48,.7,.5])cg_moving(rs_t);
    color([.95,.59,.15])rs_spacers();
    color([.24,.27,.3])rs_fasteners();
    color([.12,.67,.45])rs_spring();
}
module rs_probe_geometry(){
    if(rs_probe=="spring-neighbors")intersection(){rs_spring(rs_t,true);rs_neighbors();}
    else if(rs_probe=="spring-hardware")intersection(){rs_spring();union(){rs_fasteners();rs_spacers();}}
    else if(rs_probe=="hardware-fit")intersection(){rs_fasteners();rs_neighbors();}
    else if(rs_probe=="spacer-fit")intersection(){rs_spacers();union(){rs_neighbors();rs_fasteners();}}
    else if(rs_probe=="spring-sweep")intersection(){rs_spring_sweep();rs_fixed();}
    else if(rs_probe=="moving-end-sweep")intersection(){hull(){rs_pin(false,0);rs_pin(false,1);rs_spacer(false,0);rs_spacer(false,1);}rs_fixed();}
    else if(rs_probe=="tools")intersection(){rs_tools();union(){rs_neighbors();rs_spacers();rs_fasteners();}}
    else if(rs_probe=="continuous-fixed")intersection(){rs_spring_continuous_sweep();union(){rs_fixed();rs_spacer(true,0);rs_endpoint_hardware(true,0);}}
    else if(rs_probe=="continuous-moving")intersection(){rs_spring_continuous_sweep(true);union(){feeder_carriage(0);rs_spacer(false,0);rs_endpoint_hardware(false,0);}}
    else if(rs_probe=="sweep-coverage-fixed")difference(){rs_spring(rs_t,true);rs_spring_continuous_sweep(numerical_cover_pad=.00001);}
    else if(rs_probe=="sweep-coverage-moving")difference(){translate([0,0,-cam_stroke*rs_t])rs_spring(rs_t,true);rs_spring_continuous_sweep(true,.00001);}
    else if(rs_probe=="sweep-coverage-control")difference(){rs_spring(0,true);translate([.1,0,0])rs_spring_continuous_sweep(numerical_cover_pad=.00001);}
    else if(rs_probe=="legacy-sweep-spacer-control")intersection(){rs_spring_sweep();rs_spacer(true,0);}
    else if(rs_probe=="legacy-solid-tool-control")intersection(){rs_tools_legacy_solid();rs_endpoint_hardware(false,rs_t);}
    else if(rs_probe=="socket-cavity-target")difference(){intersection(){rs_socket_outer();rs_endpoint_hardware(false,rs_t);}rs_socket_cavity();}
    else if(rs_probe=="short-socket-control")intersection(){difference(){rs_socket_outer();rs_socket_cavity(depth=1);}rs_endpoint_hardware(false,rs_t);}
    else if(rs_probe=="nut-feed")intersection(){rs_nut_feed();rs_neighbors();}
    else if(rs_probe=="pin-feed")intersection(){rs_pin_feed();rs_neighbors();}
    else if(rs_probe=="relief-only")intersection(){ic_fixed();rs_nut_relief();}
    else if(rs_probe=="front-bearing-unchanged")intersection(){rs_nut_relief();translate([-76,14,-42])cube([13,4,33]);}
    else if(rs_probe=="old-nut-margin-control")intersection(){rs_nut_feed();ic_fixed();}
    else if(rs_probe=="spring-fault")intersection(){translate([rs_fault,0,0])rs_spring(rs_t,true);rs_neighbors();}
    else if(rs_probe=="oversize-washer-control")intersection(){rs_spring();for(z=[rs_fixed_z,rs_top(rs_t)])rs_ycyl(z,rs_head_y-.5,.5,12);}
    else assert(false,"Unknown return spring probe");
}
if(is_undef(rs_library_mode)||!rs_library_mode){
    if(rs_part=="fixed-spacer")rs_spacer(true,0);
    else if(rs_part=="moving-spacer")rs_spacer(false,0);
    else if(rs_part=="left-support")rs_left_support();
    else if(rs_part=="spring-reference")rs_spring();
    else if(rs_part=="hardware-reference")rs_fasteners();
    else if(rs_part=="local")intersection(){rs_show();translate([-84,6,-43])cube([34,39,83]);}
    else if(rs_part=="section")intersection(){rs_show();translate([-90,-100,-80])cube([18,220,140]);}
    else if(rs_part=="probe")rs_probe_geometry();
    else rs_show();
}
