// Mass geometry only: isolated hex-bush candidate, in input local coordinates.
use <../../current-axis-retention-review/candidate.scad>
use <../../../cad/cable-trigger-input.scad>
$fn=72;
part="lever";
if(part=="lever")ar_lever(0);
else if(part=="cap")ci_local_terminal_cap();
else if(part=="bush")ar_bush(0);
else if(part=="metal")ar_other_moving_hardware(0);
else assert(false,"Unknown moving mass part");
