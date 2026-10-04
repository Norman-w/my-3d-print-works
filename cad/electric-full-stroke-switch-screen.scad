// Candidate full-stroke switch mirrored from the independent home-switch
// envelope around Z=-15 (midpoint of the existing upper/lower fixed stops).
// Only a packaging screen; the adjustable mount and wiring are not designed.
use <electric-home-switch-screen.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>

fs_part = "probe"; // probe, context, switch, tab
fs_probe = "switch-fixed";
fs_t = 1; // 1 = feeder fully extended to 20 mm hard stop

assert(fs_t>=0 && fs_t<=1);

module fs_reflect(){translate([0,0,-30]) scale([1,1,-1]) children();}
module fs_switch(){fs_reflect() hs_non_actuating_envelope();}
module fs_case(){fs_reflect() hs_case();}
module fs_terminals(){fs_reflect() hs_solder_clearance();}
module fs_plunger(){fs_reflect() hs_plunger_free_bound();}
module fs_tab(t=fs_t){
    // At t=1 this roots into the lower moving shoulder, Z=-39..-35.
    // At t=0 it is 20 mm below that position.
    translate([0,0,20*(t-1)]) fs_reflect() hs_tab(0);
}
module fs_hardware(t=fs_t){
    hs_selected_hardware(t);
}
module fs_probe_geometry(){
    if(fs_probe=="switch-fixed")
        intersection(){fs_switch();it_fixed_printed();}
    else if(fs_probe=="switch-moving")
        intersection(){fs_switch();it_moving_printed(fs_t,0);}
    else if(fs_probe=="switch-hardware")
        intersection(){fs_switch();fs_hardware(fs_t);}
    else if(fs_probe=="tab-fixed")
        intersection(){fs_tab(fs_t);it_fixed_printed();}
    else if(fs_probe=="tab-hardware")
        intersection(){fs_tab(fs_t);fs_hardware(fs_t);}
    else if(fs_probe=="full-contact")
        intersection(){fs_tab(fs_t);fs_reflect() hs_nominal_operating_marker();}
    else if(fs_probe=="one-mm-before-free-clearance")
        intersection(){fs_tab(fs_t);fs_plunger();}
    else if(fs_probe=="tab-root-control")
        intersection(){fs_tab(fs_t);it_moving_printed(fs_t,0);}
    else if(fs_probe=="home-switch-separation")
        intersection(){fs_switch();hs_non_actuating_envelope();}
    else assert(false,"Unknown full-stroke-switch probe");
}

if(fs_part=="probe") fs_probe_geometry();
else if(fs_part=="switch") fs_switch();
else if(fs_part=="tab") fs_tab();
else if(fs_part=="context") {
    color([.70,.74,.77,.55]) it_assembly(fs_t,0);
    color([.13,.13,.14]) fs_case();
    color([.72,.72,.74]) fs_terminals();
    color([.85,.18,.12]) fs_plunger();
    color([.98,.75,.12]) fs_tab(fs_t);
    color([.10,.15,.20]) hs_case(); // other endpoint for spacing reference
}
else assert(false,"Unknown full-stroke-switch screen part");
