// v5 thread-only profile sweep. Product mounting/support logic stays elsewhere.
// Derived from openscad-stl-print anchored-helix workflow at skill 77f77fd.
// No runtime includes from a former project version or from the skill repo.
module v5_profile_helix(zlo,zhi,anchor,pitch,profile,phase=0,steps_turn=128) {
    assert(zhi>zlo && pitch>0 && len(profile)>=4);
    start=anchor+floor((zlo-anchor)/pitch-1)*pitch;
    stop=anchor+ceil((zhi-anchor)/pitch+1)*pitch;
    steps=round((stop-start)/pitch*steps_turn);
    n=len(profile);
    points=[for(i=[0:steps]) for(p=profile)
        let(z=start+(stop-start)*i/steps,a=phase+360*(z-anchor)/pitch)
        [p[0]*cos(a),p[0]*sin(a),z+p[1]]];
    faces=concat([[for(j=[n-1:-1:0]) j]],[[for(j=[0:n-1]) steps*n+j]],
        [for(i=[0:steps-1]) for(j=[0:n-1])
        [i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j]]);
    bound=max([for(p=profile) p[0]])+1;
    intersection() {
        polyhedron(points=points,faces=faces,convexity=40);
        translate([-bound,-bound,zlo]) cube([2*bound,2*bound,zhi-zlo]);
    }
}

function v5_male_profile() = [
    [v5_core_r-v5_root_embed,-v5_profile_half],
    [v5_core_r-v5_shoulder_burial,-v5_profile_half],
    [v5_core_r+v5_thread_h,-v5_crest_w/2],
    [v5_core_r+v5_thread_h, v5_crest_w/2],
    [v5_core_r-v5_shoulder_burial, v5_profile_half],
    [v5_core_r-v5_root_embed, v5_profile_half]
];

// Translate EVERY male profile point radially, expand upper/lower axial
// sides by the same clearance. The result is a paired real tooth envelope.
function v5_female_profile() = [for(p=v5_male_profile())
    [p[0]+v5_radial_clearance,
     p[1]+(p[1]<0 ? -v5_axial_clearance : v5_axial_clearance)]];

module v5_male_ridge() {
    intersection() {
        v5_profile_helix(v5_male_z0,v5_male_z1,v5_male_z0,v5_pitch,
            v5_male_profile(),v5_phase,v5_steps_per_turn);
        // Fully buried ends avoid tiny flat ledges caused by circle faceting.
        rotate_extrude() polygon([
            [0,v5_male_z0],[v5_core_r-v5_runout_bury,v5_male_z0],
            // Keep the envelope outside the crest (also between polygon
            // vertices). Tangent coincident cylinders otherwise leave
            // float32-degenerate slivers in binary STL boolean output.
            // The actual crest radius remains fixed by the tooth profile.
            [v5_male_major/2+0.02,v5_male_z0+v5_runout_l],
            [v5_male_major/2+0.02,v5_male_z1-v5_runout_l],
            [v5_core_r-v5_runout_bury,v5_male_z1],[0,v5_male_z1]]);
    }
}

module v5_female_groove() {
    v5_profile_helix(v5_female_z0,v5_female_z1,v5_female_z0,v5_pitch,
        v5_female_profile(),v5_phase,v5_steps_per_turn);
}
