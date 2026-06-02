// Boss / cavity Z lookup from side profile (generated/profiles.scad)

include <generated/profiles.scad>

function _bezier_clamp_i(i) = max(0, min(BEZIER_N - 2, i));

function _bezier_lerp(a, b, t) = a * (1 - t) + b * t;

function _bezier_idx(y) =
    let(i = floor((y - BEZIER_Y0) / BEZIER_DH))
    _bezier_clamp_i(i);

function _bezier_t(y, i) =
    let(yi = BEZIER_Y0 + i * BEZIER_DH)
    BEZIER_DH > 0 ? (y - yi) / BEZIER_DH : 0;

// Legacy HX table removed — outer shape uses generated/bezier_geometry.scad

function bezier_half_z_at(y) =
    (y < BEZIER_Y0 || y > BEZIER_Y1) ? blade_half_t :
    let(i = _bezier_idx(y), t = _bezier_t(y, i))
    _bezier_lerp(BEZIER_HZ[i], BEZIER_HZ[i + 1], t);
