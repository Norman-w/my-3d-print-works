// Schematic 45/30 mm rocker swept through the selected electric assembly.
// This is an engineering clearance tool, NOT a printable linkage or mount.
// Its pins, bearings, crossheads and load path are not dimensioned for use.
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>

rp_part = "probe"; // probe, context
rp_target = "fixed"; // fixed, moving, hardware
rp_plane_y = 63; // 45 shows the inward-plane counterexample
rp_t = 0; // 0..1 corresponds to 0..20 mm feeder travel
rp_pivot_x = 40;
rp_pivot_z = 23;
rp_input_r = 45;
rp_output_r = 30;
rp_half_swing = asin(1/3);
rp_angle = rp_half_swing*(2*rp_t-1);

assert(rp_t>=0 && rp_t<=1);
assert(rp_plane_y==45 || rp_plane_y==63);

module rp_ycyl(x,z,d,h){
    translate([x,0,z]) rotate([90,0,0])
        cylinder(d=d,h=h,center=true,$fn=64);
}
module rp_rocker(){
    translate([rp_pivot_x,rp_plane_y,rp_pivot_z])
        rotate([0,-rp_angle,0]) {
            hull(){rp_ycyl(0,0,10,5);rp_ycyl(rp_input_r,0,7,5);}
            rp_ycyl(rp_output_r,0,7,8);
        }
}
module rp_pivot_envelope(){
    translate([rp_pivot_x,rp_plane_y,rp_pivot_z])
        rotate([90,0,0]) cylinder(d=12,h=12,center=true,$fn=64);
}
module rp_proxy(){rp_rocker();rp_pivot_envelope();}
module rp_target_solid(){
    if(rp_target=="fixed") it_fixed_printed();
    else if(rp_target=="moving") it_moving_printed(rp_t,0);
    else if(rp_target=="hardware") {
        ed_fixed_hardware();ed_moving_hardware(rp_t);
    }
    else assert(false,"Unknown rocker-plane target");
}

if(rp_part=="probe") intersection(){rp_proxy();rp_target_solid();}
else if(rp_part=="self-control") intersection(){rp_proxy();rp_proxy();}
else if(rp_part=="context") {
    color([.74,.78,.80,.45]) it_assembly(rp_t,0);
    color([.15,.70,.47,.88]) rp_rocker();
    color([.99,.65,.10]) rp_pivot_envelope();
}
else assert(false,"Unknown rocker-plane screen part");
