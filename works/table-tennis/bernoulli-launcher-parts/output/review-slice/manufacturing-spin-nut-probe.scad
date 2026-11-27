// Review-only probe. This file does not alter candidate CAD.
include <manufacturing-snapshot/cad/spin-parameters.scad>
use <manufacturing-snapshot/cad/spin-head.scad>
review_nut_y=14.5;
review_with_cage_bolt=true;
review_nut_thickness=3.2;
review_nut_af=7;
module candidate_nut() {
    difference() {
        cyl_x(55.75,review_nut_y,43,review_nut_thickness,review_nut_af/cos(30),6);
        cyl_x(55.7,review_nut_y,43,3.4,4.5);
    }
}
intersection() {
    candidate_nut();
    union() {
        cover();
        if(review_with_cage_bolt) cyl_x(47,11,43,12,3);
    }
}
