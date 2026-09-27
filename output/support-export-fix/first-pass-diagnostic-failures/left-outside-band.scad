module old(){use <unfixed-source/feeder-cam-guide-revision.scad>
use <unfixed-source/feeder-guide-revision.scad>
use <unfixed-source/feeder-supports.scad>
union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
}
module revised(){use <fixed-source/feeder-cam-guide-revision.scad>
use <fixed-source/feeder-guide-revision.scad>
use <fixed-source/feeder-supports.scad>
union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}
}
difference(){difference(){old();revised();}mirror([1,0,0])union(){for(g=[0,-28.5])translate([57.999,-14.001,g-4.301])cube([.022,9.322,8.602]);}}
