// SmartPaddle mechanical/electrical handoff contract.
// Current documented combination: M7.C5 (version is descriptive only).
// This file is included by enclosure/paddle_shell.scad and independently
// checked against the current KiCad PCB by scripts/validate_mechanical_handoff.py.

// Protected 14500 supplied by the user: protection PCB remains within the
// cell diameter and adds no more than 2 mm to a nominal 50 mm cell.
protected_14500_max_d = 14.0;
protected_14500_max_l = 52.0;
protected_14500_fit_radial_clearance = 0.15;
protected_14500_fit_axial_clearance = 0.25;
// Move the protected cell 5 mm toward the paddle head (+Y).  The former
// center at Y=-138 crossed the obsolete pair of M2 boss columns at Y=-160.
protected_14500_center = [0, -133.0, 0];

// Two purchased MX1.25 finished-wire branches.  Each branch contains four
// UL1571 28 AWG conductors (7 x 0.12 mm tinned copper), OD about 0.9 mm,
// with a 3 mm tinned free end.  A 2 x 2 bundle is given a 2.0 mm square
// passage; bend radius is intentionally not part of this fit contract.
handle_wire_od = 0.9;
handle_wire_conductors_per_branch = 4;
handle_wire_branch_count = 2;
handle_wire_tinned_end_l = 3.0;
handle_wire_corridor_size = 2.0;
handle_wire_corridor_center_x = 8.2;
handle_wire_corridor_y0 = -159.25;
handle_wire_corridor_y1 = -106.75;
handle_wire_neck_center_x = 4.0;
handle_wire_neck_y = -98.5;

// Current physical PCB wire-pad facts: Ø2.5 mm land, Ø1.2 mm drill.  The
// shell pocket is Ø3.5 mm, giving 0.5 mm radial clearance around the copper,
// and reaches 0.5 mm deeper than the ordinary rigid-PCB cavity on both sides.
pzt_wire_pad_d = 2.5;
pzt_wire_pad_drill = 1.2;
pzt_solder_relief_d = 3.5;
pzt_solder_relief_extra_depth = 0.5;
pzt_solder_pad_centers_scad = [
    [-39.116, -42.512],  // pzt_bl.pzt_gnd_pad
    [-34.925, -46.068],  // pzt_bl.pzt_signal_pad
    [ 35.052, -46.068],  // pzt_br.pzt_gnd_pad
    [ 38.989, -42.766],  // pzt_br.pzt_signal_pad
    [-29.972,  45.245],  // pzt_tl.pzt_gnd_pad
    [-34.417,  42.070],  // pzt_tl.pzt_signal_pad
    [ 34.544,  41.943],  // pzt_tr.pzt_gnd_pad
    [ 29.972,  45.245],  // pzt_tr.pzt_signal_pad
];
