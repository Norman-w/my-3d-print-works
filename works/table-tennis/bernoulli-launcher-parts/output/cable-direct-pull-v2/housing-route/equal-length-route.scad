// Independent route FAMILY, not an assertion of the shape an unsupported cable takes.
// The first virtual corner slides; second/third corners and guided third arc stay fixed.
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
cv_part="none";
cv_delta=0;
cv_R=75;
cv_step=2;
cv_limit=2;
function cv_vertices(delta,s)=let(v=cr_vertices(),d=cr_input_direction())
 [v[0]-delta*d,v[1]+s*d,v[2],v[3],v[4]];
function cv_arc(i,delta,s)=i==3?cr_arc(3):let(v=cv_vertices(delta,s),
 a=cr_unit(v[i]-v[i-1]),b=cr_unit(v[i+1]-v[i]),
 c=max(-1,min(1,cr_dot(a,b))),theta=acos(c),
 trim=cv_R*tan(theta/2),normal=cr_unit(b-a*c),
 A=v[i]-a*trim,B=v[i]+b*trim,C=A+normal*cv_R)
 [A,B,C,-normal,a,theta,trim];
function cv_lines(delta,s)=let(v=cv_vertices(delta,s))[
 for(i=[0:3])let(A=i==0?v[0]:cv_arc(i,delta,s)[1],
 B=i==3?v[4]:cv_arc(i+1,delta,s)[0])
 [A,B,norm(B-A),cr_dot(B-A,cr_unit(v[i+1]-v[i]))]];
function cv_length(delta,s)=cr_sum([for(l=cv_lines(delta,s))l[2]])+
 cr_sum([for(i=[1:3])cv_R*cv_arc(i,delta,s)[5]*PI/180]);
function cv_shift(delta,lo=-12,hi=12,n=0)=n>=45?(lo+hi)/2:
 let(m=(lo+hi)/2)cv_length(delta,m)<cr_length()?
 cv_shift(delta,m,hi,n+1):cv_shift(delta,lo,m,n+1);
function cv_arc_point(i,t,delta,s)=let(a=cv_arc(i,delta,s),angle=a[5]*t)
 a[2]+cv_R*(a[3]*cos(angle)+a[4]*sin(angle));
function cv_points(delta,trim_ports=false)=let(s=cv_shift(delta),v=cv_vertices(delta,s))concat(
 [v[0]+(trim_ports?15:0)*cr_input_direction()],
 [for(i=[1:3])each[for(k=[0:ceil(cv_arc(i,delta,s)[5]/cv_step)])
 cv_arc_point(i,k/ceil(cv_arc(i,delta,s)[5]/cv_step),delta,s)]],
 [v[4]+[0,0,trim_ports?15:0]]);
module cv_require(delta){
 assert(abs(delta)<=cv_limit,"Diagnostic input setting exceeds +/-2 mm");
 assert(cv_R==cr_get(cr_contract(),"arc_radius"));
 assert(cv_length(delta,-12)<cr_length()&&cv_length(delta,12)>cr_length(),"No bracketed route-length root");
 assert(abs(cv_length(delta,cv_shift(delta))-cr_length())<.000001);
 for(l=cv_lines(delta,cv_shift(delta)))assert(l[3]>0,"Tangent fillets overlap");
 children();
}
module cv_housing(delta=cv_delta){cv_require(delta)cr_sweep(cv_points(delta),5);}
module cv_envelope(delta=cv_delta,extra=1,trim_ports=true){
 cv_require(delta)cr_sweep(cv_points(delta,trim_ports),
 (5+2*(extra+cv_R*(1-cos(cv_step/2))))/pow(cos(180/24),2));
}
module cv_contract(){echo(cv_contract=[
 ["status","ADMISSIBLE_GEOMETRIC_FAMILY_ONLY"],["delta",cv_delta],
 ["corner_shift",cv_shift(cv_delta)],["length",cv_length(cv_delta,cv_shift(cv_delta))],
 ["original_length",cr_length()],["vertices",cv_vertices(cv_delta,cv_shift(cv_delta))],
 ["lines",cv_lines(cv_delta,cv_shift(cv_delta))],
 ["arcs",[for(i=[1:3])cv_arc(i,cv_delta,cv_shift(cv_delta))]],
 ["third_arc_exactly_original",cv_arc(3,cv_delta,cv_shift(cv_delta))==cr_arc(3)],
 ["radius",cv_R],["physical_shape_retained",false]]);}
if(cv_part=="contract")cv_contract();
else if(cv_part=="housing")cv_housing();
else if(cv_part=="envelope")cv_envelope();
else if(cv_part!="none")assert(false,"Unknown route family selector");
