// Purchased flexible housing, NOT a printable part.
// Source-derived port datums; the route is a nominal installation proposal.
// Datum-to-datum length excludes the unconfirmed end-seating corrections.
use <input-offset.scad>
use <../../../cad/cable-output-interface.scad>
cr_part="assembly";
cr_R=75;
cr_input_run=100;
cr_side_run=198;
cr_apex_z=400;
cr_step_deg=2;
cr_port_exclusion=15;
cr_ci=ci_spec();

function cr_get(s,k)=s[search([k],s)[0]][1];
function cr_unit(v)=v/norm(v);
function cr_dot(a,b)=a*b;
function cr_input_port(delta=ci_install_delta())=ci_local_to_cad([
    cr_get(cr_ci,"adjuster_overall_x")[0]-ci_install_delta()+delta,
    cr_get(cr_ci,"adjuster_seat_local")[1],
    cr_get(cr_ci,"wire_z")]);
function cr_input_direction()=-cr_get(cr_ci,"basis_x");
function cr_output_port()=co_housing_entry();
function cr_base_vertices()=let(p=cr_input_port(0),q=cr_output_port(),
    a=p+cr_input_run*cr_input_direction(),b=a+[0,cr_side_run,0])
    [p,a,b,[q[0],q[1],cr_apex_z],q];
// Installation family: first two free bends move to preserve length. The
// second/third virtual corners and output stay fixed, preserving the guided arc.
function cr_candidate_vertices(delta,s)=let(v=cr_base_vertices(),d=cr_input_direction())
    [v[0]-delta*d,v[1]+s*d,v[2],v[3],v[4]];
// Arc contract: A/B tangency points, centre, radial/tangent bases,
// angle in degrees, trim length. Every arc has the SAME exact radius.
function cr_arc_from_vertices(i,p)=let(
    a=cr_unit(p[i]-p[i-1]),b=cr_unit(p[i+1]-p[i]),
    c=max(-1,min(1,cr_dot(a,b))),theta=acos(c),
    trim=cr_R*tan(theta/2),normal=cr_unit(b-a*c),
    A=p[i]-a*trim,B=p[i]+b*trim,C=A+normal*cr_R)
    [A,B,C,-normal,a,theta,trim];
function cr_candidate_arc(i,delta,s)=cr_arc_from_vertices(i,
    i==3?cr_base_vertices():cr_candidate_vertices(delta,s));
function cr_candidate_lines(delta,s)=let(v=cr_candidate_vertices(delta,s))[
    for(i=[0:3])let(A=i==0?v[0]:cr_candidate_arc(i,delta,s)[1],
        B=i==3?v[4]:cr_candidate_arc(i+1,delta,s)[0])
        [A,B,norm(B-A),cr_dot(B-A,cr_unit(v[i+1]-v[i]))]];
function cr_candidate_length(delta,s)=
    cr_sum([for(l=cr_candidate_lines(delta,s))l[2]])+
    cr_sum([for(i=[1:3])cr_R*cr_candidate_arc(i,delta,s)[5]*PI/180]);
function cr_base_length()=cr_candidate_length(0,0);
function cr_solve_shift(delta,lo=-2,hi=2,n=0)=n>=45?(lo+hi)/2:
    let(m=(lo+hi)/2)cr_candidate_length(delta,m)<cr_base_length()?
    cr_solve_shift(delta,m,hi,n+1):cr_solve_shift(delta,lo,m,n+1);
function cr_corner_shift(delta=ci_install_delta())=delta==0?0:cr_solve_shift(delta);
function cr_vertices(delta=ci_install_delta())=
    cr_candidate_vertices(delta,cr_corner_shift(delta));
function cr_arc(i,delta=ci_install_delta())=cr_candidate_arc(i,delta,cr_corner_shift(delta));
function cr_arc_point(i,t)=let(a=cr_arc(i),angle=a[5]*t)
    a[2]+cr_R*(a[3]*cos(angle)+a[4]*sin(angle));
function cr_lines()=let(v=cr_vertices(),n=len(v))[
    for(i=[0:n-2])let(A=i==0?v[0]:cr_arc(i)[1],
        B=i==n-2?v[n-1]:cr_arc(i+1)[0])[A,B,norm(B-A),
        cr_dot(B-A,cr_unit(v[i+1]-v[i]))]];
function cr_points(trim_ports=false)=let(v=cr_vertices(),n=len(v))concat(
    [v[0]+(trim_ports?cr_port_exclusion:0)*cr_input_direction()],
    [for(i=[1:n-2])each [for(k=[0:ceil(cr_arc(i)[5]/cr_step_deg)])
        cr_arc_point(i,k/ceil(cr_arc(i)[5]/cr_step_deg))]],
    [v[n-1]+[0,0,trim_ports?cr_port_exclusion:0]]);
function cr_length()=let(v=cr_vertices())
    cr_sum([for(l=cr_lines())l[2]])+
    cr_sum([for(i=[1:len(v)-2])cr_R*cr_arc(i)[5]*PI/180]);
function cr_sum(v,i=0)=i>=len(v)?0:v[i]+cr_sum(v,i+1);
function cr_sagitta()=cr_R*(1-cos(cr_step_deg/2));
function cr_contract()=[
    ["units","mm"],["role","purchased-flexible-reference"],
    ["status","equal-length-installation-family-not-release"],
    ["route_law","fixed-third-arc-equal-length-v1"],
    ["adjuster_delta",ci_install_delta()],["adjuster_delta_range",[-2,2]],
    ["first_corner_shift",cr_corner_shift()],["nominal_outside_port_length",cr_base_length()],
    ["input_port",cr_input_port()],["output_port",cr_output_port()],
    ["input_outward_tangent",cr_input_direction()],
    ["output_arrival_tangent",[0,0,-1]],
    ["housing_od",cr_get(ci_spec(),"housing_od")],
    ["wire_d",cr_get(ci_spec(),"wire_d")],
    ["minimum_supplier_radius",65],["arc_radius",cr_R],
    ["virtual_vertices",cr_vertices()],["lines",cr_lines()],
    ["arcs",[for(i=[1:len(cr_vertices())-2])cr_arc(i)]],
    ["sample_points",cr_points()],["maximum_chord_error",cr_sagitta()],
    ["outside_port_route_length",cr_length()],
    ["port_clearance_test_exclusion",cr_port_exclusion],
    ["manufactured_housing_cut_length",undef],
    ["cut_length_reason","actual seating and installed layout corrections are unresolved"],
    ["purchased_kit_candidate","03096-14-1000; vendor permits shortening"],
    ["core_trim_order","leave core long until both sheath ends and actuator travel are set"],
    ["external_obstacles_verified",false],
    ["physical_route_retained",false],
    ["retention_reason","end ferrules and third bend have modeled retainers; first two bends remain free"],
    ["adjustment_setup","disconnect and park housing for bench adjuster service; reseat and reroute before resetting core zero"],
    ["family_scope","equal-length geometric family; not an equilibrium or physical shape-retention model"]
];

module cr_sweep(points,d){
    // Circumscribed facets plus chord sagitta are added only by the clearance
    // probe. The display is the nominal OD and is not itself a tolerance proof.
    for(i=[0:len(points)-2])hull(){
        translate(points[i])sphere(d=d,$fn=24);
        translate(points[i+1])sphere(d=d,$fn=24);
    }
}
module cr_require_valid(){
    assert(cr_get(cr_ci,"origin")==[75,-85,5],"Offset route requires its reviewed input origin");
    assert(cr_R>=65,"Below selected housing supplier minimum bend radius");
    assert(abs(ci_install_delta())<=2,"Housing route setting outside +/-2 mm");
    // The proved family uses these fixed nominal dimensions. A redesign must
    // establish its own bracket and clearances rather than silently reusing it.
    assert(cr_R==75&&cr_input_run==100&&cr_side_run==198&&cr_apex_z==400,
        "Equal-length installation family needs its reviewed nominal route parameters");
    assert(cr_candidate_length(ci_install_delta(),-2)<cr_base_length()&&
           cr_candidate_length(ci_install_delta(),2)>cr_base_length(),"Route root not bracketed");
    assert(abs(cr_length()-cr_base_length())<.000001,"Route length changed with setting");
    for(l=cr_lines())assert(l[3]>0,"Route fillets overlap on a straight segment");
    assert(cr_lines()[0][2]>cr_port_exclusion);
    assert(cr_lines()[len(cr_lines())-1][2]>cr_port_exclusion);
    children();
}
module cr_housing(){cr_require_valid()cr_sweep(cr_points(),cr_get(ci_spec(),"housing_od"));}
module cr_wire(){
    cr_require_valid(){
    cr_sweep(cr_points(),cr_get(ci_spec(),"wire_d"));
    cr_sweep([cr_input_port(),ci_local_to_cad(cr_get(ci_spec(),"adjuster_exit_local"))],
        cr_get(ci_spec(),"wire_d"));
    }
}
module cr_clearance(extra=1){
    // A capsule containing the true circle arc, plus 1 mm route clearance.
    // Sphere faceting is covered conservatively in both angular directions.
    cr_require_valid()cr_sweep(cr_points(true),
        (cr_get(ci_spec(),"housing_od")+2*(extra+cr_sagitta()))/pow(cos(180/24),2));
}
if(cr_part=="contract")echo("CR_CONTRACT",cr_contract());
else if(cr_part=="housing")cr_housing();
else if(cr_part=="wire")cr_wire();
else if(cr_part=="clearance")cr_clearance();
else if(cr_part=="assembly"){color([.14,.17,.20,.8])cr_housing();color([.7,.72,.76])cr_wire();}
else assert(false,"Unknown cable housing route part");
