// Project-local, self-contained r/z profile sweep, adapted from the installed
// openscad-stl-print anchored-helix workflow. No imports from obsolete models.
// Thread geometry only: no bayonet/lug or support-generation logic here.
module v4_profile_helix(zlo,zhi,anchor,pitch,profile,phase=0,steps_turn=128) {
    assert(zhi>zlo && pitch>0 && len(profile)>=4);
    start=anchor+floor((zlo-anchor)/pitch-1)*pitch;
    stop=anchor+ceil((zhi-anchor)/pitch+1)*pitch;
    steps=round((stop-start)/pitch*steps_turn);
    n=len(profile);
    points=[for(i=[0:steps]) for(p=profile)
        let(z=start+(stop-start)*i/steps,a=phase+360*(z-anchor)/pitch)
        [p[0]*cos(a),p[0]*sin(a),z+p[1]]];
    faces=concat([[for(j=[n-1:-1:0]) j]],
        [[for(j=[0:n-1]) steps*n+j]],
        [for(i=[0:steps-1]) for(j=[0:n-1])
        [i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j]]);
    bound=max([for(p=profile) p[0]])+1;
    intersection() {
        polyhedron(points=points,faces=faces,convexity=20);
        translate([-bound,-bound,zlo]) cube([2*bound,2*bound,zhi-zlo]);
    }
}

function v4_reference_male_profile() = [
    [v4_core_od/2-v4_root_embed,-v4_root_w/2],
    [v4_male_major/2,-v4_crest_w/2],
    [v4_male_major/2, v4_crest_w/2],
    [v4_core_od/2-v4_root_embed, v4_root_w/2]
];

function v4_female_profile() = [
    [v4_groove_r0,-v4_root_w/2-v4_axial_clearance],
    [v4_groove_r1,-v4_crest_w/2-v4_axial_clearance],
    [v4_groove_r1, v4_groove_top_outer],
    [v4_groove_r0, v4_groove_top_root]
];

module v4_female_groove() {
    v4_profile_helix(v4_female_z0,v4_female_z1,v4_female_z0,v4_pitch,
        v4_female_profile(),v4_phase,v4_steps_per_turn);
}

// Compatibility specimen only; preserve the baseline male exactly.
module v4_reference_male_ridge() {
    intersection() {
        v4_profile_helix(v4_male_z0,v4_male_z1,v4_male_z0,v4_pitch,
            v4_reference_male_profile(),v4_phase,v4_steps_per_turn);
        union() {
            translate([0,0,v4_male_z0]) cylinder(h=1,d1=v4_core_od,d2=v4_male_major);
            translate([0,0,v4_male_z0+1]) cylinder(h=v4_male_z1-v4_male_z0-2,d=v4_male_major);
            translate([0,0,v4_male_z1-1]) cylinder(h=1,d1=v4_male_major,d2=v4_core_od);
        }
    }
}
