// REV F / mm / X1C / unfilled PETG / 0.4 mm nozzle.
// Clear rectangular interior 130 x 100 x 50; 25 mm per half, 2.5 mm floors.
// Two INTERNAL catches actuated by sealed flexible front-wall pads.
// Short internal latches occupy the front service band outside the gasket.
// Textured finger recess straddles the FRONT SEAM.
// Side walls are smooth. The mouth recess stops before the continuous seal.
// Captive hinge pins lie within an enlarged rear service band, outside the seal.
// Seam is at H, with a stepped rear skirt and relief for an opening of 0..100 deg.
// Print a 90-degree opening in a V pose, both shells inclined 45 degrees.
// Local hinge supports only where slicing requires; no support in bearing gaps.
// Two captive rigid bodies print together; silicone gasket is a separate item.
// No inserted pins or separate latch hardware. Water seal and snap loads require
// physical first article; geometric checks cannot establish those properties.

model_mode = "print";
opening_angle = 90;
$fn = 64;
eps = .01;
inner_length = 130;
inner_width = 100;
inner_height_total = 50;
wall = 5.6;
base_floor = 2.5;
front_service = 6;
rear_service = 8;
outer_chamfer = 1.2;
seam_chamfer = .35;
release_membrane = .8;
latch_depth_shift = 10;
mechanism_keepout = 0;
latch_edge = 2.6;
latch_pocket_depth = 9;
finger_root_height = 17.5;
half_clear_height = inner_height_total/2;
half_height = base_floor+half_clear_height;
outer_length = inner_length+2*wall;
outer_width = inner_width+2*wall+front_service+rear_service;
inner_y = wall+front_service;
axis_y = outer_width-4.2;
axis_z = half_height;
hinge_centers = [30,outer_length-30];
pin_radius = 1.8;
radial_clearance = .35;
bore_bias = .15;
axial_clearance = .35;
bearing_radius = 3.2;
bearing_length = 6;
fork_width = 3.2;
fork_offset = bearing_length/2+axial_clearance;
rear_relief_y = inner_y+inner_width+4.6;
groove_inner_offset = 1.5;
groove_width = 2.6;
groove_depth = 1.45;
cord_diameter = 2;
latch_width = 12;
latch_thickness = 1.6;
latch_standoff = 2.2;
latch_play = .15;
front_centers = [35,outer_length-35];

assert(inner_height_total==50);
assert(rear_relief_y>inner_y+inner_width+groove_inner_offset+groove_width);
assert(axis_y+bearing_radius<outer_width);

module rounded_rect(l,w,r) {
    translate([r,r]) offset(r=r) square([l-2*r,w-2*r]);
}
// Broad top/bottom chamfers, plus a small bevel at the parting rim.
module outer_blank() {
    hull() {
        translate([outer_chamfer,outer_chamfer,0]) linear_extrude(eps)
            rounded_rect(outer_length-2*outer_chamfer,outer_width-2*outer_chamfer,wall-outer_chamfer);
        translate([0,0,outer_chamfer-eps]) linear_extrude(eps)
            rounded_rect(outer_length,outer_width,wall);
        translate([0,0,half_height-seam_chamfer]) linear_extrude(eps)
            rounded_rect(outer_length,outer_width,wall);
        translate([seam_chamfer,seam_chamfer,half_height-eps]) linear_extrude(eps)
            rounded_rect(outer_length-2*seam_chamfer,outer_width-2*seam_chamfer,wall-seam_chamfer);
    }
}
module seal_outline(d) {
    translate([wall,inner_y]) offset(r=d) square([inner_length,inner_width]);
}
module ring(inner,outer,z,h) {
    translate([0,0,z]) linear_extrude(h)
        difference() { seal_outline(outer); seal_outline(inner); }
}
module x_prism(x,length,points) {
    translate([x,0,0]) multmatrix([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1]])
        linear_extrude(length) polygon(points);
}
module x_cylinder(x,length,r) {
    translate([x,axis_y,axis_z]) rotate([0,90,0]) cylinder(h=length,r=r);
}
// Half of a finger pocket opens directly onto the front parting edge.
// Mirroring the lid forms a shared 40 mm mouth across the seam, ~8 mm high.
// Maximum reach Y=4 leaves 3.5 mm material before the groove's front edge Y=7.5.
// Three shallow channels texture the actual upper/lower contact lips.
module mouth_grip() {
    translate([outer_length/2,-.5,half_height]) scale([20,4.5,4]) sphere(r=1);
    for(y=[.8,2,3.2]) intersection() {
        translate([outer_length/2,-.5,half_height-.35])
            scale([20,4.5,4]) sphere(r=1);
        translate([outer_length/2-21,y-.3,half_height-5]) cube([42,.6,5+eps]);
    }
}
module shell(grooved=false) {
    difference() {
        outer_blank();
        translate([wall,inner_y,base_floor]) cube([inner_length,inner_width,half_clear_height+eps]);
        if(grooved) ring(groove_inner_offset,groove_inner_offset+groove_width,
                        half_height-groove_depth,groove_depth+eps);
        mouth_grip();
    }
}
// Internal relief leaves an unbroken .8 mm exterior skin: no exposed spring,
// open button slot, or water passage through the front wall. Travel ~1.5 mm
// and membrane fatigue must be evaluated on PETG first articles.
module release_pad_pockets() {
    for(cx=front_centers)
        translate([cx-12,release_membrane,3.5])
            cube([24,latch_pocket_depth-release_membrane,half_height-6.5]);
}
module latch_channels() {
    // Channel is outside the gasket front edge Y=7.5. Full-height wall at
    // Y>=7 protects the seal; the closed front skin hides the springs.
    for(cx=front_centers)
        translate([cx-10,release_membrane,half_height-3-eps])
            cube([20,7-release_membrane,3+2*eps]);
}
module release_pushers() {
    for(cx=front_centers)
        x_prism(cx-2,4,[[release_membrane-.2,half_height-14.7],
            [latch_edge+.5,half_height-14],[latch_edge+.5,half_height-12.95],
            [release_membrane-.2,half_height-12.3]]);
}
module catch() {
    // Two 5 mm catches at the beam edges avoid a long transverse bridge.
    for(x=[-8.5,3.5]) x_prism(x,5,
        [[.2,half_height-5.5-latch_depth_shift],[-.7,half_height-4.6-latch_depth_shift],
         [-.7,half_height-2.8-latch_depth_shift],[-1.8,half_height-2.8-latch_depth_shift],
         [-1.8,half_height-1.7-latch_depth_shift],[.2,half_height-latch_depth_shift]]);
}
module finger() {
    d=latch_standoff;
    union() {
        // Only ~3 mm of root bridge, attached to the rear of the service pocket.
        translate([-latch_width/2,-(latch_pocket_depth-latch_edge+.2),finger_root_height])
            cube([latch_width,latch_pocket_depth-latch_edge+.2-d-latch_thickness+.2,2]);
        translate([-latch_width/2,-d-latch_thickness,finger_root_height])
            cube([latch_width,latch_thickness,half_height+4.3+latch_depth_shift-finger_root_height]);
        x_prism(-latch_width/2,latch_width,
            [[-d-.1,half_height+2.8+latch_play+latch_depth_shift],[-.9,half_height+2.8+latch_play+latch_depth_shift],
             [-.9,half_height+3.15+latch_depth_shift],[-d-.05,half_height+4.25+latch_depth_shift],
             [-d-.1,half_height+4.25+latch_depth_shift]]);
    }
}
module front_positions() {
    // Reverse the edge normal: hooks and beams face INTO the cavity.
    for(cx=front_centers) translate([cx,latch_edge,0]) rotate([0,0,180]) children();
}
module internal_catch_bridges() {
    // Two short side arms, clear of the central spring and actuator. They run
    // along Y (inclined 45 degrees in print), not across a 24 mm empty pocket.
    for(cx=front_centers) for(x=[cx-8.5,cx+6.5])
        translate([x,latch_edge+.5,half_height-11.7])
            cube([2,latch_pocket_depth+.2-latch_edge-.5,2]);
}
module base_hinges() {
    for(cx=hinge_centers) {
        for(x=[cx-fork_offset-fork_width,cx+fork_offset]) {
            // Front-rooted fork stays clear of the rear cover's swept path.
            x_prism(x,fork_width,[[rear_relief_y-.3,half_height-2],
                [axis_y-2.8,half_height-1.4],[axis_y-2.8,half_height-.4],
                [rear_relief_y-.3,half_height-.4]]);
            x_cylinder(x,fork_width,bearing_radius);
        }
        x_cylinder(cx-fork_offset-eps,2*fork_offset+2*eps,pin_radius);
    }
}
module base_half(include_catches=true,include_pushers=true) {
    union() {
        difference() {
            shell(true);
            release_pad_pockets();
            latch_channels();
            // Rear relief is entirely OUTSIDE the uninterrupted seal land.
            translate([-eps,rear_relief_y,half_height-6])
                cube([outer_length+2*eps,outer_width-rear_relief_y+eps,10]);
        }
        base_hinges();
        // Raise the outer rear fascia while retaining its clearance at 100 deg.
        intersection() {
            translate([0,0,half_height-6.2]) linear_extrude(.9)
                rounded_rect(outer_length,outer_width,wall);
            translate([0,outer_width-.7,half_height-6.2]) cube([outer_length,.7,.9]);
        }
        if(include_pushers) release_pushers();
        if(include_catches) {
            front_positions() catch();
            internal_catch_bridges();
        }
    }
}
module lid_local(include_fingers=true) {
    union() {
        difference() {
            shell(false);
            for(cx=front_centers) translate([cx-12,release_membrane,base_floor])
                cube([24,latch_pocket_depth-release_membrane,half_height-3-base_floor]);
            latch_channels();
        }
        if(include_fingers) front_positions() finger();
    }
}
module lid_half_closed(include_fingers=true) {
    union() {
        difference() {
            union() {
                translate([0,0,2*half_height]) mirror([0,0,1]) lid_local(include_fingers);
                // Rear skirt covers most of the motion relief when closed.
                intersection() {
                    translate([0,0,half_height-4]) linear_extrude(4.2)
                        rounded_rect(outer_length,outer_width,wall);
                    translate([0,outer_width-1.4,half_height-4]) cube([outer_length,1.4,4.2]);
                }
            }
            // Clear entire fork sweeps; leave only the center sleeve added below.
            for(cx=hinge_centers)
                translate([cx-fork_offset-fork_width-.35,rear_relief_y,half_height-4.1])
                    cube([2*(fork_offset+fork_width+.35),outer_width-.7-rear_relief_y,8.2]);
        }
        for(cx=hinge_centers) difference() {
            union() {
                x_cylinder(cx-bearing_length/2,bearing_length,bearing_radius);
                translate([cx-bearing_length/2,axis_y-1.5,half_height+2.5]) cube([bearing_length,3,2.8]);
            }
            translate([0,0,bore_bias]) x_cylinder(cx-bearing_length/2-eps,
                bearing_length+2*eps,pin_radius+radial_clearance);
        }
    }
}
module lid_at(angle=0,include_fingers=true) {
    translate([0,axis_y,axis_z]) rotate([-angle,0,0])
        translate([0,-axis_y,-axis_z]) lid_half_closed(include_fingers);
}
module assembly(angle=90) {
    color([.22,.55,.64]) base_half();
    color([.83,.87,.89]) lid_at(angle);
}
module print_orientation() {
    // Outer bevels form narrow first-layer lands. Account for hull slice eps.
    translate([0,(-outer_chamfer+eps)/sqrt(2),(outer_width-outer_chamfer+eps)/sqrt(2)])
        rotate([-45,0,0]) children();
}
module section() {
    intersection() {
        assembly(0);
        translate([-1,-1,-1]) cube([outer_length+2,inner_y+inner_width/2+1,2*half_height+2]);
    }
}
module coupon() {
    intersection() {
        assembly(90);
        translate([hinge_centers[0]-12,rear_relief_y-5,0])
            cube([24,outer_width+half_height-rear_relief_y+10,half_height+22]);
    }
}
echo(str("REV_F nominal_inner=",inner_length,"x",inner_width,"x",inner_height_total,
    " half_depth=",half_clear_height," body=",outer_length,"x",outer_width,"x",2*half_height,
    " print_angle=90 front_latches=2 side_latches=0 mode=",model_mode));
if(model_mode=="print") print_orientation() assembly(90);
else if(model_mode=="closed") assembly(0);
else if(model_mode=="open90") assembly(90);
else if(model_mode=="base") base_half();
else if(model_mode=="lid") lid_half_closed();
else if(model_mode=="section") section();
else if(model_mode=="coupon") print_orientation() coupon();
else if(model_mode=="rigid_collision") intersection() { base_half(false); lid_at(opening_angle,false); }
else if(model_mode=="full_collision") intersection() { base_half(); lid_at(opening_angle); }
else assert(false,"Unknown model_mode");
