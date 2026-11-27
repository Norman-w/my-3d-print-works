include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-guide-revision.scad>
module actual(){revision_gib_local();}
union(){difference(){import("y-gib-right-front.stl");actual();}difference(){actual();import("y-gib-right-front.stl");}}