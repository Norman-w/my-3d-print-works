# Direct-pull v2 — isolated candidate, not released

Frozen source: `candidate.scad`, SHA-256 `f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588`. No formal `cad/` or web file was modified. Current evidence index is `local-review-summary.json`; native exports and local checks are in `runs/20260927T084134904834Z-f76a83eeb9/`.

The fixed R59.25 contact surface now has centre `[-24,0,2]`. With a nominal Ø1.5 core the ideal centreline radius is 60 mm. The M6 outlet remains `[-29+delta,60,2]`, so the initial axial straight segment is `5-delta`: 3–7 mm over the explicit `delta=-2..2` assembly budget. The guide's lower connecting rib reaches its whole base; all new guide material grows from local Z−12. The adjuster and ferrule move with delta; the two thin nuts and metal washers stay at the fixed seat faces. Each thread end retains at least 1.2 mm nominal exposed length; unprovided chamfer/runout is not assumed away.

At fixed delta, the constant inlet term cancels from `L(theta,delta)-L(0,delta)`. The ideal positive-tension u20 solution is 19.3342519252°; u22 is 21.3139729946°. The same original axis, finger shape, host interface, main cover and two-screw terminal cap remain. This is not the old `u/60` wrap motion. Actual cable friction, bending, ferrule seating and tension remain physical uncertainties.

## Evidence completed

- **176 local native cases:** source stable; body exported by CGAL, lever/cap/cover by Manifold; each final print mesh is closed, one connected component, with no non-manifold edge or vertex-link defect. Motion and free-core checks sampled u0…20 and22 at delta−2/0/+2; separate continuous adjuster exterior range, assembly/removal and positive controls are recorded. Named thrust/clamping planes and intentional guide/core tangency are classified separately. This is not an arbitrary-slack or continuous full-motion proof.
- **New native offline slices:** `slices/20260927T084928459673Z-f76a83eeb9/` contains body and lever at 0.1 mm, X1C/.4, PETG, support disabled. Both native warning strings are empty and both actual 3MF artifact checks are `SLICE_ARTIFACT_IDENTITY_PASS`, including unchanged triangle counts and no reported repair.
- **Exact reuse only:** `slice-reuse-proof.json` proves the v2 terminal cap and main cover STL bytes match the old 0.1 mm/no-support inputs. Their original invocations and original source attribution were not rewritten. Cap wire/ball/fastener paths were re-evaluated against the v2 motion contract.
- **Version-specific path review:** `path_review.py`, `body_path_review.py` and `guide_path_review.py` live here; no frozen v1 helper was edited. Actual 3MF placement and G-code bead widths/heights are mapped back to input-local coordinates.

Lever and terminal cap have zero conservative path intrusions into the nominal Ø5 ball, M3 rod/head and SW5.5 nut envelopes. Minimum ball clearance lower bounds are 0.27685 and0.29078 mm. The lever's first12 mm cable capsule has minimum0.35635 mm lower clearance at u0/10/20/22 samples. Printed split Z3.1, nut roof−.6 and head shoulder4.5 are at their intended actual layer boundaries. These are nominal emitted-bead margins, not measured printed tolerances.

The body M6 seat and three stop cavities contain no support paths. The new guide adds no non-bed horizontal underside: the whole-STL survey finds the two retained rear M3 nut-roofs at localZ−9 and the retained stop nut-roof atZ4.9. The M3 roofs still begin with overhanging circular paths; their up-to12.5 mm curved no-prior-overlap path length is **not** a straight bridge span or proof of successful bridging. The stop chamber's actual roof paths cross a roughly2.96 mm no-prior-overlap interval. Images preserve the complete geometry and previous-layer footprints.

The retained body rear-nut roofs step from a SW5.8 hex cavity to a Ø3.4 passage: in plan the nominal inward radial step is 2.9−1.7=1.20 mm at each hex flat, up to 5.8/√3−1.7≈1.649 mm toward a hex corner. The roughly12.5 mm path figure follows part of a circular deposited wall around the hole; it is not a12.5 mm straight bridge across empty space. It nevertheless lacks previous-layer underlay in that interval, so same-layer bonding and PETG sag are unresolved. The lever’s new SW5.8 nut recesses have the same nominal shoulder step; the cap Ø6.2 head recess toØ3.4 passage has a1.40 mm radial shoulder. The terminal path checks prove nominal opening/metal clearance and layer placement, not successful printing of those shoulders. The body stop nut-roof retains the reported roughly2.96 mm previous-layer gap; M6 and round stop bores retain their curved roof overhang/short bridge paths. None receives a manufacturing PASS from the empty native warning field.

The guide intentionally contacts the wire. Its worst conservative actual-bead clearance is−0.001748 mm after an explicit0.00325 mm arc/buffer over-cover, plus a separately recorded tiny contact-arc approximation. This is a contact/fit boundary, not a new demonstrated jam, and not evidence of low friction. The solid guide begins on the bed and rises vertically; no new unsupported guide roof was found.

## Re-run selected checks

Use `/Applications/FreeCAD.app/Contents/Resources/bin/python` for scripts needing NumPy/Shapely/Matplotlib.

```sh
python output/cable-direct-pull-v2/path_review.py --folder output/cable-direct-pull-v2/slices/20260927T084928459673Z-f76a83eeb9/cable-input-lever
python output/cable-direct-pull-v2/path_review.py --folder output/print-review/current-cable/20260927T082206132152Z/cable-input-terminal-cap
python output/cable-direct-pull-v2/body_path_review.py --folder output/cable-direct-pull-v2/slices/20260927T084928459673Z-f76a83eeb9/cable-input-body
python output/cable-direct-pull-v2/guide_path_review.py --folder output/cable-direct-pull-v2/slices/20260927T084928459673Z-f76a83eeb9/cable-input-body
```

`run_slices.py` creates a new timestamped slice directory; `review.py` creates a new timestamp-and-source-SHA native directory. Do not overwrite old failures or treat a stale STL as the result of an empty intersection.

## Integration and remaining boundary

Public `cdp_body()`, `cdp_lever(u)`, `cdp_terminal_cap(u)`, `cdp_cover()`, fixed/moving hardware, cable and adjuster/ferrule modules return feeder CAD coordinates. `cdp_direct_contract()` emits the live parameter contract. `cdp_part` selectors are listed there. Body native export should use CGAL.

Install terminal ball and two cap nuts on the bench, close the small cap with its two M3 screws, then assemble main cover and mount the module. For service, unload/disconnect cable and remove the whole input module as required before opening toward local+Z; do not infer in-place cover access from isolated cap sweeps. Delta is adjusted only during assembly, with housing/ferrule reseated and nuts locked before defining zero. The SW8 adjuster-head tool and loose-nut transient remain separate open service checks.

Root-owned route and host checks must use new moving endpoints and the v2 body; old fixed-route PASS cannot be reused. Adoption must replace the old motion contract/animation, account for the extra two-screw terminal cap and update absolute bare-core length. PETG fit, guide abrasion/friction, return-force margin, stop synchronization, broken-wire behavior and real one-ball feeding are not certified by this candidate. Nothing has been sent to a printer.
