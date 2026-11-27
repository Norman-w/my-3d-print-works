include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-guide-revision.scad>
module actual(){cg_right_support();}
union(){difference(){import("right-support.stl");actual();}difference(){actual();import("right-support.stl");}}