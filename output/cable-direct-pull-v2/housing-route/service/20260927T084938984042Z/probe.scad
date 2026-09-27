use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/housing-route/equal-length-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-service-review.scad>
delta=0;kind="input-mount-tools";fault=false;
module updated_service(){
 if(kind=="input-stop-tools")for(setting=[16,20,22]){
  sx=cdp_stop_tip(setting);
  cdp_to_cad(){
   cdp_xcyl(-24,2,-100,sx-33+100,4);
   translate([sx-33,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=1.5,d=2.5/cos(30),$fn=6);
  }
 }else csr_service_envelope(kind);
}
intersection(){cv_envelope(delta,1,false);union(){updated_service();
 if(fault)translate(cv_points(delta)[40])sphere(d=10,$fn=24);
}}
