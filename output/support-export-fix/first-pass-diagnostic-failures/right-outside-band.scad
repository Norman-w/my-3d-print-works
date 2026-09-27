module old(){use <unfixed-source/feeder-cam-guide-revision.scad>
use <unfixed-source/feeder-guide-revision.scad>
use <unfixed-source/feeder-supports.scad>
cg_right_support();
}
module revised(){use <fixed-source/feeder-cam-guide-revision.scad>
use <fixed-source/feeder-guide-revision.scad>
use <fixed-source/feeder-supports.scad>
cg_right_support();
}
difference(){difference(){old();revised();}union(){for(g=[0,-28.5])translate([57.999,-14.001,g-4.301])cube([.022,9.322,8.602]);}}
