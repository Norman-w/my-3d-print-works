use <candidate.scad>
use <route/candidate.scad>
use <../../cad/cable-trigger-input.scad>
$fn=72;
part="axis";
module candidate_route(){cr_housing();cr_wire();}
if(part=="axis")intersection(){ci_to_cad()offset_axis_sweep();candidate_route();}
else if(part=="body")intersection(){ci_to_cad()offset_body();candidate_route();}
else if(part=="cover")intersection(){ci_to_cad()offset_cover();candidate_route();}
