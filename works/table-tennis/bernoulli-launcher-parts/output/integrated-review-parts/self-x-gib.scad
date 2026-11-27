include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-guide-revision.scad>
module actual(){cg_gib();}
union(){difference(){import("x-gib.stl");actual();}difference(){actual();import("x-gib.stl");}}