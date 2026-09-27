// Local keeper clearance for the four existing M3 support mounting screws.
// No host holes, guide working surfaces, or mounting datums are modified.
include <parameters.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>

hc_part="assembly";
hc_rear=false;
hc_head_clearance=0.25;
hc_head_outer_x=47.30;
hc_driver_d=4.20;       // cylindrical tool envelope, not a selected driver model
hc_driver_clearance=0.20;

function hc_gate_z(rear)=rear?-gate_spacing:0;

module hc_x_cylinder(x,y,z,length,d,n=72) {
    translate([x,y,z])rotate([0,90,0])cylinder(h=length,d=d,$fn=n);
}

module hc_keeper_cuts_local(rear=false) {
    for(z=[-45,16]) {
        // Relative +Y sweep is the exact removal direction when the keeper
        // moves towards -Y past an already fitted support screw and washer.
        // A common washer-radius envelope also clears the smaller screw head.
        hull() for(y=[-14,6])
            hc_x_cylinder(43.45,y,z-hc_gate_z(rear),
                hc_head_outer_x-43.45,7+2*hc_head_clearance);
        // The driver reaches the head along X, independently of keeper removal.
        // It needs only a shallow scallop at the front keeper's top end.
        hc_x_cylinder(47.05,-14,z-hc_gate_z(rear),45,
            hc_driver_d+2*hc_driver_clearance);
    }
}

module hc_keeper_local(rear=false) {
    difference(){revision_keeper_local();hc_keeper_cuts_local(rear);}
}

module hc_keepers() {
    for(side=[-1,1],rear=[false,true])
        scale([side,1,1])translate([0,0,hc_gate_z(rear)])hc_keeper_local(rear);
}

// The one-piece fixed keeper bosses also block the axial installation of the
// support screw/washer. Start outside the support spine X<=43.5: its mounting
// seat must not be bored away. This cut reaches at most Y=-10.25, behind the
// unchanged keeper nut seats beginning at Y=-8.6 and away from both Y guides.
module hc_support_service_cuts_local() {
    for(z=[-45,16])
        hc_x_cylinder(47.05,-14,z,45,7+2*hc_head_clearance);
}

// Pass an already globally placed right/left support as the child. Compatible
// with yg_right_support()/yg_left_support(); do not mirror the child again.
module hc_support_clearance(side=1) {
    assert(side==1 || side==-1);
    difference(){children();scale([side,1,1])hc_support_service_cuts_local();}
}

// These audit references duplicate only the explicit, frozen hardware envelope
// in feeder_mount_hardware. The audit compares their union with that source.
module hc_mount_one_local(z=16) {
    hc_x_cylinder(32,-14,z,12,3,32);
    hc_x_cylinder(43.5,-14,z,.5,7,32);
    hc_x_cylinder(44,-14,z,3,5.5,32);
}

module hc_mount_sweep_local(rear=false,dy=20,dx=0) {
    for(z=[-45,16],p=[[32,12,3],[43.5,.5,7],[44,3,5.5]])
        hull() for(s=[0,1])
            hc_x_cylinder(p[0]+s*dx,-14+s*dy,z-hc_gate_z(rear),p[1],p[2],32);
}

module hc_mount_drivers() {
    for(side=[-1,1],z=[-45,16])scale([side,1,1])
        hc_x_cylinder(47.05,-14,z,45,hc_driver_d/cos(180/72));
}

if(hc_part=="keeper")hc_keeper_local(hc_rear);
else if(hc_part=="assembly") {
    color([.2,.55,.8])hc_keepers();
    color([.45,.45,.48])feeder_mount_hardware();
}
