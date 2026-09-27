# Captured stop nut: bearing contact, not a radial fit failure

The original 202 flags and −0.0181307064 mm clearance lower bound remain unchanged in the source report. All 202 nearest hardware points are on **local X = −32.6**, the deliberately touching axial bearing face. The inspected CAD rotates the hexagonal nut exactly as the clearance ROI does; this is not an axis/hex-orientation error.

The worst actual command is G-code line **349521**, a straight `Overhang wall` at print Z15.8, local slab Z3.7…3.8, declared width0.45. Its centreline lies at X≈−32.38988. The nominal half-width therefore extends to X≈−32.61488: 0.0148807 mm past the ideal bearing face, or 0.0181307 mm including the unchanged 0.00325 mm analysis allowance. A strictly interior witness is local **[−32.6074,−24,3.75]**. It is outside the nut bore and inside both the nominal solid nut and declared extrusion slab. This is not merely zero-thickness contact, but the declared slab is not a measurement of deposited PETG.

A second check keeps the **same full SW5.5 × 2.4 mm nut**, orientation, and error allowance. Its continuous +X insertion is represented by the exact swept hexagonal prism:

| Final front face | Swept X interval | Model commands checked | Flags | Minimum lower clearance |
|---|---|---:|---:|---:|
| Nominal −32.600 | −90…−32.600 | 5746 | 202 | −0.0181307 mm |
| 0.019 mm before that face | −90…−32.619 | 5746 | 0 | +0.0008693 mm |

This is an axial pose comparison, not a narrower nut or a deleted radial ROI. The nut at the second pose occupies X[−35.019,−32.619], leaving 3.281 mm inside the existing −38.3…−32.6 axial pocket behind it. Since the approach to that pose is clear and the original pose crosses the declared bead envelope, first axial contact occurs between the two poses under this model. No separate radial obstruction was found along that complete approach.

**This flag does not justify enlarging SW5.8 or revising/re-slicing CAD.** It identifies the small difference between an ideal zero-clearance bearing datum and the declared sliced surface. Actual assembly seats the nut against the printed face, then adjusts the stop. The 0.019 mm comparison is not a claim of printing accuracy, a calibrated stop value, full-face bearing contact, or physical fit. If exact nominal seating at X−32.6 is a requirement, the present data do not establish it; arbitrarily widening the radial pocket would not establish that datum either.

The continuous path check covers this printed body only after support removal. Supplier tolerances, real bead shape/sag, finish, seating force, bearing strength, and other hardware/tool access remain outside this limited check. No manufacturing or physical release is asserted.

Reproduce with:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python output/current-eclip-slices-review/stop-nut-audit/audit_stop_nut.py
```

`report.json` records source hashes, the full worst command, witness, insertion bounds, and limitations; `raw-hits.json` and `swept-insertion.json` retain individual commands. The original `body-clearance-review.json`, CAD, G-code, and profiles were not modified.
