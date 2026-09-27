// Service access REVIEW, not printable geometry. Coordinates: feeder CAD, mm.
// A fixed nominal sheath can be an obstacle only for actions performed before
// disconnecting it. Module removal / bench cover service are separate phases.
use <cable-housing-route.scad>
use <cable-service-contract.scad>
use <cable-trigger-input.scad>
use <cable-output-interface.scad>
use <feeder-support-harness.scad>
use <feeder-return-spring.scad>
use <feeder-pin-seat-revision.scad>
yg_library_mode=true;
include <feeder-frame-y-guide.scad>
use <feeder-complete-hardware.scad>
use <outlet-retention.scad>
use <inlet-retention-review.scad>

csr_part="probe";
csr_kind="input-mount-tools";
csr_fault=false;

function csr_kinds()=["input-mount-tools","input-mount-bolts","input-stop-tools","input-stop-locknut",
    "output-tools","output-cap-bolts","output-cap-removal","output-washer-removal",
    "output-terminal-removal","spring-tools","follower-tools",
    "guide-tools","outlet-tools","inlet-tools","seam-tools","original-tools"];

// Disconnected input-module phase. Kept separate from csr_kinds(), because
// those original kinds are evaluated against a fixed installed sheath.
function csr_bench_kinds()=["terminal-tools","terminal-bolts","terminal-cap","terminal-ball","main-cover"];
module csr_bench_envelope(kind=csr_kind){
 if(kind=="terminal-tools")cs_input_terminal_tools();
 else if(kind=="terminal-bolts")cs_input_terminal_bolt_sweep();
 else if(kind=="terminal-cap")cs_input_terminal_cap_sweep();
 else if(kind=="terminal-ball")cs_input_terminal_ball_sweep();
 else if(kind=="main-cover")cs_input_bench_cover_sweep();
 else assert(false,str("Unknown bench service envelope: ",kind));
}
module csr_bench_obstacle(kind=csr_kind){
 ci_body();ci_lever(0);
 if(kind=="main-cover"){
  ci_terminal_cap(0);ci_moving_hardware(0);
 }else{
  if(kind=="terminal-tools"){
   ci_fixed_hardware();ci_moving_hardware(0);ci_terminal_cap(0);
  }else{
   cs_input_terminal_remaining_metal(kind=="terminal-ball");
   if(kind=="terminal-bolts")ci_terminal_cap(0);
  }
  // Real wrong-stage positive controls: leaving the main cover installed
  // blocks the tool/bolt/cap path; leaving the terminal cap traps the ball.
  if(csr_fault){
   if(kind=="terminal-ball")ci_terminal_cap(0);
   else ci_cover();
  }
 }
}
module csr_bench_probe(){intersection(){csr_bench_envelope();csr_bench_obstacle();}}

// Full nominal route plus 1 mm clearance, with conservative mesh/chord cover.
// End fittings are not part of this obstacle. They need their own mating tests.
module csr_route_envelope(){cr_require_valid()cr_sweep(cr_points(),
    (cr_get(ci_spec(),"housing_od")+2*(1+cr_sagitta()))/pow(cos(180/24),2));}

// Conservative continuous Z translation. Applying it to a union preserves
// concavities, unlike a hull around disconnected objects. Static members may
// be swept unnecessarily; if positive, diagnose before calling it a collision.
module csr_z_sweep(travel=20){minkowski(){children();
    translate([-.001,-.001,0])cube([.002,.002,travel]);}}

module csr_service_envelope(kind=csr_kind){
    if(kind=="input-mount-tools")cs_input_mount_tools();
    else if(kind=="input-mount-bolts")cs_input_mount_bolt_sweep();
    else if(kind=="input-stop-tools")for(setting=[16,20,22])cs_input_stop_tools(setting);
    else if(kind=="input-stop-locknut")cs_input_stop_locknut_tool();
    else if(kind=="output-tools")csr_z_sweep()co_tools(0);
    else if(kind=="output-cap-bolts")csr_z_sweep()cs_output_cap_bolt_sweep(0);
    else if(kind=="output-cap-removal")csr_z_sweep()cs_output_cap_sweep(0);
    else if(kind=="output-washer-removal")csr_z_sweep()cs_output_washer_sweep(0);
    else if(kind=="output-terminal-removal")csr_z_sweep()cs_output_nipple_sweep(0);
    else if(kind=="spring-tools")csr_z_sweep()rs_tools(0);
    // Follower radial motion is nonlinear; the source helper supplies the
    // endpoints at each pose. These remain explicitly sampled, not continuous.
    else if(kind=="follower-tools")for(i=[0:20])ps_tools(i/20);
    else if(kind=="guide-tools")for(side=[-1,1])yg_at(side){
        for(z=yg_jack_z)yg_local_tools(z,true);
        for(z=support_cap_screw_z)yg_local_tools(z,false);
    }
    else if(kind=="outlet-tools")or_tools();
    else if(kind=="inlet-tools"){
        ir_clamp_drivers();ir_anchor_drivers();ir_front_spanners();}
    else if(kind=="seam-tools")fh_seam_tools();
    else if(kind=="original-tools")sh_existing_tools();
    else assert(false,str("Unknown service envelope: ",kind));
}

module csr_probe(){intersection(){csr_route_envelope();union(){
    csr_service_envelope();
    if(csr_fault)translate(cr_points()[floor(len(cr_points())/2)])sphere(d=10,$fn=24);
}}}
if(csr_part=="probe")csr_probe();
else if(csr_part=="bench-probe")csr_bench_probe();
else if(csr_part=="bench-envelope")csr_bench_envelope();
else if(csr_part=="bench-assembly"){
 color([.3,.5,.6,.5])csr_bench_obstacle();
 color([1,.5,.1,.6])csr_bench_envelope();
}
else if(csr_part=="envelope")csr_service_envelope();
else if(csr_part=="assembly"){
    color([.1,.15,.2])cr_housing();
    color([1,.4,.1,.65])csr_service_envelope();
}
else if(csr_part=="contract")echo("CSR_CONTRACT",[
    ["units","mm"],["kinds",csr_kinds()],["bench_kinds",csr_bench_kinds()],["bench_scope","separate disconnected input module at u0; not against fixed installed housing"],
    ["route_clearance",1],["full_route_including_ports",true],
    ["scope","fixed nominal sheath versus named service envelopes only"],
    ["excluded_phase","input module and cover movement after cable disconnection"],
    ["service_contract",cs_contract_data()],
    ["physical_route_retained",false],["physical_acceptance",false]]);
else assert(false,"Unknown service review part");
