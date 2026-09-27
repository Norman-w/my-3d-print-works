include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-scene-export.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
module rs_current_rigid(){
  // feeder/positive-half
  la_item("positive-half",1,false,0);
  // feeder/negative-half
  la_item("negative-half",1,false,0);
  // feeder/beam-grip
  cse_item("beam",0);
  // feeder/liner
  la_item("liner",1,false,0);
  // feeder/right-support
  la_item("right-support",1,false,0);
  // feeder/left-support
  la_item("left-support",1,false,0);
  // feeder/x-gib
  la_item("x-gib",1,false,0);
  // feeder/x-cover
  la_item("x-cover",1,false,0);
  // feeder/frame
  cse_item("frame",0);
  // feeder/fixed-spacer
  la_item("fixed-spacer",1,false,0);
  // feeder/moving-spacer
  la_item("moving-spacer",1,false,0);
  // feeder/capture-right
  la_item("capture",1,false,0);
  // feeder/pipe-clamp-right
  la_item("pipe-clamp",1,false,0);
  // feeder/y-cap-right
  la_item("y-cap",1,false,0);
  // feeder/frame-y-gib-right
  la_item("frame-y-gib",1,false,0);
  // feeder/y-gib-right-front
  la_item("y-gib",1,false,0);
  // feeder/y-keeper-right-front
  la_item("y-keeper",1,false,0);
  // feeder/finger-right-front
  la_item("finger",1,false,0);
  // feeder/pin-block-right-front
  la_item("pin-block",1,false,0);
  // feeder/y-gib-right-rear
  la_item("y-gib",1,true,0);
  // feeder/y-keeper-right-rear
  la_item("y-keeper",1,true,0);
  // feeder/finger-right-rear
  la_item("finger",1,true,0);
  // feeder/pin-block-right-rear
  la_item("pin-block",1,true,0);
  // feeder/capture-left
  la_item("capture",-1,false,0);
  // feeder/pipe-clamp-left
  la_item("pipe-clamp",-1,false,0);
  // feeder/y-cap-left
  la_item("y-cap",-1,false,0);
  // feeder/frame-y-gib-left
  la_item("frame-y-gib",-1,false,0);
  // feeder/y-gib-left-front
  la_item("y-gib",-1,false,0);
  // feeder/y-keeper-left-front
  la_item("y-keeper",-1,false,0);
  // feeder/finger-left-front
  la_item("finger",-1,false,0);
  // feeder/pin-block-left-front
  la_item("pin-block",-1,false,0);
  // feeder/y-gib-left-rear
  la_item("y-gib",-1,true,0);
  // feeder/y-keeper-left-rear
  la_item("y-keeper",-1,true,0);
  // feeder/finger-left-rear
  la_item("finger",-1,true,0);
  // feeder/pin-block-left-rear
  la_item("pin-block",-1,true,0);
  // feeder/inlet-rear
  la_item("inlet-rear",1,false,0);
  // feeder/inlet-front
  la_item("inlet-front",1,false,0);
  // feeder/inlet-backplate
  la_item("inlet-backplate",1,false,0);
  // feeder/cable-input-body
  cse_item("input-body",0);
  // feeder/cable-input-lever
  cse_item("input-lever",0);
  // feeder/cable-input-terminal-cap
  cse_item("input-terminal-cap",0);
  // feeder/cable-input-cover
  cse_item("input-cover",0);
  // feeder/cable-output-cap
  cse_item("output-cap",0);
  // feeder/hardware-fixed
  cse_item("original-fixed-hardware",0);
  // feeder/hardware-right-front
  cse_follower_hardware(1,false,0);
  // feeder/hardware-right-rear
  cse_follower_hardware(1,true,0);
  // feeder/hardware-left-front
  cse_follower_hardware(-1,false,0);
  // feeder/hardware-left-rear
  cse_follower_hardware(-1,true,0);
  // feeder/hardware-moving-spacer
  cse_item("spring-moving-hardware",0);
  // feeder/cable-input-hardware-fixed
  cse_item("input-fixed-hardware",0);
  // feeder/cable-input-hardware-moving
  cse_item("input-moving-hardware",0);
  // feeder/cable-output-hardware-fixed
  cse_item("output-fixed-hardware",0);
  // feeder/cable-output-hardware-moving
  cse_item("output-moving-hardware",0);
  // feeder/pc-reference
  la_item("pc-reference",1,false,0);
  // feeder/hose-reference
  la_item("hose-reference",1,false,0);
  // feeder/liner-reference
  la_item("liner-reference",1,false,0);
  // feeder/spring-reference
  cse_item("spring-reference",0);
}
module rs_nominal_flexible(){
  // feeder/cable-housing
  cse_item("route-housing",0);
  // feeder/cable-core-route
  cse_item("route-wire",0);
  // feeder/cable-core-input
  cse_item("input-wire",0);
  // feeder/cable-core-output
  cse_item("output-wire",0);
}
module rs_original_feeder_only(){la_fixed();la_moving(0);rs_spring(0,true);la_item("liner-reference");}
