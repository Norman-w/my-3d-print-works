include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-review-parts.scad>
module exported(){import("positive-half.stl");
import("negative-half.stl");
import("beam-grip.stl");
import("liner.stl");
import("right-support.stl");
import("left-support.stl");
import("x-gib.stl");
import("x-cover.stl");
import("frame.stl");
import("capture-right.stl");
import("pipe-clamp-right.stl");
import("y-cap-right.stl");
import("y-gib-right-front.stl");
import("y-keeper-right-front.stl");
import("finger-right-front.stl");
import("y-gib-right-rear.stl");
import("y-keeper-right-rear.stl");
import("finger-right-rear.stl");
import("capture-left.stl");
import("pipe-clamp-left.stl");
import("y-cap-left.stl");
import("y-gib-left-front.stl");
import("y-keeper-left-front.stl");
import("finger-left-front.stl");
import("y-gib-left-rear.stl");
import("y-keeper-left-rear.stl");
import("finger-left-rear.stl");
import("pc-reference.stl");rp_hardware();}
module reference(){ic_fixed();cg_moving(0);}
union(){difference(){exported();reference();}difference(){reference();exported();}}
