// Independent review candidate; NOT adopted into feeder-body or released.
// Wrap the actual body; do not replace its guide, ports, mounts or fasteners.
include <parameters.scad>
use <feeder-body.scad>

seam_part = "assembly";
seam_eps = 0.02;
seam_explode = 12;
seam_locator_y = [40,-40];
seam_locator_z = [-59,3];
seam_ear_r = 4;
seam_ear_half_x = 4;
seam_foot_y_inner = 33;
seam_foot_y_outer = 35;
seam_foot_half_z = 3;
seam_pin_d = 3;
seam_pin_length = 6;
seam_fixed_hole_d = 3.1;
seam_round_hole_d = 3.2;
seam_slot_width = 3.2;
seam_slot_length = 4.2;
seam_hole_depth = 3.2;
seam_groove_width = 0.8;
seam_groove_depth = 0.2;
seam_spigot_bore = 45.4; // Current feeder-body scalar contract, not measured.
seam_outlet_stop = 2;
seam_split_bolt_z = [-72,-46,-10,16];

seam_body_od = body_id+2*body_wall;
seam_inlet_shoulder = guide_start_z-transition_length;
seam_inlet_start = seam_inlet_shoulder-feed_socket_length;
seam_guide_end = guide_start_z+guide_length;
seam_outlet_shoulder = seam_guide_end+transition_length;
seam_socket_start = seam_outlet_shoulder+seam_outlet_stop;
seam_outlet_end = seam_socket_start+y_stub_engagement;
seam_socket_id = y_stub_od+2*interface_radial_clearance;
seam_outlet_od = seam_socket_id+2*body_wall;
seam_locator_delta = [seam_locator_y[1]-seam_locator_y[0],
                      seam_locator_z[1]-seam_locator_z[0]];
seam_locator_span = norm(seam_locator_delta);
seam_slot_unit = seam_locator_delta/seam_locator_span;
// Segment Z extents, mean outer-shell radius at each bound. Ends are closed.
function seam_lerp(a,b,t) = a+(b-a)*t;
function seam_inlet_r(z) = seam_lerp((hose_od+seam_spigot_bore)/4,
    (seam_body_od+body_id)/4,(z-seam_inlet_shoulder)/transition_length);
function seam_outlet_r(z) = seam_lerp((seam_body_od+body_id)/4,
    (seam_outlet_od+seam_spigot_bore)/4,(z-seam_guide_end)/transition_length);
seam_segments = [
    [seam_inlet_start+1,seam_inlet_shoulder-1,
     (feed_socket_od+seam_spigot_bore)/4,(feed_socket_od+seam_spigot_bore)/4],
    [seam_inlet_shoulder+1,guide_start_z-1,
     seam_inlet_r(seam_inlet_shoulder+1),seam_inlet_r(guide_start_z-1)],
    [guide_start_z+1,seam_guide_end-1,
     (seam_body_od+body_id)/4,(seam_body_od+body_id)/4],
    [seam_guide_end+1,seam_outlet_shoulder-1,
     seam_outlet_r(seam_guide_end+1),seam_outlet_r(seam_outlet_shoulder-1)],
    [seam_socket_start+1,seam_outlet_end-1,
     (seam_outlet_od+seam_socket_id)/4,(seam_outlet_od+seam_socket_id)/4]
];

assert(seam_ear_half_x>seam_hole_depth);
assert(2*seam_hole_depth>seam_pin_length);
assert(seam_foot_y_inner>body_id/2);
assert(seam_foot_y_outer<=seam_body_od/2);
assert(seam_slot_length>seam_slot_width && seam_fixed_hole_d>seam_pin_d);
assert(seam_groove_depth>0 && seam_groove_width<2*body_wall);

seam_dimension_pairs = [
    ["locator_y",seam_locator_y],["locator_z",seam_locator_z],
    ["ear_radius",seam_ear_r],["ear_half_x",seam_ear_half_x],
    ["foot_y_inner",seam_foot_y_inner],["foot_y_outer",seam_foot_y_outer],
    ["foot_half_z",seam_foot_half_z],["pin_d",seam_pin_d],
    ["pin_length",seam_pin_length],["fixed_hole_d",seam_fixed_hole_d],
    ["round_hole_d",seam_round_hole_d],["slot_width",seam_slot_width],
    ["slot_length",seam_slot_length],["hole_depth",seam_hole_depth],
    ["groove_width",seam_groove_width],["groove_depth",seam_groove_depth],
    ["segments",seam_segments],["spigot_bore",seam_spigot_bore],
    ["inlet_od",feed_socket_od],["body_id",body_id],["body_od",seam_body_od],
    ["socket_id",seam_socket_id],["socket_od",seam_outlet_od],
    ["body_z",[seam_inlet_start,seam_outlet_end]],
    ["gate_z",[0,-gate_spacing]],["nominal_split_gap",0],
    ["split_bolt_z",seam_split_bolt_z],["body_polygon_fn",$fn]
];

module seam_x_cylinder(x,h,d,y,z,fn=72) {
    translate([x,y,z]) rotate([0,90,0]) cylinder(h=h,d=d,$fn=fn);
}

module seam_halfspace(positive) {
    translate([positive?0:-100,-100,seam_inlet_start-1])
        cube([100,200,seam_outlet_end-seam_inlet_start+2]);
}

// A volumetric root overlaps the existing cylindrical shell. The convex hull
// stays outside |Y|=33, so it cannot enter the ID64 bypass cavity.
module seam_locator_ear_blank(index=0) {
    y=seam_locator_y[index]; z=seam_locator_z[index];
    hull() {
        seam_x_cylinder(-seam_ear_half_x,2*seam_ear_half_x,
            2*seam_ear_r,y,z);
        translate([-seam_ear_half_x,y>0?seam_foot_y_inner:-seam_foot_y_outer,
            z-seam_foot_half_z])
            cube([2*seam_ear_half_x,seam_foot_y_outer-seam_foot_y_inner,
                2*seam_foot_half_z]);
    }
}

// Public cutter interface for direction-matched fit coupons. The negative half
// has two round pockets; positive index 1 is a capsule, not a rectangular slot.
module seam_locator_cut(index=0,positive=true) {
    x=positive?-seam_eps:-seam_hole_depth;
    h=seam_hole_depth+seam_eps;
    y=seam_locator_y[index]; z=seam_locator_z[index];
    if(positive && index==1)
        hull() for(s=[-1,1])
            seam_x_cylinder(x,h,seam_slot_width,
                y+s*(seam_slot_length-seam_slot_width)/2*seam_slot_unit[0],
                z+s*(seam_slot_length-seam_slot_width)/2*seam_slot_unit[1]);
    else seam_x_cylinder(x,h,positive?seam_round_hole_d:seam_fixed_hole_d,y,z);
}

// rlo/rhi specify the mean radius at the requested total Z extents. Round ends
// are inset by half width, so the actual channel does not run to the port edge.
module seam_reservoir_segment(sign,zlo,zhi,rlo,rhi) {
    radius=seam_groove_width/2;
    hull() for(z=[zlo+radius,zhi-radius])
        seam_x_cylinder(-seam_groove_depth,seam_groove_depth+seam_eps,
            seam_groove_width,sign*seam_lerp(rlo,rhi,(z-zlo)/(zhi-zlo)),z,48);
}

module seam_reservoir_cuts() {
    for(s=[-1,1],a=seam_segments)
        seam_reservoir_segment(s,a[0],a[1],a[2],a[3]);
}

module seam_candidate_half(positive=true) {
    difference() {
        intersection() {
            union() {
                feeder_body_full();
                for(i=[0,1]) seam_locator_ear_blank(i);
            }
            seam_halfspace(positive);
        }
        for(i=[0,1]) seam_locator_cut(i,positive);
        if(!positive) seam_reservoir_cuts();
    }
}

module seam_pins(length=seam_pin_length,offset_y=0) {
    for(i=[0,1]) seam_x_cylinder(-seam_hole_depth,length,seam_pin_d,
        seam_locator_y[i]+offset_y,seam_locator_z[i]);
}

// Exact continuous convex sweeps, not a finite set of sampled insertion poses.
module seam_pin_insertion_sweep() {
    for(i=[0,1]) hull() {
        seam_x_cylinder(-seam_hole_depth,seam_pin_length,seam_pin_d,
            seam_locator_y[i],seam_locator_z[i]);
        seam_x_cylinder(0,seam_pin_length,seam_pin_d,
            seam_locator_y[i],seam_locator_z[i]);
    }
}

module seam_cover_pin_sweep() {
    // Positive half closes from X=+8 to 0. Hold it fixed and move pins oppositely.
    for(i=[0,1]) hull() {
        seam_x_cylinder(-seam_hole_depth,seam_pin_length,seam_pin_d,
            seam_locator_y[i],seam_locator_z[i]);
        seam_x_cylinder(-seam_hole_depth-8,seam_pin_length,seam_pin_d,
            seam_locator_y[i],seam_locator_z[i]);
    }
}

module seam_dry_stop_regions() {
    // Inspection regions only, not added pads. Existing coplanar faces are dry.
    for(y=[-40,40],z=seam_split_bolt_z)
        difference() {
            seam_x_cylinder(-0.01,0.02,8,y,z);
            seam_x_cylinder(-0.02,0.04,fastener_d,y,z);
        }
    for(s=[-1,1],z=[-64,-20,8])
        translate([-0.01,s>0?25:-30,z]) cube([0.02,5,3]);
}

module seam_preview(exploded=false) {
    color([0.36,0.63,0.77]) seam_candidate_half(false);
    color([0.74,0.79,0.83]) translate([exploded?seam_explode:0,0,0])
        seam_candidate_half(true);
    color([0.86,0.63,0.18]) seam_pins();
}

echo("REVIEW ONLY: hard seam X=0; PETG sealant, ports, tolerances and air tightness OPEN");
echo("locator span",seam_locator_span,"blind bottom",seam_ear_half_x-seam_hole_depth,
     "pin axial slack",2*seam_hole_depth-seam_pin_length);
if(seam_part=="negative_half") seam_candidate_half(false);
else if(seam_part=="positive_half") seam_candidate_half(true);
else if(seam_part=="assembly") seam_preview();
else if(seam_part=="exploded") seam_preview(true);
else if(seam_part=="negative_face") {
    color([0.36,0.63,0.77]) seam_candidate_half(false);
    color([0.90,0.65,0.16]) seam_dry_stop_regions();
}
else if(seam_part=="halves_interference") intersection() {
    seam_candidate_half(false); seam_candidate_half(true);
}
else if(seam_part=="pins_interference") intersection() {
    seam_pins(); union() { seam_candidate_half(false); seam_candidate_half(true); }
}
else if(seam_part=="pin_insertion") intersection() {
    seam_candidate_half(false); seam_pin_insertion_sweep();
}
else if(seam_part=="cover_insertion") intersection() {
    seam_candidate_half(true); seam_cover_pin_sweep();
}
else if(seam_part=="ear_connection") intersection() {
    feeder_body_full(); for(i=[0,1]) seam_locator_ear_blank(i);
}
else if(seam_part=="cavity_intrusion") intersection() {
    for(i=[0,1]) seam_locator_ear_blank(i);
    translate([0,0,guide_start_z]) cylinder(h=guide_length,d=body_id);
}
else if(seam_part=="dry_stop_cut") intersection() {
    seam_reservoir_cuts(); seam_dry_stop_regions();
}
else if(seam_part=="groove_breakthrough") difference() {
    intersection() { seam_reservoir_cuts(); seam_halfspace(false); }
    body_outer_shell();
}
else if(seam_part=="original_fasteners_refilled") intersection() {
    for(i=[0,1]) seam_locator_ear_blank(i);
    union() { body_split_fastener_cuts(); body_side_cuts(); }
}
else if(seam_part=="guide_changed") intersection() {
    union() {
        difference() {
            feeder_body_full();
            union() { seam_candidate_half(false); seam_candidate_half(true); }
        }
        difference() {
            union() { seam_candidate_half(false); seam_candidate_half(true); }
            feeder_body_full();
        }
    }
    translate([0,0,guide_start_z]) cylinder(h=guide_length,d=body_id);
}
else if(seam_part=="overclose_control") intersection() {
    seam_candidate_half(false); translate([-0.1,0,0]) seam_candidate_half(true);
}
else if(seam_part=="long_pin_control") intersection() {
    seam_pins(length=6.6); seam_candidate_half(true);
}
else if(seam_part=="offset_pin_control") intersection() {
    seam_pins(offset_y=0.3); seam_candidate_half(false);
}
else if(seam_part=="dimensions") echo("SEAM_DIMENSIONS",seam_dimension_pairs);
else assert(false,"Unknown seam candidate part");
