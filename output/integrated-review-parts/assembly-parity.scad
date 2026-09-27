include <../../cad/parameters.scad>
use <../../cad/feeder-integrated-candidate.scad>
use <../../cad/feeder-cam-guide-revision.scad>
use <../../cad/feeder-review-parts.scad>
module exported(){rp_item(part="positive-half",t=0);
rp_item(part="negative-half",t=0);
rp_item(part="beam-grip",t=0);
rp_item(part="liner",t=0);
rp_item(part="right-support",t=0);
rp_item(part="left-support",t=0);
rp_item(part="x-gib",t=0);
rp_item(part="x-cover",t=0);
rp_item(part="frame",t=0);
rp_item(part="capture",t=0,side=1);
rp_item(part="pipe-clamp",t=0,side=1);
rp_item(part="y-cap",t=0,side=1);
rp_item(part="y-gib",t=0,side=1,rear=false);
rp_item(part="y-keeper",t=0,side=1,rear=false);
rp_item(part="finger",t=0,side=1,rear=false);
rp_item(part="y-gib",t=0,side=1,rear=true);
rp_item(part="y-keeper",t=0,side=1,rear=true);
rp_item(part="finger",t=0,side=1,rear=true);
rp_item(part="capture",t=0,side=-1);
rp_item(part="pipe-clamp",t=0,side=-1);
rp_item(part="y-cap",t=0,side=-1);
rp_item(part="y-gib",t=0,side=-1,rear=false);
rp_item(part="y-keeper",t=0,side=-1,rear=false);
rp_item(part="finger",t=0,side=-1,rear=false);
rp_item(part="y-gib",t=0,side=-1,rear=true);
rp_item(part="y-keeper",t=0,side=-1,rear=true);
rp_item(part="finger",t=0,side=-1,rear=true);
rp_item(part="hardware",t=0);
rp_item(part="pc-reference",t=0);}
module reference(){ic_fixed();cg_moving(0);}
union(){difference(){exported();reference();}difference(){reference();exported();}}
