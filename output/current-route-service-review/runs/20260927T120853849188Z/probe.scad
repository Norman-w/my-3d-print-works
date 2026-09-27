include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-route-service-review/runs/20260927T120853849188Z/scene-obstacles.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>

kind="cap-current";
function rs_get(k)=crr_contract()[search([k],crr_contract())[0]][1];
module rs_mount_hardware(){for(p=rs_get("clamp_bolt_centres")){
    crr_washer(p,99.3);crr_bolt(p,99.8,25);crr_nut(p,78.9);
}}
module rs_cap_nuts(){crr_basis()for(p=crr_bolt_points())crr_nut(p,-6.4);}
module rs_fixed_retainer(){crr_base();rs_cap_nuts();
    if(kind=="cap-current"){crr_lower();rs_mount_hardware();}
}
module rs_external(){
    if(kind=="lower-baseline")rs_original_feeder_only();
    else rs_current_rigid();
    if(kind=="cap-current")rs_nominal_flexible();
}
if(kind=="contract")echo("RS_CONTRACT",crr_contract(),"N",crr_N(),"C",crr_C());
else intersection(){
    if(kind=="cap-current")crr_cap_sweep(50);
    else if(kind=="lower-wrong-straight-down")crr_lower_sweep(70);
    else crr_lower_service_sweep();
    union(){rs_fixed_retainer();rs_external();}
}
