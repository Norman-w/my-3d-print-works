// Complete local feeder/cable review scene, including the removable bend guide.
// Separate parent entry avoids making a component depend recursively on host.
// NOT a print plate, manufacturing release, or the unmeasured full blower rig.
use <cable-trigger-system.scad>
use <cable-route-retention.scad>
ccr_t=0;
ccr_guide=true;
assert(ccr_t>=0 && ccr_t<=1);
ct_show(ccr_t);
if(ccr_guide){
    color([.18,.49,.60])crr_base();
    color([.40,.70,.77,.45])crr_cap();
    color([.27,.39,.47])crr_lower();
    color([.7,.72,.76])crr_hardware();
}
