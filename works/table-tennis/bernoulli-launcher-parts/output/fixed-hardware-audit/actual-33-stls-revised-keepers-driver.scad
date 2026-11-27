include <../../cad/parameters.scad>
use <../../cad/feeder-hardware-clearance.scad>
use <../../cad/feeder-guide-revision.scad>
use <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
use <../../cad/feeder-complete-hardware.scad>
use <../../cad/review-launcher-baseline33.scad>
module audit_shafts(){
 for(y=[-40,40],z=[-72,-46,-10,16])
  translate([-8.2,y,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
 for(s=[-1,1],z=[-45,16])scale([s,1,1])
  translate([32,-14,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
}
module audit_bosses(){difference(){union(){body_split_bosses();body_mount_bosses();}
 body_split_fastener_cuts();body_side_cuts();}}
module audit_protected(){
 // Keep the three holes and full outer washer bearing footprints unchanged.
 for(z=[-10,0,10])translate([51,-17.51,z])rotate([-90,0,0])cylinder(h=4.02,d=7,$fn=72);
 // Both positive rear gib stroke stops remain exactly the old geometry.
 translate([45.9,-13.51,-6.6])cube([9.2,3,13.2]);
}
intersection(){union(){hc_keepers();import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/positive-half.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/negative-half.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/beam-grip.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/liner.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/right-support.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/left-support.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/x-gib.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/x-cover.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/frame.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/fixed-spacer.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/moving-spacer.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/capture-right.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pipe-clamp-right.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-cap-right.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-gib-right-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/finger-right-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pin-block-right-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-gib-right-rear.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/finger-right-rear.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pin-block-right-rear.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/capture-left.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pipe-clamp-left.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-cap-left.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-gib-left-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/finger-left-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pin-block-left-front.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/y-gib-left-rear.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/finger-left-rear.stl");import("/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/launcher-final/pin-block-left-rear.stl");}hc_mount_drivers();}
