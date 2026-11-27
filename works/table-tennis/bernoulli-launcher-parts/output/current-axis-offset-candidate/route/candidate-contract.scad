use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/route/input-offset.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-axis-offset-candidate/route/candidate.scad>
function oq(v)=is_num(v)?let(i=floor(v),f=(v-i)*1e6,j=floor(f))["__q9",i,j,round((f-j)*1000)]:is_list(v)?[for(x=v)oq(x)]:v;
function oc_fast(s)=let(d=ci_install_delta(),v=cr_candidate_vertices(d,s),ln=cr_candidate_lines(d,s))[
 ["virtual_vertices",v],["arcs",[for(i=[1:3])cr_candidate_arc(i,d,s)]],
 ["lines",ln],["outside_port_route_length",cr_candidate_length(d,s)],
 ["first_corner_shift",s],["input_port",cr_input_port()],
 ["output_port",cr_output_port()],["input_outward_tangent",cr_input_direction()]
];
cr_require_valid(){
 echo("CONTRACT_Q9",oq(ci_install_delta()==0?cr_contract():oc_fast(cr_corner_shift())));
 echo("CI_Q9",oq(ci_spec()));
 echo("CI_MOTION_Q9",oq([for(u=[0,10,20,22])[u,ci_angle(u),ci_phi(ci_angle(u)),ci_path_length(ci_angle(u)),ci_effective_arm(u)]]));
}
