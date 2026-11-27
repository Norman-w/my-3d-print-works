// Review-only probe of the stated -Z nut insertion path.
feeder_support_library_mode=true;
include <../../cad/feeder-supports.scad>
review_nut_z=-15;
review_with_spring_interface=true;
module candidate_nut() {
    difference() {
        support_y_hex(-support_cap_screw_x,review_nut_z,18.1,2.4,5.5);
        support_y_hole(-support_cap_screw_x,review_nut_z,18,3,3.2);
    }
}
intersection() {
    candidate_nut();
    union() {
        mirror([1,0,0]) feeder_side_support_local();
        if(review_with_spring_interface) feeder_spring_fixed_interface();
    }
}
