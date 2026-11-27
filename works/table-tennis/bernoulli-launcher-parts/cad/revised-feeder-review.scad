// Combined REVIEW entrance for independent seam and gib candidates.
// No adoption, print-package, tolerance or physical acceptance is implied.
include <parameters.scad>
use <feeder-seam-candidate.scad>
use <feeder-guide-revision.scad>

revised_mode="review"; // review, section, probe
revised_stroke=0.5;
revised_gib_setting=0.9;
revised_body_fault=0; // Deliberate +X body/pin translation for positive control.

module revised_body(section=false) {
    translate([revised_body_fault,0,0]) {
        seam_candidate_half(true);
        if(!section) seam_candidate_half(false);
    }
}

module revised_locator_pins() {
    translate([revised_body_fault,0,0]) seam_pins();
}

module revised_existing_hardware() {
    feeder_cap_hardware();
    feeder_mount_hardware();
    for(side=[-1,1],g=[0,-gate_spacing])
        scale([side,1,1]) revision_hardware_local(g,revised_gib_setting);
}

module revised_other_components(t=revised_stroke) {
    revision_fixed();
    revision_gibs(revised_gib_setting);
    revised_existing_hardware();
    feeder_carriage(t);
    revision_followers(t);
}

module revised_display(section=false) {
    color([0.64,0.72,0.77]) revised_body(section);
    color([0.88,0.63,0.18]) revised_locator_pins();
    color([0.78,0.78,0.81]) revision_fixed();
    color([0.97,0.63,0.12]) revision_gibs(revised_gib_setting);
    color([0.12,0.43,0.78]) feeder_carriage(revised_stroke);
    color([0.15,0.65,0.39]) revision_followers(revised_stroke);
    color([0.30,0.31,0.34]) revised_existing_hardware();
}

echo("REVIEW ONLY: independent seam + gib candidates; not adopted or print released");
echo("Excluded solids: eight seam M3 sets, body-mount captive nuts, spring, hose/Y joints");
if(revised_mode=="review") revised_display();
else if(revised_mode=="section") revised_display(true);
else if(revised_mode=="probe") intersection() {
    union() { revised_body(); revised_locator_pins(); }
    revised_other_components();
}
else assert(false,"Unknown revised feeder review mode");
