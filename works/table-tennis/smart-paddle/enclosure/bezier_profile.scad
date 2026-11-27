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

// BEZIER_HX 是拍头/拍柄合并后的包络，肩颈附近会转入拍面宽度；
// TPU 把套必须只跟随真实手柄 planform，不能在肩颈处突然膨胀到拍面宽度。
function bezier_handle_hx_at(y) =
    max([
        for (i = [0:len(BEZIER_HANDLE_PLANFORM) - 2])
            let(
                a = BEZIER_HANDLE_PLANFORM[i],
                b = BEZIER_HANDLE_PLANFORM[i + 1],
                dy = b[1] - a[1]
            )
            abs(dy) > 0.0001
                && ((a[1] <= y && y <= b[1]) || (b[1] <= y && y <= a[1]))
                ? abs(a[0] + (y - a[1]) / dy * (b[0] - a[0]))
                : 0
    ]);
