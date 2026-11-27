// Combined isolated shoulder + form-retained POM bush candidate.
// This is not the published scene or a print plate.
use <candidate.scad>
use <../current-axis-through-candidate/candidate.scad>
use <../current-axis-retention-review/candidate.scad>
use <../../cad/cable-trigger-input.scad>
$fn=72;
part="section";
input_u=0;
module combined(){
 color([.13,.48,.72])shoulder_plastics();
 ar_rotor(input_u);
 color([.73,.76,.80]){shoulder_axis();other_fixed_metal();ci_from_cad()ci_mount_hardware_cad();}
}
if(part=="axis-rotor-probe")intersection(){shoulder_sweep();ar_rotor(input_u);}
else if(part=="rotor-plastic-probe")intersection(){shoulder_plastics();ar_rotor(input_u);}
else if(part=="bush-solid-control")intersection(){ar_bush();ar_bush();}
else if(part=="section")clip()combined();
else if(part=="assembly")combined();
