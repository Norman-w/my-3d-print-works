include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-guide-revision.scad>
module actual(){ic_host_half(true);}
union(){difference(){import("positive-half.stl");actual();}difference(){actual();import("positive-half.stl");}}