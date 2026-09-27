// Removable guide for route bend 3 only. Not a release for the free housing route.
// All geometry derives from cr_arc(3); do not relocate either cable port here.
use <cable-housing-route.scad>
use <cable-output-interface.scad>
use <cable-trigger-system.scad>
use <cable-trigger-input.scad>
use <launcher-final-assembly.scad>
use <feeder-return-spring.scad>
use <outlet-retention.scad>
use <inlet-retention-final.scad>

crr_part="assembly";
crr_test="host";
crr_t=0;
crr_fn=32;
crr_eps=.02;
crr_bore=6.2;
crr_band=17;
crr_base_depth=7;
crr_cap_depth=5;
crr_mount_stations=[-12,12];
crr_mount_x=[-73,-43];
crr_fastener_angles=[10,70,137];
crr_fastener_radii=[63,87];

function crr_arc()=cr_arc(3);
function crr_C()=crr_arc()[2];
function crr_U()=crr_arc()[3];
function crr_V()=crr_arc()[4];
function crr_N()=cross(crr_U(),crr_V());
function crr_global(p)=crr_C()+p[0]*crr_U()+p[1]*crr_V()+p[2]*crr_N();
function crr_local(p)=let(v=p-crr_C())[v*crr_U(),v*crr_V(),v*crr_N()];
function crr_radius()=norm(crr_arc()[0]-crr_C());
function crr_path()=let(a=crr_arc(),n=ceil(a[5]/2),r=crr_radius())concat(
    [[r,-15,0]], [for(k=[0:n])[r*cos(a[5]*k/n),r*sin(a[5]*k/n),0]],
    [crr_local(cr_output_port()+[0,0,15])]);
function crr_bolt_points()=[for(a=crr_fastener_angles)for(r=crr_fastener_radii)[r*cos(a),r*sin(a),0]];
function crr_contract()=[
    ["status","local-guide-candidate-not-print-release"],
    ["guided_route_arc",3],["arc_radius",crr_radius()],
    ["arc_angle",crr_arc()[5]],["guide_start",crr_global(crr_path()[0])],
    ["guide_end",crr_global(crr_path()[len(crr_path())-1])],
    ["housing_od",5],["groove_id",crr_bore],["radial_clearance",(crr_bore-5)/2],
    ["side_loading_direction",crr_N()],
    ["host_platform",[[-70,-52,85],[-46,45,93]]],
    ["clamp_clearance_per_face",.3],
    ["clamp_bolt_centres",[for(x=crr_mount_x)for(y=crr_mount_stations)[x,y]]],
    ["clamp_bolt_candidate","M3x25 socket head + OD7 x 0.5 washer + AF5.5 x 2.4 nut"],
    ["cap_bolt_candidate","M3x16 socket head + OD7 x 0.5 washer + AF5.5 x 2.4 nut"],
    ["thread_dimensions","nominal envelopes; purchase and strength not confirmed"],
    ["free_route_supported",false],
    ["minimum_radius_guarantee","none for free hose or arbitrary installed loads"],
    ["print_profile","X1C / 0.4 mm / PETG; orientation and supports not released"]
];

module crr_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module crr_basis(){u=crr_U();v=crr_V();n=crr_N();c=crr_C();multmatrix([
    [u[0],v[0],n[0],c[0]],[u[1],v[1],n[1],c[1]],
    [u[2],v[2],n[2],c[2]],[0,0,0,1]])children();}
module crr_stroke_2d(points,r){for(i=[0:len(points)-2])hull(){
    translate([points[i][0],points[i][1]])circle(r=r,$fn=crr_fn);
    translate([points[i+1][0],points[i+1][1]])circle(r=r,$fn=crr_fn);}}
module crr_sweep(points,d){for(i=[0:len(points)-2])hull(){
    translate(points[i])sphere(d=d,$fn=crr_fn);
    translate(points[i+1])sphere(d=d,$fn=crr_fn);}}
module crr_zhex(p,z,h,af){translate([p[0],p[1],z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module crr_band_2d(){union(){
    crr_stroke_2d(crr_path(),crr_band/2);
    for(p=crr_bolt_points())translate([p[0],p[1]])circle(d=11,$fn=crr_fn);
}}
module crr_groove(){
    p=crr_path();n=len(p)-1;
    entry=(p[1]-p[0])/norm(p[1]-p[0]);exit=(p[n]-p[n-1])/norm(p[n]-p[n-1]);
    // Cut completely through rounded band ends, so the housing is not capped.
    crr_sweep(concat([p[0]-12*entry],p,[p[n]+12*exit]),crr_bore);
    // Mouth relief is a tapered opening, not a claimed bend-radius constraint.
    for(e=[0,len(p)-1])let(q=e==0?1:e-1,d=(p[q]-p[e])/norm(p[q]-p[e]))hull(){
        translate(p[e]-d*10)sphere(d=8,$fn=crr_fn);
        translate(p[e]+d*5)sphere(d=crr_bore,$fn=crr_fn);
    }
}
module crr_arc_base(){crr_basis()difference(){
    translate([0,0,-crr_base_depth])linear_extrude(height=crr_base_depth)crr_band_2d();
    crr_groove();
    for(p=crr_bolt_points()){
        translate([p[0],p[1],-crr_base_depth-crr_eps])cylinder(h=12,d=3.5,$fn=crr_fn);
        crr_zhex(p,-crr_base_depth-crr_eps,3.02,5.8);
    }
}}
module crr_cap_sweep(travel=0){crr_basis()difference(){
    // Exact linear removal sweep: the planar band is solid above groove z=3.1.
    linear_extrude(height=crr_cap_depth+travel)crr_band_2d();
    crr_groove();
    for(p=crr_bolt_points())translate([p[0],p[1],-crr_eps])cylinder(h=crr_cap_depth+travel+2*crr_eps,d=3.5,$fn=crr_fn);
}}
module crr_cap(travel=0){translate(travel*crr_N())crr_cap_sweep();}
module crr_clamp_top_blank(travel=0){
    crr_box(-77,-67,-56,85,93.3,99.3+travel);
    crr_box(-49.6,-39,-56,20,93.3,99.3+travel);
    for(y=crr_mount_stations){
        crr_box(-77,-39,y-5,y+5,93.3,99.3+travel);
        crr_box(-77,-70.3,y-5,y+5,84.7,99.3+travel);
        crr_box(-45.7,-39,y-5,y+5,84.7,99.3+travel);
    }
    // Both ends bear on the actual platform edge; no friction-only Y datum.
    crr_box(-77,-67,45.3,49,84.7,99.3+travel);
    crr_box(-77,-67,-56,-52.3,84.7,99.3+travel);
}
module crr_clamp_holes(){for(x=crr_mount_x)for(y=crr_mount_stations)
    translate([x,y,70])cylinder(h=35,d=3.5,$fn=crr_fn);}
module crr_clamp_top(){difference(){crr_clamp_top_blank();crr_clamp_holes();}}
module crr_brace_node(a){crr_basis()rotate([0,0,a])crr_box(64,70,-4,4,-7,0);}
module crr_braces(travel=0){
    // Approach from the back of the guide plane, not through the removable cap.
    // Raised roots keep the diagonal webs above the existing upper feeder frame.
    for(k=[0:1])let(y=k==0?60:80,a=k==0?38:103){
        crr_box(-77,-67,y-5,y+5,93.3,145+travel);
        hull(){crr_box(-77,-67,y-5,y+5,135,145+travel);crr_brace_node(a);translate([0,0,travel])crr_brace_node(a);}
    }
}
module crr_base(){difference(){union(){crr_arc_base();crr_clamp_top();crr_braces();}crr_clamp_holes();}}
module crr_base_install_sweep(travel=60){
    // Continuous +Z withdrawal / -Z installation. Filled own bores and groove
    // deliberately make this an outer bound; the housing is not yet installed.
    p=crr_path();
    for(i=[0:len(p)-2])hull()for(k=[i,i+1])for(z=[0,travel])translate([0,0,z])crr_basis()
        translate([p[k][0],p[k][1],-7])cylinder(h=7,d=crr_band,$fn=crr_fn);
    for(b=crr_bolt_points())hull()for(z=[0,travel])translate([0,0,z])crr_basis()
        translate([b[0],b[1],-7])cylinder(h=7,d=11,$fn=crr_fn);
    crr_clamp_top_blank(travel);crr_braces(travel);
}
module crr_lower(travel=0){translate([0,0,-travel])difference(){union(){
    // U cradle stays outside the two gussets and behind the rear column.
    crr_box(-77,-67.4,-65,20,78.5,84.7);
    crr_box(-49.6,-39,-65,20,78.5,84.7);
    crr_box(-77,-39,-65,-60,78.5,84.7);
    }crr_clamp_holes();
    for(x=crr_mount_x)for(y=crr_mount_stations)crr_zhex([x,y],78.48,2.82,5.8);
}}
module crr_lower_sweep(travel=8){union(){
    crr_box(-77,-67.4,-65,20,78.5-travel,84.7);
    crr_box(-49.6,-39,-65,20,78.5-travel,84.7);
    crr_box(-77,-39,-65,-60,78.5-travel,84.7);
}}
module crr_lower_service_sweep(){
    // First drop 8 mm, then withdraw 100 mm toward -Y behind the column.
    // Long vertical removal is obstructed by the existing feeder below.
    crr_lower_sweep(8);
    crr_box(-77,-67.4,-165,20,70.5,76.7);
    crr_box(-49.6,-39,-165,20,70.5,76.7);
    crr_box(-77,-39,-165,-60,70.5,76.7);
}
module crr_tools(){
    // Shaft corridor starts 0.01 mm beyond the head; socket is modelled separately.
    for(x=crr_mount_x)for(y=crr_mount_stations)translate([x,y,102.81])cylinder(h=45,d=4,$fn=crr_fn);
    crr_basis()for(p=crr_bolt_points())translate([p[0],p[1],8.51])cylinder(h=45,d=4,$fn=crr_fn);
}
module crr_washer(p,z){translate([p[0],p[1],z])difference(){cylinder(h=.5,d=7,$fn=crr_fn);translate([0,0,-crr_eps])cylinder(h=.5+2*crr_eps,d=3.2,$fn=crr_fn);}}
module crr_bolt(p,underhead,length){translate([p[0],p[1],underhead]){
    translate([0,0,-length])cylinder(h=length,d=3,$fn=crr_fn);
    difference(){cylinder(h=3,d=5.5,$fn=crr_fn);translate([0,0,1.3])cylinder(h=1.72,d=2.5/cos(30),$fn=6);}
}}
module crr_nut(p,z){difference(){crr_zhex(p,z,2.4,5.5);translate([p[0],p[1],z-crr_eps])cylinder(h=2.4+2*crr_eps,d=3.01,$fn=crr_fn);}}
module crr_hardware(){
    for(x=crr_mount_x)for(y=crr_mount_stations){crr_washer([x,y],99.3);crr_bolt([x,y],99.8,25);crr_nut([x,y],78.9);}
    crr_basis()for(p=crr_bolt_points()){crr_washer(p,5);crr_bolt(p,5.5,16);crr_nut(p,-6.4);}
}
module crr_printed(){crr_base();crr_cap();crr_lower();}
module crr_all(){crr_printed();crr_hardware();}
module crr_host(t=0){
    ct_fixed_printed();ct_moving_printed(t);ct_original_fixed_hardware();
    la_moving_hardware(t);ci_hardware(20*t);co_hardware(t);rs_spring(t,true);
    or_pipe();ir_hose_reference();
}
module crr_contact_skins(){
    // Diagnostic only: deliberate mating planes, 0.0001 mm numerical skin.
    // Do not treat subtraction alone as a no-interference proof.
    for(z=[81.3,84.7,99.3])crr_box(-100,110,-100,110,z-.0001,z+.0001);
    crr_basis()for(z=[-4,0,5])crr_box(-100,110,-40,110,z-.0001,z+.0001);
}
module crr_pair_intersections(){union(){
    intersection(){crr_base();crr_cap();}intersection(){crr_base();crr_lower();}intersection(){crr_cap();crr_lower();}
    intersection(){crr_printed();crr_hardware();}
}}
module crr_probe(kind="host",t=0){
    if(kind=="host")intersection(){crr_all();crr_host(t);}
    else if(kind=="housing")intersection(){crr_all();cr_housing();}
    else if(kind=="parts")crr_pair_intersections();
    else if(kind=="parts-without-contact-skins")difference(){crr_pair_intersections();crr_contact_skins();}
    else if(kind=="output-tools")intersection(){crr_all();co_tools(t);}
    else if(kind=="output-screw-ray")intersection(){crr_all();co_screw_exit_ray(t,1000);}
    else if(kind=="spring-continuous")intersection(){crr_all();rs_spring_continuous_sweep();}
    else if(kind=="lower-removal")intersection(){crr_lower_service_sweep();union(){crr_base();crr_cap();crr_host(t);cr_housing();}}
    else if(kind=="cap-removal")intersection(){crr_cap_sweep(50);union(){crr_base();crr_lower();crr_host(t);cr_housing();}}
    else if(kind=="service-without-contact-skins")difference(){union(){crr_probe("cap-removal",t);crr_probe("lower-removal",t);}crr_contact_skins();}
    else if(kind=="tools")intersection(){crr_tools();union(){crr_all();crr_host(t);cr_housing();}}
    else if(kind=="base-installation")intersection(){crr_base_install_sweep();crr_host(t);}
    else if(kind=="positive-control")intersection(){crr_base();crr_base();}
    else assert(false,"Unknown retention probe");
}
module crr_show(){
    color([.25,.53,.65])crr_base();color([.4,.72,.8,.7])crr_cap();
    color([.35,.46,.56])crr_lower();color([.7,.72,.76])crr_hardware();
    color([.8,.55,.2,.4])co_fixed_bridge();color([.13,.15,.18])cr_housing();
}
if(crr_part=="assembly")crr_show();
else if(crr_part=="base")crr_base();
else if(crr_part=="cap")crr_cap();
else if(crr_part=="lower")crr_lower();
else if(crr_part=="hardware")crr_hardware();
else if(crr_part=="contract")echo("CRR_CONTRACT",crr_contract());
else if(crr_part=="probe")crr_probe(crr_test,crr_t);
else assert(false,"Unknown route retention part");
