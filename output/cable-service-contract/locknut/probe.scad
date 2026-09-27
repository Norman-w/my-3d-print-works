use <../../../cad/cable-trigger-input.scad>
use <../../../cad/cable-service-contract.scad>
u=0;
control=false;
intersection(){
 cs_input_stop_locknut_tool();
 union(){ci_body();ci_cover();ci_lever(u);ci_fixed_hardware();ci_moving_hardware(u);
 if(control)ci_to_cad()translate([-27.5,-32,2])sphere(d=5,$fn=24);}
}
