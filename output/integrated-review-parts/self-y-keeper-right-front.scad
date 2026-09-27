include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-guide-revision.scad>
module actual(){revision_keeper_local();}
union(){difference(){import("y-keeper-right-front.stl");actual();}difference(){actual();import("y-keeper-right-front.stl");}}