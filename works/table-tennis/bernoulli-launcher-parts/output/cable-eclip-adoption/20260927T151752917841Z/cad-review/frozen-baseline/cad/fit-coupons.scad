// Local fit coupons only, mm. No baseline clearances are changed by this file.
// FDM candidate directions are explicit below; material/nozzle are UNKNOWN.
// Contact surfaces are copied/cropped from candidate modules wherever possible.
revision_library_mode=true;
include <feeder-guide-revision.scad>
use <feeder-body.scad>
use <feeder-seam-candidate.scad>

coupon_part="layout";
coupon_eps=0.02;
coupon_holes=[5.3,2*(finger_tip_radius+radial_print_clearance),5.7];
coupon_labels=["53","55","57"];

module coupon_text(s,p,size=2.5) {
    translate(p) linear_extrude(height=1)
        text(s,size=size,halign="center",valign="center");
}
module radial_core(d=5.5) {
    difference() {
        union() {
            // Same nominal curved liner as body_inner_guide(), wall (47-42.5)/2.
            intersection() {
                body_tube(-7.05,14.05,guide_od,guide_id);
                translate([18,-6,-7.05])cube([8,12,14.05]);
            }
            // Actual outer seat's limiting round-hole thickness X31.5..33.5.
            translate([31.5,-6,-7.05])cube([2,12,14.05]);
        }
        translate([17,0,0])rotate([0,90,0])cylinder(h=18,d=d);
    }
}
module radial_actual_core() {
    intersection() {
        feeder_body_full();
        union() {
            translate([18,-6,-7.05])cube([8,12,14.05]);
            translate([31.5,-6,-7.05])cube([2,12,14.05]);
        }
    }
}
module radial_pair_coupon() {
    difference() {
        union() {
            cube([26,50,2]);
            for(i=[0:2])translate([-18,7+18*i,9])radial_core(coupon_holes[i]);
        }
        // Labels remain outside both walls and below rod centreline Z9.
        for(i=[0:2])coupon_text(coupon_labels[i],[21,7+18*i,1.6]);
    }
}
module finger_coupon() {
    // -X (toward the ball tip) becomes print +Z. Full real finger is retained.
    difference() {
        translate([6,8,31])rotate([0,90,0])union() {
            cam_finger_local();
            translate([27.9,-8,-6])cube([3.1,16,12]);
        }
        coupon_text("R5",[6,14.5,2.6],2);
    }
}
module slider_seat_raw() {
    union() {
        intersection() {
            revision_side_support_local();
            translate([43,-18,-15])cube([24,46,30]);
        }
        // Label tab outside the Y +/-4.5 sliding surfaces and fasteners.
        translate([66,9,-15])cube([8,7,3]);
    }
}
module slider_seat_coupon() {
    difference() {
        translate([-43,18,15])slider_seat_raw();
        coupon_text("S",[27,30.5,2.6],3);
    }
}
module slider_gib_coupon() {
    // Real gib, fully retracted s=0. Flat non-contact web back is the bed face.
    difference() {
        translate([-revision_x0,revision_ear_z1,-revision_rear(0)])
            rotate([90,0,0])revision_gib_local(0);
        coupon_text("G",[16,revision_ear_z1,revision_ear_depth-0.4],2.2);
    }
}
module slider_keeper_coupon() {
    // Actual keeper, including jack/nut holes and retraction stops.
    difference() {
        translate([-43.8,14,-revision_keeper_back_y])rotate([90,0,0])union() {
            revision_keeper_local();
            translate([59.8,revision_keeper_back_y,5])cube([7,2,6]);
        }
        coupon_text("K",[19.5,6,1.6],2.5);
    }
}

// Pin and seal modules reuse the seam candidate cutters. They do not adopt it
// into the baseline. The locator blind bottom remains the actual 4-3.2=0.8 mm.
module locator_hole_local(kind="31") {
    if(kind=="31")mirror([1,0,0])translate([0,-40,59])seam_locator_cut(0,false);
    else if(kind=="32")translate([0,-40,59])seam_locator_cut(0,true);
    else translate([0,40,-3])seam_locator_cut(1,true);
}
module locator_blank_local(index=0) {
    intersection() {
        translate([0,index==0?-40:40,index==0?59:-3])seam_locator_ear_blank(index);
        translate([0,-8,-5])cube([4,16,10]);
    }
}
module locator_coupon_raw() {
    difference() {
        union() {
            for(i=[0:2])translate([0,8+18*i,7])locator_blank_local(i==2?1:0);
            // Connect outside the pocket and preserve the real blind-hole back.
            translate([0,0,1])cube([4,54,3]);
        }
        for(i=[0:2])translate([0,8+18*i,7])
            locator_hole_local(i==0?"31":i==1?"32":"slot");
    }
}
module locator_coupon() {
    // Seam face is ON the bed, matching the current seam print-direction candidate.
    // Holes open at print Z=0; depth3.2. First-layer effects are deliberately tested.
    difference() {
        translate([14,0,0])rotate([0,-90,0])locator_coupon_raw();
        for(i=[0:2])coupon_text(["31","32","SL"][i],[11.5,8+18*i,3.6],2);
    }
}
module seal_core() {
    difference() {
        intersection() {
            body_tube(-12.5,25,49.4,45.4);
            translate([-4,21.5,-12.5])cube([4,4,25]);
        }
        // 0.8-mm groove centred in a 2-mm radial wall: nominal lands 0.6 each.
        seam_reservoir_segment(1,-11,11,23.7,23.7);
    }
}
module seal_coupon() {
    // Negative-half X0 seam face ON the bed. Groove is a bottom-layer feature.
    difference() {
        translate([16,-19,0])rotate([0,90,0])union() {
            seal_core();
            for(z=[-16,12])translate([-4,19,z])cube([4,10,4]);
        }
        coupon_text("08",[2,5,3.6],2.5);
    }
}

module coupon_layout() {
    radial_pair_coupon();
    translate([33,0,0])finger_coupon();
    translate([52,0,0])slider_seat_coupon();
    translate([90,0,0])slider_gib_coupon();
    translate([90,20,0])slider_keeper_coupon();
    translate([119,0,0])locator_coupon();
    translate([0,60,0])seal_coupon();
}
if(coupon_part=="radial-pair")radial_pair_coupon();
else if(coupon_part=="finger")finger_coupon();
else if(coupon_part=="slider-seat")slider_seat_coupon();
else if(coupon_part=="slider-gib")slider_gib_coupon();
else if(coupon_part=="slider-keeper")slider_keeper_coupon();
else if(coupon_part=="locator")locator_coupon();
else if(coupon_part=="seal")seal_coupon();
else if(coupon_part=="radial-reference-xor")union() {
    difference(){radial_core(coupon_holes[1]);radial_actual_core();}
    difference(){radial_actual_core();radial_core(coupon_holes[1]);}
}
else if(coupon_part=="radial-reference-actual")radial_actual_core();
else if(coupon_part=="radial-reference-derived")radial_core(coupon_holes[1]);
else coupon_layout();
