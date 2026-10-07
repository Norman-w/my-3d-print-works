// Independent product copy of the canonical anchored axial r-z sweep.
// No runtime dependency on Ø41 source, old model versions or the skill tree.
// Six-point embedded root follows the canonical instruction to keep the
// exposed flank independent of embed; radial/axial clearance translates it.
module f76_profile_helix(zlo,zhi,anchor,profile) {
    start=anchor+floor((zlo-anchor)/f76_pitch-1)*f76_pitch;
    stop=anchor+ceil((zhi-anchor)/f76_pitch+1)*f76_pitch;
    steps=round((stop-start)/f76_pitch*f76_steps_turn);
    n=len(profile);
    pts=[for(i=[0:steps]) for(p=profile)
        let(z=start+(stop-start)*i/steps,a=360*(z-anchor)/f76_pitch)
        [p[0]*cos(a),p[0]*sin(a),z+p[1]]];
    faces=concat([[for(j=[n-1:-1:0]) j]],
        [[for(j=[0:n-1]) steps*n+j]],
        [for(i=[0:steps-1]) for(j=[0:n-1])
         [i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j]]);
    bound=max([for(p=profile) p[0]])+1;
    intersection() {
        polyhedron(points=pts,faces=faces,convexity=60);
        translate([-bound,-bound,zlo]) cube([2*bound,2*bound,zhi-zlo]);
    }
}

function f76_male_profile() = [
    [f76_core_r-f76_root_embed,-f76_profile_half],
    [f76_core_r-f76_shoulder_burial,-f76_profile_half],
    [f76_core_r+f76_thread_h,-f76_crest_w/2],
    [f76_core_r+f76_thread_h, f76_crest_w/2],
    [f76_core_r-f76_shoulder_burial, f76_profile_half],
    [f76_core_r-f76_root_embed, f76_profile_half]
];
function f76_female_profile() = [for(p=f76_male_profile())
    [p[0]+f76_radial_clear,p[1]+(p[1]<0 ? -f76_axial_clear : f76_axial_clear)]];

module f76_male_ridge() {
    intersection() {
        f76_profile_helix(f76_male_z0,f76_male_z1,f76_male_z0,f76_male_profile());
        // Full-burial runouts; envelope exceeds crest slightly to avoid
        // coincident polygons/float32 slivers. Actual tooth OD remains 41.8.
        rotate_extrude() polygon([
            [0,f76_male_z0],[f76_core_r-f76_runout_bury,f76_male_z0],
            [f76_male_major/2+0.02,f76_male_full_z0],
            [f76_male_major/2+0.02,f76_male_full_z1],
            [f76_core_r-f76_runout_bury,f76_male_z1],[0,f76_male_z1]]);
    }
}
module f76_female_groove() {
    f76_profile_helix(f76_female_cut_z0,f76_female_cut_z1,
        f76_female_z0,f76_female_profile());
}
