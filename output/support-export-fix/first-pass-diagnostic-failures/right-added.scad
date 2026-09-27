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
difference(){revised();old();}
