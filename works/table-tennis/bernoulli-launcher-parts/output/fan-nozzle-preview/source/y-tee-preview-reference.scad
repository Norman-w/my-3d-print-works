// Display-only purchased Y fitting, NOT a print target or a measured replica.
// Visual source: Taobao 695023134217, gallery 1 + transparent-blue 50 SKU.
// Three enlarged sockets + terminal beads + narrower straight/oblique bodies.
// Source frame: air +Z; fan socket faces -Z; ball inlet faces +X and -Z.
// The ball inlet's INWARD vector has a positive +Z component (with the air).
// Origin: illustrative fan-socket stop. The printer part's exit face sits here.
// Socket ID is user-measured; largest OD / overall length are vendor-nominal.
// Other values are visual assumptions, NOT verified fit dimensions.

part = "reference";
y_socket_id = 50.2;
y_bore_id = 48;
y_body_od = 53.2;
y_socket_od = 55.2;
y_lip_od = 56.38;
y_socket_depth = 25;
y_lip_l = 5;
y_socket_transition_l = 3;
y_main_start = -y_socket_depth;
y_main_end = 128-y_socket_depth;
y_junction_z = 65;
y_branch_l = 70;
y_branch_angle = 135; // outward toward the FAN, not toward the discharge
y_fn = 160;
y_eps = 0.02;

function y_dir(a) = [sin(a), 0, cos(a)];
function y_branch_point(t) = [t*sin(y_branch_angle), 0,
                             y_junction_z+t*cos(y_branch_angle)];

module y_along(point, angle) {
    translate(point) rotate([0,angle,0]) children();
}

// Ordered from the stem/stop to the open mouth. Use each coaxial outline in
// ONE revolve instead of Boolean-unioning touching cylinders and sockets:
// coplanar seams can collapse into degenerate STL triangles at float precision.
function y_socket_profile() = [
    [y_body_od/2,0],
    [y_socket_od/2,y_socket_transition_l],
    [y_socket_od/2,y_socket_depth-y_lip_l-0.6],
    [y_lip_od/2,y_socket_depth-y_lip_l],
    [y_lip_od/2,y_socket_depth-0.5],
    [y_lip_od/2-0.35,y_socket_depth]
];
function y_forward_profile(stop) = [for(p=y_socket_profile()) [p[0],stop+p[1]]];
function y_rear_profile() = let(p=y_socket_profile())
    [for(i=[len(p)-1:-1:0]) [p[i][0],-p[i][1]]];

module y_main_outer() {
    rotate_extrude($fn=y_fn) polygon(concat(
        [[0,y_main_start]], y_rear_profile(),
        y_forward_profile(y_main_end-y_socket_depth), [[0,y_main_end]]));
}

module y_branch_outer() {
    rotate_extrude($fn=y_fn) polygon(concat(
        [[0,0],[y_body_od/2,0]],
        y_forward_profile(y_branch_l-y_socket_depth), [[0,y_branch_l]]));
}

module y_main_bore() {
    rotate_extrude($fn=y_fn) polygon([
        [0,y_main_start-y_eps],
        [y_socket_id/2+0.4,y_main_start-y_eps],
        [y_socket_id/2,y_main_start+0.8], [y_socket_id/2,0],
        [y_bore_id/2,0], [y_bore_id/2,y_main_end-y_socket_depth],
        [y_socket_id/2,y_main_end-y_socket_depth],
        [y_socket_id/2,y_main_end-0.8],
        [y_socket_id/2+0.4,y_main_end+y_eps], [0,y_main_end+y_eps]
    ]);
}

module y_branch_bore() {
    rotate_extrude($fn=y_fn) polygon([
        [0,-y_eps], [y_bore_id/2,-y_eps],
        [y_bore_id/2,y_branch_l-y_socket_depth],
        [y_socket_id/2,y_branch_l-y_socket_depth],
        [y_socket_id/2,y_branch_l-0.8],
        [y_socket_id/2+0.4,y_branch_l+y_eps], [0,y_branch_l+y_eps]
    ]);
}

module y_outer() {
    union() {
        y_main_outer();
        y_along([0,0,y_junction_z], y_branch_angle)
            y_branch_outer();
    }
}

module y_inner() {
    union() {
        y_main_bore();
        y_along([0,0,y_junction_z], y_branch_angle)
            y_branch_bore();
    }
}

module y_reference() { difference() { y_outer(); y_inner(); } }

assert(y_socket_id > y_bore_id && y_socket_od > y_socket_id);
assert(y_body_od > y_bore_id && y_lip_od > y_socket_od);
assert(y_branch_angle > 90 && y_branch_angle < 180);

if (part == "reference") y_reference();
else if (part == "contract") echo(y_reference_contract = [
    ["revision","y-tee-photo-v2-20261007"], ["units","mm"],
    ["source_item_id","695023134217"], ["print_target",false],
    ["source_sku_id","4929691240158"],
    ["vendor_nominal_socket_id",49.8], ["vendor_nominal_od",56.38],
    ["vendor_nominal_length",128],
    ["measured_socket_id",y_socket_id],
    ["illustrative_bore_id",y_bore_id], ["illustrative_body_od",y_body_od],
    ["illustrative_socket_od",y_socket_od], ["illustrative_lip_od",y_lip_od],
    ["illustrative_socket_depth",y_socket_depth],
    ["illustrative_lip_length",y_lip_l],
    ["illustrative_main_length",y_main_end-y_main_start],
    ["illustrative_junction_z",y_junction_z],
    ["illustrative_branch_length",y_branch_l],
    ["illustrative_branch_angle_deg",y_branch_angle],
    ["airflow_local",[0,0,1]],
    ["fan_port",[0,0,y_main_start]], ["fan_outward",[0,0,-1]],
    ["outlet_port",[0,0,y_main_end]], ["outlet_outward",[0,0,1]],
    ["ball_port",y_branch_point(y_branch_l)],
    ["ball_outward",y_dir(y_branch_angle)],
    ["display_rotation_deg",[0,-90,0]]
]);
else assert(false, "Unknown Y reference selector");
