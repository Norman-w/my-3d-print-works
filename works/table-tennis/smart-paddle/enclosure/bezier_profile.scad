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
    // 实体外沿夹到端点厚度，避免退回 blade_half_t 把尾端基台削扁。
    y <= BEZIER_Y0 ? BEZIER_HZ[0] :
    y >= BEZIER_Y1 ? BEZIER_HZ[BEZIER_N] :
    let(i = _bezier_idx(y), t = _bezier_t(y, i))
    _bezier_lerp(BEZIER_HZ[i], BEZIER_HZ[i + 1], t);

function bezier_envelope_hx(y) =
    y <= BEZIER_Y0 ? BEZIER_HX[0] :
    y >= BEZIER_Y1 ? BEZIER_HX[BEZIER_N] :
    let(i = _bezier_idx(y), t = _bezier_t(y, i))
    _bezier_lerp(BEZIER_HX[i], BEZIER_HX[i + 1], t);
