use <candidate.scad>
use <../current-axis-retention-review/candidate.scad>
$fn=72;
module section_cut(){render()intersection(){children();translate([-17,-.001,-28])cube([34,27,55]);}}
color([.13,.48,.72])section_cut()offset_plastics();
color([.94,.57,.15])section_cut()ar_lever(0);
color([.90,.93,.94])section_cut()ar_bush(0);
color([.78,.8,.83])section_cut()offset_axis();
color([.95,.85,.35])section_cut()ar_thrust();
