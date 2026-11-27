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
difference(){old();revised();}
