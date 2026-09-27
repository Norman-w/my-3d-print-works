// Nominal METAL reference solids omitted from earlier combined reviews.
// Units mm; threads/socket recesses are not represented. Never print these.
// Placement contract is checked against feeder-body.scad by the integration audit.
include <parameters.scad>
use <feeder-cam-guide-revision.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>
use <feeder-seam-candidate.scad>

fh_part="assembly";
fh_t=0;
fh_fault=0;
fh_frame_installed=true;
fh_eps=.02;
fh_seam_y=40;
fh_seam_z=[-72,-46,-10,16];
fh_seam_head_under_x=3.8;
fh_seam_nut_x=-7;
fh_mount_nut_x=33.1;
fh_mount_y=-14;
fh_mount_z=[-45,16];

module fh_x_cyl(x,y,z,h,d,n=64){translate([x,y,z])rotate([0,90,0])cylinder(h=h,d=d,$fn=n);}
module fh_x_nut(x,y,z){difference(){
    fh_x_cyl(x,y,z,2.4,5.5/cos(30),6);
    fh_x_cyl(x-fh_eps,y,z,2.4+2*fh_eps,3.2);
}}
module fh_seam_bolts(){for(y=[-fh_seam_y,fh_seam_y],z=fh_seam_z){
    fh_x_cyl(fh_seam_head_under_x-12,y,z,12,3);
    fh_x_cyl(fh_seam_head_under_x,y,z,3,5.5);
}}
module fh_seam_nuts(){for(y=[-fh_seam_y,fh_seam_y],z=fh_seam_z)
    fh_x_nut(fh_seam_nut_x,y,z);}
module fh_mount_nuts(){for(side=[-1,1],z=fh_mount_z)scale([side,1,1])
    fh_x_nut(fh_mount_nut_x,fh_mount_y,z);}
module fh_added_hardware(){fh_seam_bolts();fh_seam_nuts();fh_mount_nuts();}
module fh_seam_tools(){for(y=[-fh_seam_y,fh_seam_y],z=fh_seam_z)
    fh_x_cyl(fh_seam_head_under_x+3,y,z,65,4);}
module fh_seam_nut_feeds(){for(y=[-fh_seam_y,fh_seam_y],z=fh_seam_z)hull(){
    fh_x_cyl(fh_seam_nut_x,y,z,2.4,5.5/cos(30),6);
    fh_x_cyl(fh_seam_nut_x-30,y,z,2.4,5.5/cos(30),6);
}}
module fh_mount_nut_feeds(){for(side=[-1,1],z=fh_mount_z)scale([side,1,1])hull(){
    fh_x_cyl(fh_mount_nut_x,fh_mount_y,z,2.4,5.5/cos(30),6);
    fh_x_cyl(fh_mount_nut_x+30,fh_mount_y,z,2.4,5.5/cos(30),6);
}}
module fh_other_solids(){cg_body();cg_fixed();cg_gib();revision_gibs();if(fh_frame_installed)cg_moving(fh_t);}
if(fh_part=="assembly")color([.25,.28,.3])fh_added_hardware();
else if(fh_part=="seam-bolts")fh_seam_bolts();
else if(fh_part=="seam-nuts")fh_seam_nuts();
else if(fh_part=="mount-nuts")fh_mount_nuts();
else if(fh_part=="fit")intersection(){fh_other_solids();translate([0,fh_fault,0])fh_added_hardware();}
else if(fh_part=="hardware-fit")intersection(){fh_added_hardware();cg_old_hardware();}
else if(fh_part=="seam-tools")intersection(){fh_other_solids();fh_seam_tools();}
else if(fh_part=="mount-feed")intersection(){cg_body();fh_mount_nut_feeds();}
else if(fh_part=="seam-feed")intersection(){cg_body();fh_seam_nut_feeds();}
else if(fh_part=="wrong-mount-sequence")intersection(){cg_fixed();fh_mount_nut_feeds();}
