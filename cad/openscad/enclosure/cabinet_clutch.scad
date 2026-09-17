// SmartPartsDrawer 抽屉动力母线与中心纯永磁离合机构
//
// Mechanical contract
// process: FDM fit prototype; gears/pulleys in PETG or nylon, metal 3 mm D rod preferred
// material: PETG/nylon for printed parts; motor, belts, springs and screws are purchased parts
// parting_plane: cabinet front face Z = 0 and back face Z = -D; all new drive parts stay in the rear cavity or below drawers
// opening_direction: drawers pull toward +Z; the removable back panel is serviced toward -Z
// fastener: center clutch uses a removable M3 mechanism plate; old screw/fork
// follower remains legacy-only; motor/rod mounts are parameterized
// seal: none — this is a mechanism prototype, not a watertight enclosure
// print_orientation: gears/pulleys flat with their axis vertical (+Y); center
// carrier, printed guide sleeves and plate are separate PETG service parts;
// the two guide rods are purchased metal references
// units: mm
//
// User/world coordinate contract (the canonical web view is from the rear):
//   X = cabinet width; in a front view +X is screen-right, while in the rear view +X appears screen-left
//   Y = height/elevation, +Y is screen-up
//   Z = cabinet depth, front is Z=0 and rear is -Z
// The rear camera stands on the -Z side and looks along +Z, so +Z points
// away from the rear observer toward the cabinet front. A front camera shows
// the requested +X-to-the-right orientation.
// The green arrow in the supplied rear references is +Y, not +Z.
// Tensioner orientation: the T crossbar/base is on the front-side end and the
// long T rod extends toward -Z; its tip is therefore at the cabinet rear.
// The screw bore opens at the +X end and the fastener advances along -X.
//
// cabinet_params.scad is used only as the dimension source. All geometry in
// this file is written directly in the user/world frame; no final coordinate
// swap or view-only transform is used.

//#region 导入/依赖
QUALITY = is_undef(QUALITY) ? 2 : QUALITY;
// cabinet.scad owns the generic PART/EXPLODE variables, so use namespaced
// controls for this root entry to keep its library include side-effect free.
CLUTCH_PART = is_undef(CLUTCH_PART) ? "assembly" : CLUTCH_PART;
CLUTCH_EXPLODE = is_undef(CLUTCH_EXPLODE) ? 0 : CLUTCH_EXPLODE;
ENGAGED = is_undef(ENGAGED) ? false : ENGAGED;
SELECTED_COLUMN = is_undef(SELECTED_COLUMN) ? 2 : SELECTED_COLUMN;
SELECTED_ROW = is_undef(SELECTED_ROW) ? 2 : SELECTED_ROW;
// Start the physical validation scene with one known-good center station.
// Set SHOW_LEGACY_STATIONS=true only when the remaining 24 old stations are
// ready to be reviewed again; this keeps unverified legacy clutches out of the
// main assembly and out of the drawer-drive preview by default.
SHOW_LEGACY_STATIONS = is_undef(SHOW_LEGACY_STATIONS)
    ? false
    : SHOW_LEGACY_STATIONS;

// Read the frozen cabinet dimensions directly. The old cabinet geometry file
// is intentionally not included; this scene owns its native X/Y/Z geometry.
include <cabinet_params.scad>
// Keep the canonical world cabinet on the same motor-mount truth source as
// cabinet.scad/cabinet_chain.scad.  The shared mount is authored in the
// cabinet local frame (X=width, Y=depth, Z=height); this native root maps it
// below with [x, y, z] -> [x, z, -y].
include <cabinet_motor_mount_params.scad>
include <cabinet_motor_mount.scad>
use <../parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
use <../ch1_03c_long_gear_shaft.scad>
include <../ch1_03c_gt2_clutch_pair.scad>
include <../parts/center_clutch_selector_shoe.scad>
// The center station reuses the finished CH1 03C rounded-triangle/magnet
// construction.  This main scene's vertical shaft is the existing 12T / 3 mm
// profile, so override the standalone pair's 10T / 2.4 mm datum after
// including it.  The exact X1C-fine 15T / 2.4 mm pair remains a separate
// printable sample; it must not be mixed into this 3 mm cabinet assembly.
GT2_CLUTCH_EMBEDDED = true;
GT2_LONG_TEETH = 12;
GT2_LONG_PITCH_MM = 3.0;
GT2_LONG_TOOTH_DEPTH = 0.82;
GT2_MALE_TEETH = 12;
GT2_MALE_PITCH_MM = 3.0;
GT2_MALE_TOOTH_DEPTH = 0.82;
// The larger 3 mm-compatible tooth ring needs a deliberate +Z stand-off from
// the vertical rod.  0.32 mm leaves both the mother wall and the 2GT belt
// back-envelope above the pair's 0.45 mm clearance requirement.
GT2_GEAR_MESH_CLEARANCE = 0.32;
// The authored Y-axis long gear shaft is the real middle-column member.  The
// assembly calls its parameterized library API below with this enclosure's
// live 3 mm mating datum, so the standalone X1C-fine default cannot silently
// mismatch the existing clutch gears.
// A numeric override is used by the geometry gate to sample the complete
// open-to-engaged travel.  The normal assembly still derives its position from
// ENGAGED, so a preview/export without an override has exactly the two
// contract end states.
CENTER_CLUTCH_TRAVEL_MM = is_undef(CENTER_CLUTCH_TRAVEL_MM)
    ? (ENGAGED ? GT2_CLUTCH_ENGAGE_STROKE_MM : 0)
    : CENTER_CLUTCH_TRAVEL_MM;
// The snake-chain selector shoe is already constrained by the existing chain
// plane and cannot be lowered without putting the lowest chain layer into the
// cabinet floor.  Lift the complete center clutch datum instead, preserving
// the chain/motor mount and giving the shoe a real under-rotor approach.
CENTER_CLUTCH_VERTICAL_LIFT_MM = is_undef(CENTER_CLUTCH_VERTICAL_LIFT_MM)
    ? 5.00
    : CENTER_CLUTCH_VERTICAL_LIFT_MM;
//#endregion

//#region 常量/配置
$fa = QUALITY <= 1 ? 10 : 6;
$fs = QUALITY <= 1 ? 0.50 : 0.24;

// HTD3M-like pitch is kept as the single timing-belt pitch for this prototype.
TIMING_PITCH_MM = 3.0;
TIMING_TEETH = 20;
TIMING_TOOTH_DEPTH = 0.86;
TIMING_PULLEY_W = 5.0;
TIMING_BELT_W = 5.0;
TIMING_BELT_T = 1.8;
TIMING_BELT_CLEAR = 0.65;
// The timing pulley is a 20T / 3 mm-pitch wheel.  Its polygon leaves a
// 0.40-pitch root gap (the 0.8→1.0→0.2 sector); the belt tooth is narrower
// than that gap and is shallower than the 0.86 mm pulley tooth depth.
TIMING_MESH_CLEAR = 0.12;
TIMING_BELT_TOOTH_H = max(0.20, TIMING_TOOTH_DEPTH - TIMING_MESH_CLEAR);
TIMING_BELT_TOOTH_BASE = TIMING_PITCH_MM * 0.36;
TIMING_BELT_TOOTH_TIP = TIMING_PITCH_MM * 0.22;

// A 3 mm D rod is the default because it matches the Pololu output shaft.
// For a long production shaft, replace the rod with a metal D shaft or increase ROD_D.
ROD_D = 3.0;
ROD_FLAT_DEPTH = 0.50;
ROD_CLEARANCE = 0.12;
ROD_FLAT_CLEARANCE = 0.12;
ROD_WALL_CLEAR = 0.35;
ROUND_BORE_D = ROD_D + 2 * ROD_CLEARANCE;

// The upper clutch wheel is a 12T spur/dog prototype.  The pitch and all mating
// wheels are shared so the open/closed relation is not hidden in placements.
CLUTCH_PITCH_MM = 3.0;
CLUTCH_GEAR_TEETH = 12;
CLUTCH_GEAR_TOOTH_DEPTH = 0.82;
CLUTCH_GEAR_T = 3.0;
CLUTCH_GEAR_PITCH_R = CLUTCH_GEAR_TEETH * CLUTCH_PITCH_MM / (2 * PI);
CLUTCH_GEAR_OUTER_R = CLUTCH_GEAR_PITCH_R + CLUTCH_GEAR_TOOTH_DEPTH;
CLUTCH_DOG_TEETH = 12;
CLUTCH_DOG_TOOTH_H = 0.90;
CLUTCH_DOG_T = 3.0;
CLUTCH_DOG_R = CLUTCH_GEAR_OUTER_R;
CLUTCH_HUB_D = 4.0;
CLUTCH_CARRIER_STEM_H = 0.60;
CLUTCH_DOG_CLEAR = 0.25;
CLUTCH_ENGAGED_OVERLAP = 0.20;
CLUTCH_DROP_MM = 10.0;

// The fork compresses a spring between the stationary lower dog and the upper
// carrier.  The open gap is deliberately 2× one dog tooth height as requested.
CLUTCH_OPEN_GAP = 2 * CLUTCH_DOG_TOOTH_H;
CLUTCH_SPRING_WIRE_D = 0.65;
CLUTCH_SPRING_OD = 4.8;
CLUTCH_SPRING_TURNS = 4;
CLUTCH_SPRING_MIN_H = 0.70;
CLUTCH_SCREW_D = 3.0;
CLUTCH_SCREW_HEAD_D = 6.0;
CLUTCH_SCREW_HEAD_H = 1.35;
CLUTCH_SCREW_SHAFT_L = 9.0;
CLUTCH_SCREW_RECESS_OPEN = 2 * CLUTCH_DOG_TOOTH_H;
CLUTCH_SCREW_FLUSH = 0.18;
COMPOUND_LAYER_GAP = 0.35;

// Rear cavity locations. The horizontal bus is behind the partition; the
// complete pulley OD must clear the partition rear edge, not just its center.
// The front pulleys sit under the drawer fronts and send motion along +Z.
// The cabinet occupies -D..0: front is the zero datum and rear is negative Z.
WORLD_PARTITION_FRONT_Z = -FRONT_NET;
WORLD_PARTITION_T = PARTITION_T;
WORLD_PARTITION_BACK_Z = WORLD_PARTITION_FRONT_Z - WORLD_PARTITION_T;
WORLD_GRID_ORIGIN_X = WALL + SERVICE_W;
WORLD_GRID_ORIGIN_Y = WALL + SERVICE_H;
WORLD_GRID_W = GRID_W;
WORLD_GRID_H = GRID_H;
WORLD_BAY_W = BAY_W;
WORLD_BAY_H = BAY_H;
WORLD_COL_PITCH = COL_PITCH;
WORLD_ROW_PITCH = ROW_PITCH;
WORLD_DIV_T = DIV_T;
WORLD_SHELF_T = SHELF_T;
WORLD_BACK_PANEL_T = BACK_PANEL_T;
// The native drawer drive shares the rear cavity with the legacy snake-chain
// world adapter. That adapter places the chain at local Y=PARTITION_BACK_Y+
// 12 mm, which becomes world Z=-(PARTITION_BACK_Y+12) after the rear-view
// conversion. Keep the chain envelope as an explicit collision datum instead
// of moving the drawer drive by an unexplained magic offset.
SNAKE_CHAIN_CENTER_Z = -(PARTITION_BACK_Y + 12.0);
SNAKE_CHAIN_HALF_DEPTH = 3.0;       // 12T sprocket envelope: local Y 72..78
SNAKE_CHAIN_REAR_EDGE_Z = SNAKE_CHAIN_CENTER_Z - SNAKE_CHAIN_HALF_DEPTH;

// Native aliases preserve the world-scene diagnostics while deriving every
// value from cabinet_motor_mount_params.scad.  The local seat's depth axis is
// inverted into native world -Z, so its two local Y hole offsets are negated.
SNAKE_MOTOR_MOUNT_CENTER_X = motor_mount_c()[0];
SNAKE_MOTOR_MOUNT_SEAT_CENTER_X = MOTOR_MOUNT_OMEGA_SEAT_CENTER_X;
SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z = -(
    MOTOR_MOUNT_CHAIN_Y + MOTOR_MOUNT_OMEGA_SEAT_CENTER_Y_LOCAL
);
SNAKE_MOTOR_MOUNT_SEAT_FASTENER_OFFSETS_Z = [
    for (offset_y = MOTOR_MOUNT_OMEGA_SEAT_FASTENER_OFFSETS_Y) -offset_y
];
SNAKE_MOTOR_BOSS_STAGE1_H = MOTOR_MOUNT_BOSS_STAGE1_H;
SNAKE_MOTOR_BOSS_STAGE1_EMBED = MOTOR_MOUNT_BOSS_STAGE1_EMBED;
SNAKE_MOTOR_BOSS_STAGE1_Y0 = MOTOR_MOUNT_BOSS_STAGE1_Z0;
SNAKE_MOTOR_BOSS_STAGE1_TOP_Y = MOTOR_MOUNT_BOSS_STAGE1_TOP_Z;
SNAKE_MOTOR_BOSS_RAIL_W = MOTOR_MOUNT_BOSS_STAGE1_RAIL_W;
SNAKE_MOTOR_BOSS_RAIL_L = MOTOR_MOUNT_BOSS_STAGE1_RAIL_L;
SNAKE_MOTOR_BOSS_RAIL_R = MOTOR_MOUNT_BOSS_STAGE1_RAIL_R;
SNAKE_MOTOR_BOSS_GUIDE_H = MOTOR_MOUNT_BOSS_GUIDE_H;
SNAKE_MOTOR_BOSS_GUIDE_OD = MOTOR_MOUNT_BOSS_GUIDE_OD;
SNAKE_MOTOR_BOSS_GUIDE_BORE_D = MOTOR_MOUNT_BOSS_PILOT_D;
SNAKE_MOTOR_BOSS_GUIDE_TOP_Y = MOTOR_MOUNT_BOSS_GUIDE_TOP_Z;
DRAWER_BUS_CHAIN_CLEARANCE = is_undef(DRAWER_BUS_CHAIN_CLEARANCE)
    ? 2.0
    : DRAWER_BUS_CHAIN_CLEARANCE;

// World Z- is toward the cabinet rear. The complete drawer power bus moves
// together: motor, five Y-directed spline columns, rear clutch stacks, and
// their rear timing pulleys. The motor is mounted directly on the +X-most
// drawer column; there is no extra D-axis column. The drawer-front output
// datum stays at the existing front interface; the belt length is re-derived
// below.
DRAWER_DRIVE_REAR_SHIFT_Z = is_undef(DRAWER_DRIVE_REAR_SHIFT_Z)
    ? -18.0
    : DRAWER_DRIVE_REAR_SHIFT_Z;
DRIVE_AXIS_Z_BASE = WORLD_PARTITION_BACK_Z - 13.0;
DRIVE_AXIS_Z = DRIVE_AXIS_Z_BASE + DRAWER_DRIVE_REAR_SHIFT_Z;
// In the canonical rear view, +X is on the left. The motor is centered on
// the last drawer column (the +X-most column), so its output shaft enters that
// column's lower D stub directly. It is not a separate boundary axis.
MOTOR_COLUMN = N_COL - 1;
MOTOR_X = WORLD_GRID_ORIGIN_X + MOTOR_COLUMN * WORLD_COL_PITCH
    + WORLD_BAY_W / 2;
// The current bus therefore has exactly five physical vertical columns. A
// future independent tensioner boundary is reserved separately and is not
// counted as a drawer column.
ACTIVE_VERTICAL_AXIS_COUNT = N_COL;
PLANNED_VERTICAL_AXIS_COUNT = N_COL + 1;
VERTICAL_AXIS_COUNT = ACTIVE_VERTICAL_AXIS_COUNT;
BUS_BOTTOM_Y = WORLD_GRID_ORIGIN_Y - 5.0;
BUS_TOP_Y = H - WALL - 7.0;
MOTOR_BODY_L = 25.6;
MOTOR_SHAFT_L = 9.0;
// The gearbox face is one output-shaft length below the column's lower datum;
// the 9 mm D output shaft then overlaps the column's lower D stub.
MOTOR_FACE_Y = BUS_BOTTOM_Y - MOTOR_SHAFT_L;
ROD_BOTTOM_Y = BUS_BOTTOM_Y - 6.0;
ROD_TOP_Y = BUS_TOP_Y + 6.0;
LEFT_D_AXIS_Y0 = MOTOR_FACE_Y + MOTOR_SHAFT_L - 1.0;

// The middle-column shaft consumes the authored long-gear-shaft geometry.
// Keep the mating profile on the live 3 mm clutch datum. The tooth body stops
// before each 2GT pulley face; only the integral D stubs pass through the
// pulley. This keeps the 6 mm belt and its two guide planes visible instead
// of letting the larger 3 mm-pitch gear section cover the pulley.
VERTICAL_GEAR_TEETH = CLUTCH_GEAR_TEETH;
VERTICAL_GEAR_PITCH_MM = CLUTCH_PITCH_MM;
VERTICAL_GEAR_TOOTH_DEPTH = CLUTCH_GEAR_TOOTH_DEPTH;
VERTICAL_GEAR_TIP_START = 0.20;
VERTICAL_GEAR_TIP_END = 0.50;
VERTICAL_GEAR_ROOT_END = 0.80;
VERTICAL_GEAR_END_STUB_LENGTH = 6.0;
VERTICAL_GEAR_STUB_OVERLAP = 0.20;

// Timing dimensions remain available for the drawer take-offs. The former
// rear-view-right idler geometry is intentionally not part of this prototype.
TIMING_PITCH_R = TIMING_TEETH * TIMING_PITCH_MM / (2 * PI);
TIMING_ROOT_R = TIMING_PITCH_R - TIMING_TOOTH_DEPTH;
TIMING_OUTER_R = TIMING_PITCH_R + TIMING_TOOTH_DEPTH;
// Keep the front pulley at the existing drawer-front interface while the rear
// bus moves backward. The default front datum is the former 60T-loop location
// (-16 mm in this cabinet); the nearest integer tooth count is then chosen so
// the new belt remains on the 3 mm pitch instead of being stretched.
DRAWER_FRONT_INTERFACE_Z = is_undef(DRAWER_FRONT_INTERFACE_Z)
    ? DRIVE_AXIS_Z_BASE + 60.0
    : DRAWER_FRONT_INTERFACE_Z;
DRAWER_BELT_TEETH = is_undef(DRAWER_BELT_TEETH)
    ? round(
        (2 * (DRAWER_FRONT_INTERFACE_Z - DRIVE_AXIS_Z)
            + 2 * PI * TIMING_PITCH_R) / TIMING_PITCH_MM
      )
    : DRAWER_BELT_TEETH;
DRAWER_BELT_CENTER_DISTANCE = (
    DRAWER_BELT_TEETH * TIMING_PITCH_MM - 2 * PI * TIMING_PITCH_R
) / 2;
// The rear take-off is at DRIVE_AXIS_Z; +Z leads toward the drawer front.
// With the default shift this is a 72T loop: its 78 mm centre distance puts
// the front pulley back at the original -16 mm drawer interface.
FRONT_PULLEY_Z = DRIVE_AXIS_Z + DRAWER_BELT_CENTER_DISTANCE;
// The belt base is dimensioned from the mating pulley: its inner base radius
// is the pulley pitch radius, and its radial base thickness is exactly the
// belt thickness.  TIMING_BELT_CLEAR is reserved for cabinet passage/fit
// clearance; it must not be added to the printed belt cross-section.
TIMING_BELT_BASE_INNER_R = TIMING_PITCH_R;
TIMING_BELT_BASE_OUTER_R = TIMING_BELT_BASE_INNER_R + TIMING_BELT_T;
// Smooth retaining flanges sit above and below every timing pulley. They are
// intentionally larger than the toothed outer circle so the belt cannot walk
// off the pulley in Z.
TIMING_FLANGE_MARGIN = 1.0;
TIMING_FLANGE_T = 0.80;
TIMING_FLANGE_R = TIMING_OUTER_R + TIMING_FLANGE_MARGIN;
TIMING_FLANGE_D = 2 * TIMING_FLANGE_R;
// SKP-to-SCAD parametric reconstruction.  The supplied SKP is not imported
// as a frozen STL.  Its measured primitive layout is rebuilt below with
// editable boxes, slots, bores, and annular plates.
//
// The supplied SKP group measures 9 × 42 × 22 mm in native SketchUp X/Y/Z.
// The requested world-axis correspondence is explicit:
//   SketchUp green (+Y) -> world +X  (42 mm)
//   SketchUp red   (+X) -> world +Y  ( 9 mm)
//   SketchUp blue  (+Z) -> world Z axis, reversed onto world -Z  (22 mm)
// The blue direction is reversed so the T long rod points toward the cabinet
// rear while the part still uses the shared world Z axis. No viewer-only
// transform or imported mesh is involved.
TENSIONER_SKP_NATIVE_MIN_X = -2.0;
TENSIONER_SKP_NATIVE_MIN_Y = 0.0;
TENSIONER_SKP_NATIVE_MIN_Z = -2.0;
TENSIONER_SKP_NATIVE_SIZE_X = 9.0;
TENSIONER_SKP_NATIVE_SIZE_Y = 42.0;
TENSIONER_SKP_NATIVE_SIZE_Z = 22.0;
TENSIONER_SKP_WORLD_SIZE_X = TENSIONER_SKP_NATIVE_SIZE_Y;
TENSIONER_SKP_WORLD_SIZE_Y = TENSIONER_SKP_NATIVE_SIZE_X;
TENSIONER_SKP_WORLD_SIZE_Z = TENSIONER_SKP_NATIVE_SIZE_Z;
// Low-X placement: this is the right-hand side in the canonical rear view.
TENSIONER_SKP_WORLD_CENTER_X = WALL + 1.0 + TENSIONER_SKP_WORLD_SIZE_X / 2;
TENSIONER_SKP_WORLD_CENTER_Y = BUS_TOP_Y;
// The SKP bearing ring is one millimetre toward the rear from the mapped T
// envelope centre.  Put that ring on the same Z axis as the vertical-column
// bus wheels; the wheel/shaft assembly below can then move along X without
// changing the verified SKP orientation.
TENSIONER_SKP_WORLD_CENTER_Z = DRIVE_AXIS_Z + 1.0;

// Main SKP body: a 9×42×22 mm envelope made from a 2 mm base and a 5×20 mm
// upper rail.  Native coordinates here are SketchUp red/green/blue axes;
// tensioner_native_box() maps them to SCAD/world X/Y/Z at the point of use.
// The native blue span -2..20 is reflected onto world Z: the short crossbar
// is at local world Z=0..2 and the long T rod reaches toward world -Z.
TENSIONER_MAIN_BASE_X0 = -2.0;
TENSIONER_MAIN_BASE_Y0 = 0.0;
TENSIONER_MAIN_BASE_Z0 = -2.0;
TENSIONER_MAIN_BASE_DX = 9.0;
TENSIONER_MAIN_BASE_DY = 42.0;
TENSIONER_MAIN_BASE_DZ = 2.0;
TENSIONER_MAIN_UPPER_X0 = 0.0;
TENSIONER_MAIN_UPPER_Y0 = 0.0;
TENSIONER_MAIN_UPPER_Z0 = 0.0;
TENSIONER_MAIN_UPPER_DX = 5.0;
TENSIONER_MAIN_UPPER_DY = 42.0;
TENSIONER_MAIN_UPPER_DZ = 20.0;

// The two side openings are deliberately separate because the SKP uses
// different 1 mm border offsets on the two sides of the rail.
TENSIONER_MAIN_LEFT_SLOT_X0 = -EPS;
TENSIONER_MAIN_LEFT_SLOT_Y0 = 4.0;
TENSIONER_MAIN_LEFT_SLOT_Z0 = 4.0;
TENSIONER_MAIN_LEFT_SLOT_DX = 2.0 + EPS;
TENSIONER_MAIN_LEFT_SLOT_DY = 27.0;
TENSIONER_MAIN_LEFT_SLOT_DZ = 12.0;
TENSIONER_MAIN_RIGHT_SLOT_X0 = 2.0;
TENSIONER_MAIN_RIGHT_SLOT_Y0 = 3.0;
TENSIONER_MAIN_RIGHT_SLOT_Z0 = 3.0;
TENSIONER_MAIN_RIGHT_SLOT_DX = 3.0 + EPS;
TENSIONER_MAIN_RIGHT_SLOT_DY = 29.0;
TENSIONER_MAIN_RIGHT_SLOT_DZ = 14.0;

// Circular features in the main body.  The small bore is blind; the large
// bore exits the far end of the 42 mm rail.  Both axes are native green (+Y),
// which becomes the SCAD/world +X direction under the requested mapping.
TENSIONER_MAIN_SMALL_BORE_X = 3.5;
TENSIONER_MAIN_SMALL_BORE_Y0 = 1.5;
TENSIONER_MAIN_SMALL_BORE_Z = 10.0;
TENSIONER_MAIN_SMALL_BORE_D = 2.0;
TENSIONER_MAIN_SMALL_BORE_L = 1.5;
TENSIONER_MAIN_LARGE_BORE_X = 2.5;
TENSIONER_MAIN_LARGE_BORE_Y0 = 32.0;
TENSIONER_MAIN_LARGE_BORE_Z = 10.0;
TENSIONER_MAIN_LARGE_BORE_D = 4.0;
TENSIONER_MAIN_LARGE_BORE_L = 10.0;

// The first nested SKP group is a 3 mm native-red-axis annular plate.
TENSIONER_RING_X0 = 2.0;
TENSIONER_RING_Y0 = 11.0;
TENSIONER_RING_Z0 = 5.0;
TENSIONER_RING_DX = 3.0;
TENSIONER_RING_DY = 10.0;
TENSIONER_RING_DZ = 10.0;
TENSIONER_RING_OUTER_D = 10.0;
TENSIONER_RING_INNER_D = 6.0;

// The second nested SKP group is a 3 mm plate with an axis-red Ø10 through
// bore and a native-green Ø2 blind bore.  Its local origin is retained so the
// two nested bodies remain adjustable relative to the main rail.
TENSIONER_PLATE_X0 = 2.0;
TENSIONER_PLATE_Y0 = 9.5;
TENSIONER_PLATE_Z0 = 3.5;
TENSIONER_PLATE_DX = 3.0;
TENSIONER_PLATE_DY = 14.0;
TENSIONER_PLATE_DZ = 13.0;
TENSIONER_PLATE_BORE_D = 10.0;
TENSIONER_PLATE_SMALL_BORE_LOCAL_X = 1.5;
TENSIONER_PLATE_SMALL_BORE_LOCAL_Y0 = -1.0;
TENSIONER_PLATE_SMALL_BORE_LOCAL_Z = 6.5;
TENSIONER_PLATE_SMALL_BORE_D = 2.0;
TENSIONER_PLATE_SMALL_BORE_L = 2.5;

// SketchUp used 24 segments for the circular edges in this reference.  It is
// kept as a parameter so the reference can be matched or smoothed later.
TENSIONER_SKP_ARC_SEGMENTS = 24;
TENSIONER_SKP_WORLD_BBOX_MIN_X = TENSIONER_SKP_NATIVE_MIN_Y;
TENSIONER_SKP_WORLD_BBOX_MIN_Y = TENSIONER_SKP_NATIVE_MIN_X;
TENSIONER_SKP_WORLD_BBOX_MIN_Z = -(
    TENSIONER_SKP_NATIVE_MIN_Z + TENSIONER_SKP_NATIVE_SIZE_Z
);
TENSIONER_PARAM_WORLD_ORIGIN_X = TENSIONER_SKP_WORLD_CENTER_X
    - TENSIONER_SKP_WORLD_BBOX_MIN_X - TENSIONER_SKP_WORLD_SIZE_X / 2;
TENSIONER_PARAM_WORLD_ORIGIN_Y = TENSIONER_SKP_WORLD_CENTER_Y
    - TENSIONER_SKP_WORLD_BBOX_MIN_Y - TENSIONER_SKP_WORLD_SIZE_Y / 2;
TENSIONER_PARAM_WORLD_ORIGIN_Z = TENSIONER_SKP_WORLD_CENTER_Z
    - TENSIONER_SKP_WORLD_BBOX_MIN_Z - TENSIONER_SKP_WORLD_SIZE_Z / 2;

// The drawer rack/drive geometry is intentionally explicit.  The horizontal
// rack is under each drawer; the rear timing pulley and front timing pulley
// share one Y-running belt.
DRAWER_RACK_TOOTH_H = 1.25;
DRAWER_RACK_PITCH = 3.0;
FRONT_GEAR_TEETH = 16;
FRONT_GEAR_TOOTH_DEPTH = 1.0;
FRONT_GEAR_T = 3.2;
FRONT_GEAR_PITCH_R = FRONT_GEAR_TEETH * CLUTCH_PITCH_MM / (2 * PI);
FRONT_GEAR_ROOT_R = FRONT_GEAR_PITCH_R - FRONT_GEAR_TOOTH_DEPTH;
FRONT_GEAR_OUTER_R = FRONT_GEAR_PITCH_R + FRONT_GEAR_TOOTH_DEPTH;

// Fork clearance is a real parameter: open state leaves the fork just above
// the recessed screw head; engaged state makes it nearly flush with the gear.
FORK_W = 14.0;
FORK_D = 9.0;
FORK_T = 2.4;
FORK_CLEAR_OPEN = 0.55;
FORK_CONTACT = 0.08;

// Colors are only for the assembly preview; STL units remain millimeters.
COLOR_CABINET = "#6f8f9a";
COLOR_DRAWER = "#d3b184";
COLOR_SHAFT = "#5c6876";
COLOR_TIMING = "#f0a23b";
COLOR_BELT = "#ce5c31";
COLOR_GEAR = "#d6a64a";
COLOR_DOG = "#a9b4c0";
COLOR_SPRING = "#e6c24a";
COLOR_FORK = "#45d85c";
COLOR_RACK = "#9a77c7";
COLOR_MOTOR = "#343a40";
COLOR_TENSIONER_T_SOLID = "#aebdce";
// Diagnostic world-space triad. The origin is the cabinet front/lower/low-X
// datum [0, 0, 0]; it is shown in assembly and in CLUTCH_PART=world_axes only.
WORLD_AXIS_ORIGIN = [0, 0, 0];
WORLD_AXIS_LENGTH = 28.0;
WORLD_AXIS_SHAFT_D = 1.35;
WORLD_AXIS_HEAD_L = 5.0;
WORLD_AXIS_HEAD_D = 4.8;
WORLD_AXIS_LABEL_SIZE = 5.5;
WORLD_AXIS_LABEL_T = 0.65;
COLOR_AXIS_X = "#ef4444";
COLOR_AXIS_Y = "#22c55e";
COLOR_AXIS_Z = "#3b82f6";
//#endregion

//#region 模型/类型
// Part values:
//   assembly       cabinet + bus + one center CH1 03C clutch/2GT drive path
//   cabinet        cabinet shell and drawer ghosts
//   cabinet_context wire-frame cabinet + bay dividers + drawer context
//   power_bus      active motor + five-column 2GT bus and adjustable return wheel
//   all_vertical_axes  active D drive + five drawer axes
//   drawer_drive   rear/front compound wheels, +Z drawer belts and racks
//   clutch         center clutch by default; old stations require SHOW_LEGACY_STATIONS
//   clutch_detail  selected center mechanism (or a legacy station when enabled)
//   motor/motor_body/motor_shaft/left_d_axis/side_axes/column/vertical_rack
//   column_sync_belt_bottom/column_sync_belt_top/column_sync_tensioner
//   tensioner_t_solid
//   upper_clutch/upper_spur/upper_dog/lower_takeoff/lower_dog/rear_pulley
//   spring/screw/fork/drawer_belt/front_compound/front_pulley/front_gear/drawer_rack
//   world_axes                 native +X/+Y/+Z diagnostic triad at the origin
//                  individual verification pieces for the one-by-one workflow
//
// The center replacement uses the finished CH1 03C pair: a +Z-offset axis-Y
// input male gear with a rounded-triangle/magnet nose enters the fixed output
// female receiver above it. The female body also carries the 2GT rear pulley.
// The pair is captured by cabinet_clutch_carrier.scad: two independent D
// shafts, four 3x6x2 bearing references, dual Ø3 guide rods with printed
// sleeves, a removable plate and
// hard stops. The other 24 legacy stations are intentionally suppressed until
// this physical prototype is approved.
//#endregion

//#region 私有成员：几何函数
function timing_points(teeth, root_r, tip_r) = [
    for (i = [0:teeth - 1])
        for (p = [[0.00, root_r], [0.20, tip_r], [0.50, tip_r], [0.80, root_r]])
            let (a = (i + p[0]) * 360 / teeth)
                [p[1] * cos(a), p[1] * sin(a)]
];

function world_col_x(i) = WORLD_GRID_ORIGIN_X + i * WORLD_COL_PITCH;

function world_col_center_x(i) = world_col_x(i) + WORLD_BAY_W / 2;

function world_row_y(j) = WORLD_GRID_ORIGIN_Y + j * WORLD_ROW_PITCH;

function world_row_center_y(j) = world_row_y(j) + WORLD_BAY_H / 2;

function world_drawer_outer_w() = WORLD_BAY_W - 2 * DRAWER_CLEAR;

function world_drawer_outer_h() = WORLD_BAY_H - 2 * DRAWER_CLEAR;

function clutch_col_x(i) = world_col_center_x(i);

function clutch_upper_open_y(row) = world_row_center_y(row) - CLUTCH_DROP_MM;

function clutch_fixed_dog_y(row) =
    clutch_upper_open_y(row)
    - CLUTCH_GEAR_T / 2
    - CLUTCH_DOG_T
    - CLUTCH_CARRIER_STEM_H
    - CLUTCH_OPEN_GAP
    - CLUTCH_DOG_T / 2;

function clutch_upper_y(row, engaged) =
    clutch_upper_open_y(row)
    - (engaged ? CLUTCH_OPEN_GAP + CLUTCH_ENGAGED_OVERLAP : 0);

function clutch_upper_dog_y(row, engaged) =
    clutch_upper_y(row, engaged)
    - CLUTCH_GEAR_T / 2
    - CLUTCH_DOG_T / 2
    - CLUTCH_CARRIER_STEM_H;

function clutch_takeoff_pulley_y(row) =
    clutch_fixed_dog_y(row)
    - CLUTCH_DOG_T / 2
    - COMPOUND_LAYER_GAP
    - TIMING_PULLEY_W / 2;

function drawer_belt_y(row) = clutch_takeoff_pulley_y(row);

function clutch_screw_top_y(row, engaged) =
    clutch_upper_y(row, engaged)
    + CLUTCH_GEAR_OUTER_R
    - (engaged ? CLUTCH_SCREW_FLUSH : CLUTCH_SCREW_RECESS_OPEN);

function drawer_front_gear_y(row) =
    drawer_belt_y(row)
    + TIMING_PULLEY_W / 2
    + COMPOUND_LAYER_GAP
    + FRONT_GEAR_T / 2;

function selected_col() = min(max(0, SELECTED_COLUMN), N_COL - 1);

function selected_row() = min(max(0, SELECTED_ROW), N_ROW - 1);

// Only the center station is migrated to the finished CH1 03C mechanism.
// Columns and rows are zero-based, so this is the middle cell of the 5×5
// drawer field.  Its new mating axis is deliberately on the +Z side of the
// existing vertical 12T / 3 mm shaft.
CENTER_GT2_COL = 2;
CENTER_GT2_ROW = 2;
CENTER_GT2_BELT_TEETH = 80;       // 160 mm closed 2GT belt at 2 mm pitch
CENTER_GT2_BELT_LENGTH_MM = CENTER_GT2_BELT_TEETH * GT2_PULLEY_PITCH_MM;
CENTER_GT2_BELT_CENTER_DISTANCE = (
    CENTER_GT2_BELT_LENGTH_MM
        - 2 * PI * gt2_pulley_pitch_r()
) / 2;
// Use the same conservative back-envelope budget as the finished female
// pulley.  It is the radial envelope above the pitch circle, not the belt's
// catalog total thickness; keeping it at 0.90 mm makes the belt sit inside the
// 0.05 mm guide margin instead of visibly overhanging the retaining wall.
CENTER_GT2_BELT_T = GT2_BELT_BACK_OFFSET;
CENTER_GT2_BELT_BASE_INNER_R = gt2_pulley_pitch_r();
CENTER_GT2_BELT_BASE_OUTER_R =
    CENTER_GT2_BELT_BASE_INNER_R + CENTER_GT2_BELT_T;
CENTER_GT2_BELT_TOOTH_H = max(0.20, GT2_PULLEY_TOOTH_DEPTH - 0.12);
CENTER_GT2_BELT_TOOTH_BASE = GT2_PULLEY_PITCH_MM * 0.36;
CENTER_GT2_BELT_TOOTH_TIP = GT2_PULLEY_PITCH_MM * 0.22;

// The five vertical drawer columns share two horizontal open 2GT loops.  The
// loop length is deliberately expressed in catalog teeth, not inferred from
// a bounding box: 226T × 2 mm gives a nominal 452 mm closed belt and a 214 mm
// centre distance for the +X motor column and the -X tensioner wheel.
COLUMN_SYNC_BELT_TEETH = 226;
COLUMN_SYNC_BELT_LENGTH_MM =
    COLUMN_SYNC_BELT_TEETH * GT2_PULLEY_PITCH_MM;
COLUMN_SYNC_BELT_CENTER_DISTANCE = (
    COLUMN_SYNC_BELT_LENGTH_MM
        - 2 * PI * gt2_pulley_pitch_r()
) / 2;
// Positive adjustment is "screw out" toward the rear-view right, i.e. world
// -X.  Never add the adjustment to X: that would move the tensioner toward
// the motor and reverse the intended tension response.
VERTICAL_TENSIONER_OFFSET_X = is_undef(VERTICAL_TENSIONER_OFFSET_X)
    ? 0.0
    : VERTICAL_TENSIONER_OFFSET_X;
COLUMN_SYNC_TENSIONER_NOMINAL_X =
    MOTOR_X - COLUMN_SYNC_BELT_CENTER_DISTANCE;
COLUMN_SYNC_TENSIONER_X =
    COLUMN_SYNC_TENSIONER_NOMINAL_X - VERTICAL_TENSIONER_OFFSET_X;
COLUMN_SYNC_BELT_BASE_INNER_R = gt2_pulley_pitch_r();
COLUMN_SYNC_BELT_T = GT2_BELT_BACK_OFFSET;
COLUMN_SYNC_BELT_BASE_OUTER_R =
    COLUMN_SYNC_BELT_BASE_INNER_R + COLUMN_SYNC_BELT_T;
COLUMN_SYNC_BELT_TOOTH_H =
    max(0.20, GT2_PULLEY_TOOTH_DEPTH - 0.12);
COLUMN_SYNC_BELT_TOOTH_BASE = GT2_PULLEY_PITCH_MM * 0.36;
COLUMN_SYNC_BELT_TOOTH_TIP = GT2_PULLEY_PITCH_MM * 0.22;
// The pulley is intentionally wider than the 6 mm belt. The inward-facing
// side is the lower retainer plus half of the toothed face; leave a small
// radial-tooth-body clearance on that side so the full guide stack remains
// readable in the assembled view.
COLUMN_SYNC_PULLEY_AXIAL_WIDTH =
    GT2_BELT_LOWER_RETAINER_T
    + GT2_PULLEY_FACE_T
    + GT2_BELT_GUIDE_LIP_T;
COLUMN_SYNC_PULLEY_INNER_HALF_WIDTH =
    GT2_BELT_LOWER_RETAINER_T + GT2_PULLEY_FACE_T / 2;
VERTICAL_GEAR_END_CLEARANCE = COLUMN_SYNC_PULLEY_INNER_HALF_WIDTH + 0.35;
VERTICAL_GEAR_LENGTH = BUS_TOP_Y - BUS_BOTTOM_Y
    - 2 * VERTICAL_GEAR_END_CLEARANCE;

function is_center_gt2_station(col, row) =
    col == CENTER_GT2_COL && row == CENTER_GT2_ROW;

function center_gt2_z() = DRIVE_AXIS_Z + gt2_center_distance();

CENTER_GT2_Z = center_gt2_z();

CENTER_GT2_FRONT_PULLEY_Z =
    center_gt2_z() + CENTER_GT2_BELT_CENTER_DISTANCE;

// The first selector shoe is a native world part, not a chain-frame STL
// relocated by the browser. Its square-marked M_engage pocket is 6 mm toward
// the selector tangent from the R3C3 axis. The shoe is rotated so its blind
// magnet faces point along world +Y, from below the male rotor. The trigger
// datum is a 0.40 mm magnet-face gap below the male gear's open bottom; the
// shoe's support arm reaches back to the existing snake-chain plane.
CENTER_SELECTOR_SHOE_TANGENT_OFFSET_MM =
    GT2_ACTUATOR_TRIGGER_SPACING_MM / 2;
CENTER_SELECTOR_SHOE_TRIGGER_CLEARANCE_MM = 0.40;
CENTER_SELECTOR_SHOE_MAGNET_FACE_OFFSET_MM = CENTER_SELECTOR_SHOE_H / 2;
CENTER_SELECTOR_SHOE_TARGET_Y_MM =
    center_gt2_male_base_y(CENTER_GT2_ROW)
        - CENTER_SELECTOR_SHOE_TRIGGER_CLEARANCE_MM
        - CENTER_SELECTOR_SHOE_MAGNET_FACE_OFFSET_MM;
CENTER_SELECTOR_SHOE_NORMAL_OFFSET_MM =
    CENTER_SELECTOR_SHOE_TARGET_Y_MM
        - world_row_center_y(CENTER_GT2_ROW);
CENTER_SELECTOR_SHOE_Z_MM = center_gt2_z();
// The support arm terminates on the real R3C3 straight-chain pin datum.  The
// center axis is X=140.00; the nearest authored pin/roller center at the
// support side is X≈152.29, so use a 12.40 mm nominal arm center and let the
// 2.40 mm contact witness cover the small pin-rounding difference.  This is a
// chain interface datum, not a free visual offset.
CENTER_SELECTOR_SHOE_SUPPORT_X_OFFSET_MM = 12.40;
CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM = 2.40;
CENTER_SELECTOR_SHOE_SUPPORT_Y_T = 2.00;
CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Y_OVERHANG_MM = 1.20;
CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T = 2.40;
CENTER_SELECTOR_SHOE_SUPPORT_BRIDGE_OVERLAP_MM = 0.30;
CENTER_SELECTOR_SHOE_CHAIN_CONTACT_D_MM = 2.40;
CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM =
    world_row_center_y(CENTER_GT2_ROW);
CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM = SNAKE_CHAIN_CENTER_Z;
CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM = clutch_col_x(CENTER_GT2_COL)
    + CENTER_SELECTOR_SHOE_SUPPORT_X_OFFSET_MM;
// Keep the vertical drop of the printed chain support just outside the right
// guide rod.  Its lower foot still overlaps the Ø2.40 mm chain-pin witness at
// the authored attach datum; this offset is the clearance dog-leg, not a new
// chain coordinate.
CENTER_SELECTOR_SHOE_SUPPORT_ARM_X_OFFSET_MM = 0.80;

function center_gt2_male_base_y(row) =
    clutch_upper_open_y(row)
        + CENTER_CLUTCH_VERTICAL_LIFT_MM
        - GT2_MALE_GEAR_T / 2;

function center_gt2_male_tip_y(row) =
    center_gt2_male_base_y(row) + gt2_male_total_h();

function center_gt2_female_base_y(row) =
    center_gt2_male_tip_y(row)
        + GT2_MOTHER_GAP
        + gt2_female_total_h();

function center_gt2_belt_y(row) =
    center_gt2_female_base_y(row)
        - GT2_BELT_LOWER_RETAINER_T
        - GT2_PULLEY_FACE_T / 2;

function center_gt2_pulley_base_y(belt_y) =
    belt_y - GT2_BELT_LOWER_RETAINER_T - GT2_PULLEY_FACE_T / 2;

function center_gt2_pulley_top_y(belt_y) =
    center_gt2_pulley_base_y(belt_y)
        + GT2_BELT_LOWER_RETAINER_T
        + GT2_PULLEY_FACE_T
        + GT2_BELT_GUIDE_LIP_T;

function center_gt2_front_gear_y(row) =
    center_gt2_pulley_top_y(center_gt2_belt_y(row))
        + COMPOUND_LAYER_GAP
        + FRONT_GEAR_T / 2;

function drawer_station_belt_y(col, row) =
    is_center_gt2_station(col, row)
        ? center_gt2_belt_y(row)
        : drawer_belt_y(row);

//#endregion

//#region 私有成员：齿轮、D 轴和带
module gear_profile_2d(teeth, root_r, tip_r) {
    polygon(timing_points(teeth, root_r, tip_r));
}

module d_profile_2d(d, flat_depth, clearance = 0) {
    difference() {
        circle(d = d + 2 * clearance);
        translate([d / 2 - flat_depth + clearance, -(d + 2 * clearance)])
            square([d + 2 * clearance, 2 * (d + 2 * clearance)]);
    }
}

module d_rod_y(x, y0, z, length, d = ROD_D) {
    // A local +Z cylinder is rotated onto world +Y. The profile is in XZ.
    translate([x, y0, z])
        rotate([-90, 0, 0])
            difference() {
                cylinder(d = d, h = length);
                translate([d / 2 - ROD_FLAT_DEPTH, -d, -EPS])
                    cube([d, 2 * d, length + 2 * EPS]);
            }
}

module cylinder_x(x0, y, z, d, length) {
    // A local +Z cylinder rotated about Y becomes a world +X cylinder.
    translate([x0, y, z])
        rotate([0, 90, 0])
            cylinder(d = d, h = length);
}

module cylinder_y(x, y0, z, d, length) {
    translate([x, y0, z])
        rotate([-90, 0, 0])
            cylinder(d = d, h = length);
}

// The SKP reference is modeled in its native red/green/blue frame and mapped
// directly into the established SCAD/world frame:
//   native green (+Y) -> world +X
//   native red   (+X) -> world +Y
//   native blue  (+Z) -> world Z axis with a sign reversal onto world -Z
// Keeping these helpers separate makes the axis contract visible at every
// reconstructed feature instead of hiding it in one imported mesh transform.
module tensioner_native_box(x0, y0, z0, dx, dy, dz) {
    translate([y0, x0, -z0 - dz])
        cube([dy, dx, dz]);
}

module tensioner_native_axis_x_cylinder(x0, y, z, d, length) {
    // Native red axis (+X) is world +Y; native blue coordinates are mirrored.
    translate([y, x0, -z])
        rotate([-90, 0, 0])
            cylinder(d = d, h = length, $fn = TENSIONER_SKP_ARC_SEGMENTS);
}

module tensioner_native_axis_y_cylinder(x, y0, z, d, length) {
    // Native green axis (+Y) is world +X; native blue coordinates are mirrored.
    translate([y0, x, -z])
        rotate([0, 90, 0])
            cylinder(d = d, h = length, $fn = TENSIONER_SKP_ARC_SEGMENTS);
}

module tensioner_native_annular_plate(
    x0,
    y_center,
    z_center,
    thickness,
    outer_d,
    inner_d
) {
    // The plate normal is native red / world +Y.
    difference() {
        tensioner_native_axis_x_cylinder(
            x0,
            y_center,
            z_center,
            outer_d,
            thickness
        );
        tensioner_native_axis_x_cylinder(
            x0 - EPS,
            y_center,
            z_center,
            inner_d,
            thickness + 2 * EPS
        );
    }
}

module world_axis_arrow_x(origin, length = WORLD_AXIS_LENGTH) {
    shaft_l = max(0.1, length - WORLD_AXIS_HEAD_L);
    color(COLOR_AXIS_X) {
        cylinder_x(origin[0], origin[1], origin[2], WORLD_AXIS_SHAFT_D, shaft_l);
        translate([origin[0] + shaft_l, origin[1], origin[2]])
            rotate([0, 90, 0])
                cylinder(d1 = WORLD_AXIS_HEAD_D, d2 = 0, h = WORLD_AXIS_HEAD_L);
    }
}

module world_axis_arrow_y(origin, length = WORLD_AXIS_LENGTH) {
    shaft_l = max(0.1, length - WORLD_AXIS_HEAD_L);
    color(COLOR_AXIS_Y) {
        cylinder_y(origin[0], origin[1], origin[2], WORLD_AXIS_SHAFT_D, shaft_l);
        translate([origin[0], origin[1] + shaft_l, origin[2]])
            rotate([-90, 0, 0])
                cylinder(d1 = WORLD_AXIS_HEAD_D, d2 = 0, h = WORLD_AXIS_HEAD_L);
    }
}

module world_axis_arrow_z(origin, length = WORLD_AXIS_LENGTH) {
    shaft_l = max(0.1, length - WORLD_AXIS_HEAD_L);
    color(COLOR_AXIS_Z) {
        translate(origin)
            cylinder(d = WORLD_AXIS_SHAFT_D, h = shaft_l);
        translate([origin[0], origin[1], origin[2] + shaft_l])
            cylinder(d1 = WORLD_AXIS_HEAD_D, d2 = 0, h = WORLD_AXIS_HEAD_L);
    }
}

module world_axis_label(label, position) {
    // Labels stay centered on their world-space datum. The web ViewHelper is
    // the authoritative clickable orientation control for the rear view.
    translate(position)
        linear_extrude(height = WORLD_AXIS_LABEL_T, center = true, convexity = 4)
            text(
                label,
                size = WORLD_AXIS_LABEL_SIZE,
                halign = "center",
                valign = "center",
                font = "Liberation Sans:style=Bold"
            );
}

module world_axes_marker() {
    o = WORLD_AXIS_ORIGIN;
    l = WORLD_AXIS_LENGTH;
    // The small white origin ball makes it clear that all three arrows start
    // at the same world point even when the translucent cabinet is present.
    color("#f8fafc")
        translate(o)
            sphere(d = 3.0);
    world_axis_arrow_x(o, l);
    world_axis_arrow_y(o, l);
    world_axis_arrow_z(o, l);
    color(COLOR_AXIS_X)
        world_axis_label("+X", [o[0] + l + 3.5, o[1] + 1.0, o[2] + 0.7]);
    color(COLOR_AXIS_Y)
        world_axis_label("+Y", [o[0] + 1.5, o[1] + l + 3.5, o[2] + 0.7]);
    color(COLOR_AXIS_Z)
        world_axis_label("+Z", [o[0] + 4.0, o[1] + 1.0, o[2] + l]);
}

module timing_pulley_y(x, y, z, teeth = TIMING_TEETH, bore = "d") {
    pitch_r = teeth * TIMING_PITCH_MM / (2 * PI);
    root_r = pitch_r - TIMING_TOOTH_DEPTH;
    tip_r = pitch_r + TIMING_TOOTH_DEPTH;
    // The profile is in XZ; all layers are positioned along world +Y.
    translate([x, y - TIMING_PULLEY_W / 2 - TIMING_FLANGE_T, z])
        rotate([-90, 0, 0])
            difference() {
                union() {
                    translate([0, 0, TIMING_FLANGE_T])
                        linear_extrude(
                            height = TIMING_PULLEY_W,
                            convexity = 8
                        )
                            gear_profile_2d(teeth, root_r, tip_r);
                    // The two smooth planes are the belt guides. Their
                    // diameter is larger than the toothed circle, but they
                    // stay outside the belt groove.
                    cylinder(d = TIMING_FLANGE_D, h = TIMING_FLANGE_T);
                    translate([0, 0, TIMING_FLANGE_T + TIMING_PULLEY_W])
                        cylinder(d = TIMING_FLANGE_D, h = TIMING_FLANGE_T);
                }
                if (bore == "d")
                    translate([0, 0, -EPS])
                        linear_extrude(
                            height = TIMING_PULLEY_W
                                + 2 * TIMING_FLANGE_T
                                + 2 * EPS
                        )
                            d_profile_2d(ROD_D, ROD_FLAT_DEPTH, ROD_CLEARANCE);
                else
                    translate([0, 0, -EPS])
                        cylinder(
                            d = ROUND_BORE_D,
                            h = TIMING_PULLEY_W
                                + 2 * TIMING_FLANGE_T
                                + 2 * EPS
                        );
            }
}

module column_gt2_pulley_y(x, y, z, bore = "d") {
    // The column bus is a real GT2/2 mm interface.  Reuse the finished 12T
    // pulley profile, including its larger lower/upper guide planes, instead
    // of approximating it with the legacy 20T/3 mm timing wheel.
    base_y = y - GT2_BELT_LOWER_RETAINER_T - GT2_PULLEY_FACE_T / 2;
    translate([x, base_y, z])
        rotate([-90, 0, 0])
            difference() {
                gt2_pulley_local();
                if (bore == "d")
                    translate([0, 0, -GT2_EPS])
                        linear_extrude(
                            height = GT2_BELT_LOWER_RETAINER_T
                                + GT2_PULLEY_FACE_T
                                + GT2_BELT_GUIDE_LIP_T
                                + 2 * GT2_EPS
                        )
                            d_profile_2d(
                                ROD_D,
                                ROD_FLAT_DEPTH,
                                ROD_CLEARANCE
                            );
                else
                    translate([0, 0, -GT2_EPS])
                        cylinder(
                            d = ROUND_BORE_D,
                            h = GT2_BELT_LOWER_RETAINER_T
                                + GT2_PULLEY_FACE_T
                                + GT2_BELT_GUIDE_LIP_T
                                + 2 * GT2_EPS
                        );
            }
}

module spur_gear_y(x, y, z, teeth, pitch_mm, tooth_depth, thickness, bore_d = 3.2) {
    pitch_r = teeth * pitch_mm / (2 * PI);
    // The profile is in XZ and the axis is world +Y.
    translate([x, y - thickness / 2, z])
        rotate([-90, 0, 0])
            difference() {
                linear_extrude(height = thickness, convexity = 8)
                    gear_profile_2d(teeth, pitch_r - tooth_depth, pitch_r + tooth_depth);
                cylinder(d = bore_d, h = thickness + 2 * EPS);
            }
}

module spur_gear_z(x, y, z, teeth, pitch_mm, tooth_depth, thickness, bore_d = 3.2) {
    pitch_r = teeth * pitch_mm / (2 * PI);
    // The profile is in XY and the axis is world +Z.
    translate([x, y, z - thickness / 2])
        difference() {
            linear_extrude(height = thickness, convexity = 8)
                gear_profile_2d(teeth, pitch_r - tooth_depth, pitch_r + tooth_depth);
            cylinder(d = bore_d, h = thickness + 2 * EPS);
        }
}

module dog_face_y(x, y, z, teeth = CLUTCH_DOG_TEETH, upward = true) {
    root_r = CLUTCH_DOG_R - CLUTCH_DOG_TOOTH_H;
    // The same symmetric dog profile can face up or down.  The explicit
    // rotation documents which face the spring-loaded carrier presents.
    translate([x, y, z])
        rotate(upward ? [-90, 0, 0] : [90, 0, 0])
            difference() {
                linear_extrude(
                    height = CLUTCH_DOG_T,
                    center = true,
                    convexity = 8
                )
                    gear_profile_2d(teeth, root_r, CLUTCH_DOG_R);
                cylinder(
                    d = CLUTCH_HUB_D,
                    h = CLUTCH_DOG_T + 2 * EPS,
                    center = true
                );
            }
}

module belt_tooth_prism_z(x, z, y, inward) {
    // Rotate the same profile so its tangent follows world +Z.  In this
    // orientation local radial +Y maps to world -X, so the caller uses
    // inward=+1 on the +X run and inward=-1 on the -X run.
    translate([x, y + TIMING_BELT_W / 2, z])
        rotate([0, -90, 0])
            rotate([90, 0, 0])
                linear_extrude(height = TIMING_BELT_W + 2 * EPS)
                    polygon([
                        [-TIMING_BELT_TOOTH_BASE / 2, -inward * EPS],
                        [ TIMING_BELT_TOOTH_BASE / 2, -inward * EPS],
                        [ TIMING_BELT_TOOTH_TIP / 2, inward * TIMING_BELT_TOOTH_H],
                        [-TIMING_BELT_TOOTH_TIP / 2, inward * TIMING_BELT_TOOTH_H]
                    ]);
}

module belt_tooth_prism_arc(cx, cz, y, radial_inner, angle) {
    // At angle=0 the local +Z direction is world +X.  The tooth profile's
    // negative local radial direction therefore points into the pulley.
    translate([cx, y + TIMING_BELT_W / 2, cz])
        rotate([0, 90 - angle, 0])
            translate([0, 0, radial_inner])
                rotate([90, 0, 0])
                    linear_extrude(height = TIMING_BELT_W + 2 * EPS)
                        polygon([
                            // The root crosses the inner belt boundary by
                            // EPS toward the belt body.  Using -EPS here
                            // leaves every arc tooth as a floating solid.
                            [-TIMING_BELT_TOOTH_BASE / 2, EPS],
                            [ TIMING_BELT_TOOTH_BASE / 2, EPS],
                            [ TIMING_BELT_TOOTH_TIP / 2, -TIMING_BELT_TOOTH_H],
                            [-TIMING_BELT_TOOTH_TIP / 2, -TIMING_BELT_TOOTH_H]
                        ]);
}

module belt_loop_z_base(x, z0, z1, y) {
    inner = TIMING_BELT_BASE_INNER_R;
    outer = TIMING_BELT_BASE_OUTER_R;
    // Both drawer pulleys have vertical (+Y) axes. The belt therefore lies in
    // XZ and its two straight runs follow the drawer travel along +Z.
    translate([0, y + TIMING_BELT_W / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(height = TIMING_BELT_W, convexity = 8)
                difference() {
                    hull() {
                        translate([x, z0]) circle(r = outer);
                        translate([x, z1]) circle(r = outer);
                    }
                    hull() {
                        translate([x, z0]) circle(r = inner);
                        translate([x, z1]) circle(r = inner);
                    }
                }
}

module belt_loop_z_teeth(x, z0, z1, y) {
    inner = TIMING_BELT_BASE_INNER_R;
    run_count = max(0, floor((z1 - z0) / TIMING_PITCH_MM));
    // πR/pitch is exactly 10 for a 20T, 3 mm-pitch pulley.  round() avoids
    // floating-point truncation to 9 teeth at the two half-wraps.
    arc_count = max(1, round(PI * TIMING_PITCH_R / TIMING_PITCH_MM));
    // The drawer-running belt uses the same inner sawtooth profile.  Its
    // long runs are along +Z instead of +X.
    for (i = [0:run_count - 1]) {
        z = z0 + (i + 0.5) * TIMING_PITCH_MM;
        belt_tooth_prism_z(x + inner, z, y, 1);
        belt_tooth_prism_z(x - inner, z, y, -1);
    }
    for (i = [0:arc_count - 1]) {
        top_angle = 0 + (i + 0.5) * 180 / arc_count;
        bottom_angle = 180 + (i + 0.5) * 180 / arc_count;
        belt_tooth_prism_arc(x, z1, y, inner, top_angle);
        belt_tooth_prism_arc(x, z0, y, inner, bottom_angle);
    }
}

module belt_loop_z(x, z0, z1, y) {
    union() {
        belt_loop_z_base(x, z0, z1, y);
        belt_loop_z_teeth(x, z0, z1, y);
    }
}

// Center-cell replacement belt.  The 24 other stations retain the legacy
// 20T / 3 mm timing belt above; this path is a true 2GT / 2 mm / 6 mm belt
// envelope with its own tooth sampling so the old large 3 mm belt is fully
// removed from the migrated station.
module center_gt2_belt_tooth_prism_z(x, z, y, inward) {
    translate([x, y + GT2_BELT_WIDTH / 2, z])
        rotate([0, -90, 0])
            rotate([90, 0, 0])
                linear_extrude(height = GT2_BELT_WIDTH + 2 * EPS)
                    polygon([
                        [-CENTER_GT2_BELT_TOOTH_BASE / 2, -inward * EPS],
                        [ CENTER_GT2_BELT_TOOTH_BASE / 2, -inward * EPS],
                        [ CENTER_GT2_BELT_TOOTH_TIP / 2,
                            inward * CENTER_GT2_BELT_TOOTH_H],
                        [-CENTER_GT2_BELT_TOOTH_TIP / 2,
                            inward * CENTER_GT2_BELT_TOOTH_H]
                    ]);
}

module center_gt2_belt_tooth_prism_arc(
    cx,
    cz,
    y,
    radial_inner,
    angle
) {
    translate([cx, y + GT2_BELT_WIDTH / 2, cz])
        rotate([0, 90 - angle, 0])
            translate([0, 0, radial_inner])
                rotate([90, 0, 0])
                    linear_extrude(height = GT2_BELT_WIDTH + 2 * EPS)
                        polygon([
                            [-CENTER_GT2_BELT_TOOTH_BASE / 2, EPS],
                            [ CENTER_GT2_BELT_TOOTH_BASE / 2, EPS],
                            [ CENTER_GT2_BELT_TOOTH_TIP / 2,
                                -CENTER_GT2_BELT_TOOTH_H],
                            [-CENTER_GT2_BELT_TOOTH_TIP / 2,
                                -CENTER_GT2_BELT_TOOTH_H]
                        ]);
}

module center_gt2_belt_loop_z_base(x, z0, z1, y) {
    inner = CENTER_GT2_BELT_BASE_INNER_R;
    outer = CENTER_GT2_BELT_BASE_OUTER_R;
    translate([0, y + GT2_BELT_WIDTH / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(height = GT2_BELT_WIDTH, convexity = 8)
                difference() {
                    hull() {
                        translate([x, z0]) circle(r = outer);
                        translate([x, z1]) circle(r = outer);
                    }
                    hull() {
                        translate([x, z0]) circle(r = inner);
                        translate([x, z1]) circle(r = inner);
                    }
                }
}

module center_gt2_belt_loop_z_teeth(x, z0, z1, y) {
    inner = CENTER_GT2_BELT_BASE_INNER_R;
    run_count = max(0, floor((z1 - z0) / GT2_PULLEY_PITCH_MM));
    arc_count = max(1,
        round(PI * gt2_pulley_pitch_r() / GT2_PULLEY_PITCH_MM));
    for (i = [0:run_count - 1]) {
        z = z0 + (i + 0.5) * GT2_PULLEY_PITCH_MM;
        center_gt2_belt_tooth_prism_z(x + inner, z, y, 1);
        center_gt2_belt_tooth_prism_z(x - inner, z, y, -1);
    }
    for (i = [0:arc_count - 1]) {
        top_angle = 0 + (i + 0.5) * 180 / arc_count;
        bottom_angle = 180 + (i + 0.5) * 180 / arc_count;
        center_gt2_belt_tooth_prism_arc(
            x,
            z1,
            y,
            inner,
            top_angle
        );
        center_gt2_belt_tooth_prism_arc(
            x,
            z0,
            y,
            inner,
            bottom_angle
        );
    }
}

module center_gt2_belt_loop_z(x, z0, z1, y) {
    union() {
        center_gt2_belt_loop_z_base(x, z0, z1, y);
        center_gt2_belt_loop_z_teeth(x, z0, z1, y);
    }
}

// Two horizontal 2GT loops for the five vertical drawer columns.  The belt
// plane is XZ and its 6 mm axial width is world Y, exactly matching the
// column_gt2_pulley_y() guide stack.
function column_sync_arc_point(cx, cz, radius, tangent, angle) = [
    cx - sin(angle) * tangent + cos(angle) * radius,
    cz + cos(angle) * tangent + sin(angle) * radius
];

module column_sync_belt_tooth_x(x, z, y, inward) {
    translate([0, y + GT2_BELT_WIDTH / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = GT2_BELT_WIDTH + 2 * EPS,
                convexity = 4
            )
                polygon([
                    [x - COLUMN_SYNC_BELT_TOOTH_BASE / 2,
                        z - inward * EPS],
                    [x + COLUMN_SYNC_BELT_TOOTH_BASE / 2,
                        z - inward * EPS],
                    [x + COLUMN_SYNC_BELT_TOOTH_TIP / 2,
                        z + inward * COLUMN_SYNC_BELT_TOOTH_H],
                    [x - COLUMN_SYNC_BELT_TOOTH_TIP / 2,
                        z + inward * COLUMN_SYNC_BELT_TOOTH_H]
                ]);
}

module column_sync_belt_tooth_arc_x(cx, cz, y, angle) {
    inner = COLUMN_SYNC_BELT_BASE_INNER_R;
    translate([0, y + GT2_BELT_WIDTH / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = GT2_BELT_WIDTH + 2 * EPS,
                convexity = 4
            )
                polygon([
                    column_sync_arc_point(
                        cx,
                        cz,
                        inner + EPS,
                        -COLUMN_SYNC_BELT_TOOTH_BASE / 2,
                        angle
                    ),
                    column_sync_arc_point(
                        cx,
                        cz,
                        inner + EPS,
                        COLUMN_SYNC_BELT_TOOTH_BASE / 2,
                        angle
                    ),
                    column_sync_arc_point(
                        cx,
                        cz,
                        inner - COLUMN_SYNC_BELT_TOOTH_H,
                        COLUMN_SYNC_BELT_TOOTH_TIP / 2,
                        angle
                    ),
                    column_sync_arc_point(
                        cx,
                        cz,
                        inner - COLUMN_SYNC_BELT_TOOTH_H,
                        -COLUMN_SYNC_BELT_TOOTH_TIP / 2,
                        angle
                    )
                ]);
}

module column_sync_belt_loop_x_base(x0, x1, y, z) {
    inner = COLUMN_SYNC_BELT_BASE_INNER_R;
    outer = COLUMN_SYNC_BELT_BASE_OUTER_R;
    translate([0, y + GT2_BELT_WIDTH / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = GT2_BELT_WIDTH,
                convexity = 8
            )
                difference() {
                    hull() {
                        translate([x0, z]) circle(r = outer);
                        translate([x1, z]) circle(r = outer);
                    }
                    hull() {
                        translate([x0, z]) circle(r = inner);
                        translate([x1, z]) circle(r = inner);
                    }
                }
}

module column_sync_belt_loop_x_teeth(x0, x1, y, z) {
    inner = COLUMN_SYNC_BELT_BASE_INNER_R;
    run_count = max(0, round((x1 - x0) / GT2_PULLEY_PITCH_MM));
    arc_count = max(1,
        round(PI * GT2_PULLEY_TEETH * GT2_PULLEY_PITCH_MM
            / (2 * PI) / GT2_PULLEY_PITCH_MM));
    // The default 20.4→234.4 span is 107 pitches. Together with six teeth on
    // each half-wrap this is exactly 226 teeth around the closed belt.
    for (i = [0:run_count - 1]) {
        x = x0 + (i + 0.5) * GT2_PULLEY_PITCH_MM;
        column_sync_belt_tooth_x(x, z - inner, y, 1);
        column_sync_belt_tooth_x(x, z + inner, y, -1);
    }
    for (i = [0:arc_count - 1]) {
        right_angle = -90 + (i + 0.5) * 180 / arc_count;
        left_angle = 90 + (i + 0.5) * 180 / arc_count;
        column_sync_belt_tooth_arc_x(x1, z, y, right_angle);
        column_sync_belt_tooth_arc_x(x0, z, y, left_angle);
    }
}

module column_sync_belt_loop_x(x0, x1, y, z) {
    assert(x1 > x0, "column sync belt endpoints must run from -X to +X");
    union() {
        column_sync_belt_loop_x_base(x0, x1, y, z);
        column_sync_belt_loop_x_teeth(x0, x1, y, z);
    }
}
//#endregion

//#region 私有成员：齿杆、齿条和弹簧
module vertical_gear_rack(x, z) {
    // This is no longer the old flat rack placeholder.  The authored
    // long_gear_shaft is centered between the two bus pulley datums: its
    // continuous Y-directed spline teeth mesh with each axis-Z clutch spur,
    // while its integral D stubs carry the top and bottom timing pulleys.
    translate([x, (BUS_BOTTOM_Y + BUS_TOP_Y) / 2, z])
        color(COLOR_RACK)
            long_gear_shaft_solid_param(
                VERTICAL_GEAR_TEETH,
                VERTICAL_GEAR_PITCH_MM,
                VERTICAL_GEAR_TOOTH_DEPTH,
                VERTICAL_GEAR_TIP_START,
                VERTICAL_GEAR_TIP_END,
                VERTICAL_GEAR_ROOT_END,
                VERTICAL_GEAR_LENGTH,
                VERTICAL_GEAR_END_STUB_LENGTH,
                VERTICAL_GEAR_STUB_OVERLAP,
                ROD_D,
                ROD_FLAT_DEPTH
            );
}

module vertical_gear_column(x, z) {
    // One real Y-directed long spline gear shaft per drawer column.  The
    // shaft already contains both end D stubs; do not add a second coaxial
    // round/D rod that would hide the authored geometry. The column pulley is
    // the same finished 12T/2GT body used by the migrated center drive; its
    // two guide planes are the only larger-than-tooth-radius features.
    vertical_gear_rack(x, z);
    for (axis_y = [BUS_BOTTOM_Y, BUS_TOP_Y])
        color(COLOR_TIMING)
            column_gt2_pulley_y(x, axis_y, z, "d");
}

module horizontal_drawer_rack(x, z0, z1, y) {
    length = z1 - z0;
    rack_face_x = x + FRONT_GEAR_PITCH_R + 0.15;
    rack_body_y = y - 1.9;
    color(COLOR_RACK) {
        // The rack runs in world +Z below each drawer. Its tooth height is
        // radial in X, so the +Y-axis pinion can mesh with it.
        translate([rack_face_x, rack_body_y, z0])
            cube([3.2, 3.8, length]);
        for (rack_z = [z0 + DRAWER_RACK_PITCH / 2:DRAWER_RACK_PITCH:z1 - DRAWER_RACK_PITCH / 2])
            translate([
                rack_face_x - DRAWER_RACK_TOOTH_H,
                rack_body_y + 0.25,
                rack_z - 0.42
            ])
                cube([DRAWER_RACK_TOOTH_H + 0.20, 3.3, 0.84]);
    }
}

module compression_spring_y(x, y0, y1, z) {
    h = max(CLUTCH_SPRING_MIN_H, y1 - y0);
    translate([x, y0, z])
        rotate([-90, 0, 0])
            linear_extrude(
                height = h,
                twist = 360 * CLUTCH_SPRING_TURNS,
                slices = max(24, CLUTCH_SPRING_TURNS * 12),
                convexity = 4
            )
                translate([CLUTCH_SPRING_OD / 2 - CLUTCH_SPRING_WIRE_D / 2, 0])
                    circle(d = CLUTCH_SPRING_WIRE_D);
}

module t_countersunk_screw_y(x, z, top_y) {
    head_bottom = top_y - CLUTCH_SCREW_HEAD_H;
    color("#707985")
        difference() {
            union() {
                cylinder_y(
                    x,
                    head_bottom - CLUTCH_SCREW_SHAFT_L,
                    z,
                    CLUTCH_SCREW_D,
                    CLUTCH_SCREW_SHAFT_L
                );
                // The head is a flat-topped countersink: narrow at the lower
                // face and full diameter at the top face.
                translate([x, head_bottom, z])
                    rotate([-90, 0, 0])
                        cylinder(
                            d1 = CLUTCH_SCREW_D + 0.30,
                            d2 = CLUTCH_SCREW_HEAD_D,
                            h = CLUTCH_SCREW_HEAD_H
                        );
            }
            // Recess the T driver slot instead of adding a misleading raised
            // cross. The shallow cut remains visible in the assembly preview.
            translate([x - 1.8, top_y - 0.42, z - 0.35])
                cube([3.6, 0.50, 0.70]);
            translate([x - 0.35, top_y - 0.42, z - 1.8])
                cube([0.70, 0.50, 3.6]);
        }
}
//#endregion

//#region 公开 API：柜体与动力母线
module tensioner_main_parametric() {
    // The native SKP main group is a base slab plus an upper rail.  The two
    // side pockets are cut separately because their openings differ by 1 mm.
    difference() {
        union() {
            tensioner_native_box(
                TENSIONER_MAIN_BASE_X0,
                TENSIONER_MAIN_BASE_Y0,
                TENSIONER_MAIN_BASE_Z0,
                TENSIONER_MAIN_BASE_DX,
                TENSIONER_MAIN_BASE_DY,
                TENSIONER_MAIN_BASE_DZ
            );
            tensioner_native_box(
                TENSIONER_MAIN_UPPER_X0,
                TENSIONER_MAIN_UPPER_Y0,
                TENSIONER_MAIN_UPPER_Z0,
                TENSIONER_MAIN_UPPER_DX,
                TENSIONER_MAIN_UPPER_DY,
                TENSIONER_MAIN_UPPER_DZ
            );
        }

        tensioner_native_box(
            TENSIONER_MAIN_LEFT_SLOT_X0,
            TENSIONER_MAIN_LEFT_SLOT_Y0,
            TENSIONER_MAIN_LEFT_SLOT_Z0,
            TENSIONER_MAIN_LEFT_SLOT_DX,
            TENSIONER_MAIN_LEFT_SLOT_DY,
            TENSIONER_MAIN_LEFT_SLOT_DZ
        );
        tensioner_native_box(
            TENSIONER_MAIN_RIGHT_SLOT_X0,
            TENSIONER_MAIN_RIGHT_SLOT_Y0,
            TENSIONER_MAIN_RIGHT_SLOT_Z0,
            TENSIONER_MAIN_RIGHT_SLOT_DX,
            TENSIONER_MAIN_RIGHT_SLOT_DY,
            TENSIONER_MAIN_RIGHT_SLOT_DZ
        );

        // Small native-green blind bore: native Y 1.5→3.0, Ø2.
        tensioner_native_axis_y_cylinder(
            TENSIONER_MAIN_SMALL_BORE_X,
            TENSIONER_MAIN_SMALL_BORE_Y0,
            TENSIONER_MAIN_SMALL_BORE_Z,
            TENSIONER_MAIN_SMALL_BORE_D,
            TENSIONER_MAIN_SMALL_BORE_L + EPS
        );

        // Large native-green through bore: native Y 32→42, Ø4.
        tensioner_native_axis_y_cylinder(
            TENSIONER_MAIN_LARGE_BORE_X,
            TENSIONER_MAIN_LARGE_BORE_Y0 - EPS,
            TENSIONER_MAIN_LARGE_BORE_Z,
            TENSIONER_MAIN_LARGE_BORE_D,
            TENSIONER_MAIN_LARGE_BORE_L + 2 * EPS
        );
    }
}

module tensioner_ring_parametric() {
    tensioner_native_annular_plate(
        TENSIONER_RING_X0,
        TENSIONER_RING_Y0 + TENSIONER_RING_DY / 2,
        TENSIONER_RING_Z0 + TENSIONER_RING_DZ / 2,
        TENSIONER_RING_DX,
        TENSIONER_RING_OUTER_D,
        TENSIONER_RING_INNER_D
    );
}

module tensioner_plate_parametric() {
    difference() {
        tensioner_native_box(
            TENSIONER_PLATE_X0,
            TENSIONER_PLATE_Y0,
            TENSIONER_PLATE_Z0,
            TENSIONER_PLATE_DX,
            TENSIONER_PLATE_DY,
            TENSIONER_PLATE_DZ
        );

        // Axis-red through bore: native X, Ø10, across the 3 mm plate.
        tensioner_native_axis_x_cylinder(
            TENSIONER_PLATE_X0 - EPS,
            TENSIONER_PLATE_Y0 + TENSIONER_PLATE_DY / 2,
            TENSIONER_PLATE_Z0 + TENSIONER_PLATE_DZ / 2,
            TENSIONER_PLATE_BORE_D,
            TENSIONER_PLATE_DX + 2 * EPS
        );

        // Axis-green blind bore: native local Y -1→1.5, Ø2.
        tensioner_native_axis_y_cylinder(
            TENSIONER_PLATE_X0 + TENSIONER_PLATE_SMALL_BORE_LOCAL_X,
            TENSIONER_PLATE_Y0
                + TENSIONER_PLATE_SMALL_BORE_LOCAL_Y0
                - EPS,
            TENSIONER_PLATE_Z0 + TENSIONER_PLATE_SMALL_BORE_LOCAL_Z,
            TENSIONER_PLATE_SMALL_BORE_D,
            TENSIONER_PLATE_SMALL_BORE_L + 2 * EPS
        );
    }
}

module tensioner_skp_parametric() {
    // Align the mapped native envelope with the existing rear/low-X datum.
    // The translation is placement only; all shape dimensions remain editable
    // in the parameter block above.
    color(COLOR_TENSIONER_T_SOLID)
        translate([
            TENSIONER_PARAM_WORLD_ORIGIN_X,
            TENSIONER_PARAM_WORLD_ORIGIN_Y,
            TENSIONER_PARAM_WORLD_ORIGIN_Z
        ]) {
            tensioner_main_parametric();
            tensioner_ring_parametric();
            tensioner_plate_parametric();
        }
}

// Keep the existing part selector name stable for the exporter and viewer.
// It now resolves to the editable reconstruction, not an imported mesh.
module tensioner_t_solid() {
    tensioner_skp_parametric();
}

module world_partition_plate() {
    translate([0, 0, WORLD_PARTITION_BACK_Z])
        cube([W, H, WORLD_PARTITION_T]);
}

module world_bay_grid() {
    for (i = [1:N_COL - 1])
        translate([world_col_x(i) - WORLD_DIV_T, WORLD_GRID_ORIGIN_Y, WORLD_PARTITION_FRONT_Z])
            cube([WORLD_DIV_T, WORLD_GRID_H + EPS, -WORLD_PARTITION_FRONT_Z + EPS]);
    for (j = [1:N_ROW - 1])
        translate([WORLD_GRID_ORIGIN_X, world_row_y(j) - WORLD_SHELF_T, WORLD_PARTITION_FRONT_Z])
            cube([WORLD_GRID_W + EPS, WORLD_SHELF_T, -WORLD_PARTITION_FRONT_Z + EPS]);
    translate([WORLD_GRID_ORIGIN_X, WORLD_GRID_ORIGIN_Y - WORLD_SHELF_T, WORLD_PARTITION_FRONT_Z])
        cube([WORLD_GRID_W + EPS, WORLD_SHELF_T, -WORLD_PARTITION_FRONT_Z + EPS]);
}

module world_front_service_cheek() {
    translate([WALL - EPS, WORLD_GRID_ORIGIN_Y, WORLD_PARTITION_FRONT_Z])
        cube([SERVICE_W + EPS, WORLD_GRID_H + EPS, -WORLD_PARTITION_FRONT_Z + EPS]);
}

module world_drawer_ghosts() {
    drawer_depth = -WORLD_PARTITION_FRONT_Z - 0.6;
    for (i = [0:N_COL - 1], j = [0:N_ROW - 1])
        translate([
            world_col_x(i) + DRAWER_CLEAR,
            world_row_y(j) + DRAWER_CLEAR,
            WORLD_PARTITION_FRONT_Z + 0.4
        ])
            cube([
                world_drawer_outer_w(),
                world_drawer_outer_h(),
                drawer_depth
            ]);
}

module snake_motor_mount_bosses() {
    // Reuse the same continuous base rails, solid guide posts, and top-open
    // blind pilots as the printable cabinet.  R_x(-90) maps local
    // [x, depth, height] to native [x, -depth, height].
    rotate([-90, 0, 0])
        cabinet_motor_mount_floor_seats_local();
}

module snake_motor_mount_boss_floor_bores() {
    // These are top-open, blind M3 pilots in the posts, not through-bores in
    // the cabinet floor.  The native transform keeps the screw axis vertical.
    rotate([-90, 0, 0])
        cabinet_motor_mount_floor_pilot_holes_local();
}

module clutch_cabinet_shell() {
    // Closed thin-wall world shell. The front face is 0 and the back face is -Z;
    // the vertical dimension is +Y. Bosses are added after the cavity cut so
    // their second-stage guides remain inside the rear-cavity volume.
    difference() {
        union() {
            difference() {
                translate([0, 0, -D])
                    cube([W, H, D]);
                translate([WALL, WALL, -D + WALL])
                    cube([W - 2 * WALL, H - 2 * WALL, D - 2 * WALL]);
            }
            snake_motor_mount_bosses();
            // The internal partition is the load-bearing datum for the
            // removable center mechanism plate. It is separate from the thin
            // rear cover and contains the belt passages plus plate support
            // slots/holes.
            clutch_partition_with_belt_passages();
        }
        snake_motor_mount_boss_floor_bores();
    }
}

module clutch_assembly_shell_context() {
    // Do not use a transparent difference() or broad wall panels here.
    // OpenSCAD triangulates transparent faces into large fan faces, which makes
    // the inspection image look like the mechanism is inside broken glass. A
    // wire-frame cabinet datum is enough to show the front/back orientation;
    // the printable cabinet entry above remains a separate closed shell.
    union() {
        for (x = [0, W - WALL])
            for (z = [-WALL, -D])
                translate([x, 0, z])
                    cube([WALL, H, WALL]);
        for (x = [0, W - WALL])
            for (y = [0, H - WALL])
                translate([x, y, -D])
                    cube([WALL, WALL, D]);
        for (z = [-WALL, -D])
            for (y = [0, H - WALL])
                translate([0, y, z])
                    cube([W, WALL, WALL]);
    }
}

module clutch_partition_with_belt_passages() {
    difference() {
        world_partition_plate();
        center_clutch_partition_support_cuts(
            CENTER_GT2_COL,
            CENTER_GT2_ROW
        );
        for (row = [0:N_ROW - 1])
            for (col = [0:N_COL - 1]) {
                station_belt_t = is_center_gt2_station(col, row)
                    ? CENTER_GT2_BELT_T
                    : TIMING_BELT_T;
                station_passage_half_x = is_center_gt2_station(col, row)
                    ? CENTER_GT2_BELT_BASE_OUTER_R
                        + GT2_BELT_RADIAL_CLEARANCE + 0.45
                    : TIMING_BELT_BASE_OUTER_R
                        + TIMING_BELT_CLEAR + 0.45;
                translate([
                    clutch_col_x(col) - station_passage_half_x,
                    drawer_station_belt_y(col, row)
                        - station_belt_t / 2 - 0.45,
                    WORLD_PARTITION_BACK_Z - EPS
                ])
                    cube([
                        2 * station_passage_half_x,
                        station_belt_t + 0.90,
                        WORLD_PARTITION_T + 2 * EPS
                    ]);
            }
    }
}

module clutch_cabinet_context(include_drawers = true) {
    color(COLOR_CABINET, 0.38) clutch_assembly_shell_context();
    color(COLOR_CABINET, 0.72) {
        // Keep the partition as datum rails in the preview. The full
        // perforated partition is a printable cabinet feature, but its
        // transparent boolean face is not useful for visual inspection.
        world_bay_grid();
        world_front_service_cheek();
    }
    if (include_drawers)
        color(COLOR_DRAWER, 0.22) world_drawer_ghosts();
}

module power_motor_vertical() {
    power_motor_body();
    power_motor_shaft();
}

module power_motor_body() {
    // The purchased motor's local +Z output is rotated onto world +Y. It is
    // mounted directly beneath the +X-most drawer column; that column already
    // supplies the continuous Y-directed gear shaft and its lower D stub.
    translate([MOTOR_X, MOTOR_FACE_Y, DRIVE_AXIS_Z])
        rotate([-90, 0, 0])
            pololu_micro_metal_motor_100_1_hp_6v_body_colored();
}

module power_motor_shaft() {
    translate([MOTOR_X, MOTOR_FACE_Y, DRIVE_AXIS_Z])
        rotate([-90, 0, 0])
            color("#d6d9dc") d_shaft();
}

module left_d_axis() {
    // Rear-view-left boundary axis: the rod has a D flat and both bus pulleys
    // have matching D bores. The motor output shaft overlaps its lower end.
    color(COLOR_SHAFT)
        d_rod_y(MOTOR_X, LEFT_D_AXIS_Y0, DRIVE_AXIS_Z, ROD_TOP_Y - LEFT_D_AXIS_Y0);
    for (axis_y = [BUS_BOTTOM_Y, BUS_TOP_Y])
        color(COLOR_TIMING)
            column_gt2_pulley_y(MOTOR_X, axis_y, DRIVE_AXIS_Z, "d");
}

module side_axes() {
    left_d_axis();
}

module all_vertical_axes() {
    // Exactly five drawer columns. The +X-most column shares its lower D stub
    // with the motor output; no separate D-drive column is inserted.
    power_motor_vertical();
    for (i = [0:N_COL - 1])
        vertical_gear_column(clutch_col_x(i), DRIVE_AXIS_Z);
}

module power_column_sync_belts() {
    // Both belts are the same 226T/2GT loop, one at each end of every Y-axis
    // column.  The intermediate pulleys sit on the two tangent runs, so all
    // five shafts are mechanically represented on the same closed path.
    color(COLOR_BELT, 0.18) {
        column_sync_belt_loop_x(
            COLUMN_SYNC_TENSIONER_X,
            MOTOR_X,
            BUS_BOTTOM_Y,
            DRIVE_AXIS_Z
        );
        column_sync_belt_loop_x(
            COLUMN_SYNC_TENSIONER_X,
            MOTOR_X,
            BUS_TOP_Y,
            DRIVE_AXIS_Z
        );
    }
}

module column_sync_tensioner_wheels() {
    // The bearing/slide body is static; this shaft and its two 2GT wheels are
    // the moving part.  Positive VERTICAL_TENSIONER_OFFSET_X moves this whole
    // set toward world -X, increasing the belt centre distance.
    color(COLOR_SHAFT)
        cylinder_y(
            COLUMN_SYNC_TENSIONER_X,
            BUS_BOTTOM_Y - 5.0,
            DRIVE_AXIS_Z,
            ROD_D,
            BUS_TOP_Y - BUS_BOTTOM_Y + 10.0
        );
    for (axis_y = [BUS_BOTTOM_Y, BUS_TOP_Y])
        color(COLOR_TIMING)
            column_gt2_pulley_y(
                COLUMN_SYNC_TENSIONER_X,
                axis_y,
                DRIVE_AXIS_Z,
                "round"
            );
}

module column_sync_tensioner() {
    tensioner_t_solid();
    column_sync_tensioner_wheels();
}

module power_bus() {
    // The motor is on the +X-most drawer column. Both horizontal 2GT loops
    // couple all five columns to that motor; the low-X wheel is the adjustable
    // return/tension point and is not an extra drawer column.
    all_vertical_axes();
    power_column_sync_belts();
    column_sync_tensioner();
}
//#endregion

// The center prototype is deliberately split into a removable mechanism plate,
// fixed output cage, captured rails, moving input carriage, hard stops and
// purchased-part references. Keeping this include after the world-coordinate
// helpers makes the carrier consume the same station datums as the rotors.
include <cabinet_clutch_carrier.scad>

//#region 公开 API：离合与抽屉取力
module clutch_upper_carrier(col, row, engaged = false, include_screw = false) {
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    upper_y = clutch_upper_y(row, engaged);
    upper_dog_y = clutch_upper_dog_y(row, engaged);

    // Axis-Z upper gear: its teeth stay in the vertical (+Y) rack. A short
    // carrier stem links this wheel to the downward dog face.
    color(COLOR_GEAR)
        spur_gear_z(
            x,
            upper_y,
            z,
            CLUTCH_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            CLUTCH_GEAR_TOOTH_DEPTH,
            CLUTCH_GEAR_T,
            ROD_D + 2 * ROD_CLEARANCE
        );
    color(COLOR_DOG)
        dog_face_y(x, upper_dog_y, z, CLUTCH_DOG_TEETH, false);
    color(COLOR_SHAFT)
        cylinder_y(
            x,
            upper_dog_y + CLUTCH_DOG_T / 2,
            z,
            CLUTCH_HUB_D,
            CLUTCH_CARRIER_STEM_H
        );

    if (include_screw)
        t_countersunk_screw_y(x, z, clutch_screw_top_y(row, engaged));
}

module clutch_lower_takeoff(col, row) {
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    fixed_y = clutch_fixed_dog_y(row);
    takeoff_pulley_y = clutch_takeoff_pulley_y(row);

    // Fixed lower dog presents its teeth upward. The timing pulley is a second
    // coaxial layer below it; both layers are on the same vertical (+Y) axis.
    color(COLOR_DOG)
        dog_face_y(x, fixed_y, z, CLUTCH_DOG_TEETH, true);
    color(COLOR_TIMING)
        timing_pulley_y(x, takeoff_pulley_y, z, TIMING_TEETH, "round");
    color(COLOR_SHAFT)
        cylinder_y(
            x,
            takeoff_pulley_y - TIMING_PULLEY_W / 2 - 0.25,
            z,
            ROD_D,
            fixed_y - takeoff_pulley_y
                    + CLUTCH_DOG_T / 2 + TIMING_PULLEY_W / 2 + 0.50
        );
}

module clutch_spring_only(col, row, engaged = false) {
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    fixed_y = clutch_fixed_dog_y(row);
    upper_dog_y = clutch_upper_dog_y(row, engaged);
    spring_bottom = fixed_y + CLUTCH_DOG_T / 2 + 0.30;
    spring_open_top = upper_dog_y - CLUTCH_DOG_T / 2 - 0.30;
    spring_top = engaged ? spring_bottom + CLUTCH_SPRING_MIN_H : spring_open_top;

    color(COLOR_SPRING)
        compression_spring_y(x, spring_bottom, spring_top, z);
}

module clutch_spring_and_screw(col, row, engaged = false) {
    clutch_spring_only(col, row, engaged);
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    t_countersunk_screw_y(x, z, clutch_screw_top_y(row, engaged));
}

module clutch_station(col, row, engaged = false, detail = false) {
    clutch_upper_carrier(col, row, engaged, false);
    clutch_lower_takeoff(col, row);
    clutch_spring_and_screw(col, row, engaged);

    if (detail)
        color(COLOR_FORK, 0.12)
            clutch_fork(col, row, engaged);
}

// Finished CH1 03C pair embedded in the cabinet's center cell. The input male
// child is below and moves along +Y into the fixed output female mother above.
// Both bodies use the same +Z-shifted parallel axis, while the existing long
// shaft stays on the original axis at DRIVE_AXIS_Z and drives the input gear
// tangentially. The carrier keeps the output rotor fixed in Y and carries the
// input rotor, its D shaft and its bearings as one moving service assembly.
module center_gt2_male(col, row, engaged = false) {
    x = clutch_col_x(col);
    z = center_gt2_z();
    // The explicit travel override is intentionally shared by the rotor,
    // carriage, shafts and bearings.  Using the boolean only here would make
    // an intermediate CSG sample look stationary while the carrier moved.
    insertion_shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#e2a84b")
        translate([
            x,
            center_gt2_male_base_y(row) + insertion_shift,
            z
        ])
            rotate([-90, 0, 0])
                male_local();
}

module center_gt2_female(col, row) {
    x = clutch_col_x(col);
    z = center_gt2_z();
    color("#5d7885")
        translate([x, center_gt2_female_base_y(row), z])
            rotate([90, 0, 0])
                female_local();
}

module center_gt2_clutch(col, row, engaged = false) {
    center_clutch_carrier(col, row, engaged, true);
    center_gt2_female(col, row);
    center_gt2_male(col, row, engaged);
}

module all_clutches() {
    center_station_engaged =
        ENGAGED
            && CENTER_GT2_COL == selected_col()
            && CENTER_GT2_ROW == selected_row();
    center_gt2_clutch(CENTER_GT2_COL, CENTER_GT2_ROW, center_station_engaged);

    // The old 24 stations stay available behind an explicit review switch,
    // but are intentionally absent from the default physical-validation view.
    if (SHOW_LEGACY_STATIONS)
        for (row = [0:N_ROW - 1])
            for (col = [0:N_COL - 1])
                if (!is_center_gt2_station(col, row))
                    clutch_station(
                        col,
                        row,
                        ENGAGED && col == selected_col() && row == selected_row(),
                        false
                    );
}

module clutch_fork(col, row, engaged = false) {
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    upper_gear_top = clutch_upper_y(row, engaged) + CLUTCH_GEAR_OUTER_R;
    y = upper_gear_top + (engaged ? FORK_CONTACT : FORK_CLEAR_OPEN);
    // The fork is a U-shaped pressure shoe with its opening around the rod.
    color(COLOR_FORK)
        translate([x - FORK_W / 2, y, z - FORK_D / 2])
            difference() {
                cube([FORK_W, FORK_T, FORK_D]);
                translate([FORK_W / 2 - 2.0, -EPS, -EPS])
                    cube([4.0, FORK_T + 2 * EPS, FORK_D + 2 * EPS]);
            }
}

module drawer_front_compound(col, row) {
    x = clutch_col_x(col);
    front_z = FRONT_PULLEY_Z;
    belt_y = drawer_belt_y(row);
    gear_y = drawer_front_gear_y(row);
    color(COLOR_TIMING)
        timing_pulley_y(x, belt_y, front_z, TIMING_TEETH, "round");
    // The upper, larger gear is the pinion that contacts the rack below the drawer.
    color(COLOR_GEAR)
        spur_gear_y(
            x,
            gear_y,
            front_z,
            FRONT_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            FRONT_GEAR_TOOTH_DEPTH,
            FRONT_GEAR_T
        );
    color(COLOR_SHAFT)
        cylinder_y(
            x,
            belt_y - TIMING_PULLEY_W / 2 - 0.25,
            front_z,
            CLUTCH_HUB_D,
            gear_y - belt_y
                + TIMING_PULLEY_W / 2
                + FRONT_GEAR_T / 2
                + 0.50
        );
}

module drawer_front_drive(col, row) {
    x = clutch_col_x(col);
    belt_y = drawer_belt_y(row);
    color(COLOR_BELT, 0.14)
        belt_loop_z(x, DRIVE_AXIS_Z, FRONT_PULLEY_Z, belt_y);
    drawer_front_compound(col, row);
    horizontal_drawer_rack(
        x,
        WORLD_PARTITION_FRONT_Z + 1.5,
        FRONT_PULLEY_Z - 3.5,
        drawer_front_gear_y(row)
    );
}

module center_gt2_front_pulley_y(x, belt_y, z) {
    base_y = center_gt2_pulley_base_y(belt_y);
    color(COLOR_TIMING)
        translate([x, base_y, z])
            rotate([-90, 0, 0])
                difference() {
                    gt2_pulley_local();
                    translate([0, 0, -GT2_EPS])
                        cylinder(
                            d = ROUND_BORE_D,
                            h = GT2_BELT_LOWER_RETAINER_T
                                + GT2_PULLEY_FACE_T
                                + GT2_BELT_GUIDE_LIP_T
                                + 2 * GT2_EPS
                        );
                }
}

module center_gt2_front_compound(col, row) {
    x = clutch_col_x(col);
    front_z = CENTER_GT2_FRONT_PULLEY_Z;
    belt_y = center_gt2_belt_y(row);
    gear_y = center_gt2_front_gear_y(row);
    pulley_base_y = center_gt2_pulley_base_y(belt_y);
    gear_bottom_y = gear_y - FRONT_GEAR_T / 2;

    center_gt2_front_pulley_y(x, belt_y, front_z);
    // The front output remains the deliberately coarse rack pinion.  Only its
    // lower timing wheel changes to the standard 2GT profile and 6 mm belt.
    color(COLOR_GEAR)
        spur_gear_y(
            x,
            gear_y,
            front_z,
            FRONT_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            FRONT_GEAR_TOOTH_DEPTH,
            FRONT_GEAR_T,
            ROUND_BORE_D
        );
    color(COLOR_SHAFT)
        cylinder_y(
            x,
            pulley_base_y - 0.25,
            front_z,
            CLUTCH_HUB_D,
            gear_bottom_y - pulley_base_y + 0.50
        );
}

module center_gt2_drawer_drive(col, row) {
    x = clutch_col_x(col);
    belt_y = center_gt2_belt_y(row);
    color(COLOR_BELT, 0.18)
        center_gt2_belt_loop_z(
            x,
            center_gt2_z(),
            CENTER_GT2_FRONT_PULLEY_Z,
            belt_y
        );
    center_gt2_front_compound(col, row);
    horizontal_drawer_rack(
        x,
        WORLD_PARTITION_FRONT_Z + 1.5,
        CENTER_GT2_FRONT_PULLEY_Z - 3.5,
        center_gt2_front_gear_y(row)
    );
}

module drawer_drive() {
    center_gt2_drawer_drive(CENTER_GT2_COL, CENTER_GT2_ROW);
    if (SHOW_LEGACY_STATIONS)
        for (row = [0:N_ROW - 1])
            for (col = [0:N_COL - 1])
                if (!is_center_gt2_station(col, row)) {
                    clutch_lower_takeoff(col, row);
                    drawer_front_drive(col, row);
                }
}

// 单件检查入口。它们都使用同一组装坐标，便于把检查过的零件直接放回总装。
module selected_column_part() {
    vertical_gear_column(clutch_col_x(selected_col()), DRIVE_AXIS_Z);
}

module selected_left_d_axis_part() {
    left_d_axis();
}

module selected_power_motor_body_part() {
    power_motor_body();
}

module selected_power_motor_shaft_part() {
    power_motor_shaft();
}

module selected_column_sync_belt_bottom_part() {
    color(COLOR_BELT, 0.18)
        column_sync_belt_loop_x(
            COLUMN_SYNC_TENSIONER_X,
            MOTOR_X,
            BUS_BOTTOM_Y,
            DRIVE_AXIS_Z
        );
}

module selected_column_sync_belt_top_part() {
    color(COLOR_BELT, 0.18)
        column_sync_belt_loop_x(
            COLUMN_SYNC_TENSIONER_X,
            MOTOR_X,
            BUS_TOP_Y,
            DRIVE_AXIS_Z
        );
}

module selected_column_sync_tensioner_part() {
    column_sync_tensioner_wheels();
}

module selected_vertical_rack_part() {
    vertical_gear_rack(clutch_col_x(selected_col()), DRIVE_AXIS_Z);
}

module selected_tensioner_t_solid_part() {
    tensioner_t_solid();
}

// Center-station exports. These are intentionally named by mechanical role,
// not by the retired upper/lower candidate convention, so the preview tree
// cannot silently swap input and output again.
module selected_center_input_rotor_part() {
    center_gt2_male(CENTER_GT2_COL, CENTER_GT2_ROW, ENGAGED);
}

module selected_center_output_rotor_part() {
    center_gt2_female(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_input_carriage_part() {
    center_clutch_input_carriage(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_output_cage_part() {
    center_clutch_output_cage(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_guide_rails_part() {
    center_clutch_guide_rails(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_linear_bearings_part() {
    center_clutch_linear_bearings(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_linear_bearing_retainers_part() {
    center_clutch_linear_bearing_retainers(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_linear_bearing_fit_coupon_part() {
    center_clutch_linear_bearing_fit_coupon();
}

module selected_center_stops_part() {
    center_clutch_stops(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_mechanism_plate_part() {
    center_clutch_mechanism_plate(CENTER_GT2_COL, CENTER_GT2_ROW);
}

// Collision witness for the first-article audit. The service plate sits in
// the rear-to-front belt span, so this must export as an empty intersection
// after the plate's real through-passage is cut. It is diagnostic only and is
// never included in the default manifest.
module selected_center_plate_belt_collision_part() {
    intersection() {
        center_clutch_mechanism_plate(CENTER_GT2_COL, CENTER_GT2_ROW);
        center_gt2_belt_loop_z(
            clutch_col_x(CENTER_GT2_COL),
            center_gt2_z(),
            CENTER_GT2_FRONT_PULLEY_Z,
            center_gt2_belt_y(CENTER_GT2_ROW)
        );
    }
}

// These actual CSG intersections are exported only by the geometry gate. An
// empty result is the required witness: the pair may contact through its
// designed tooth envelope, while the carriage/rail and shoe/rail interfaces
// must retain real clearance throughout the open and engaged datums.
module selected_center_clutch_pair_collision_part() {
    intersection() {
        center_gt2_male(CENTER_GT2_COL, CENTER_GT2_ROW, ENGAGED);
        center_gt2_female(CENTER_GT2_COL, CENTER_GT2_ROW);
    }
}

module selected_center_selector_rail_collision_part() {
    intersection() {
        center_clutch_guide_rails(CENTER_GT2_COL, CENTER_GT2_ROW);
        selected_center_selector_shoe_part();
    }
}

// The selector shoe is a single printed part with a narrow support arm. The
// arm intentionally leaves the magnetic shoe at the rotor's lower face while
// reaching to the existing snake-chain plane at -Z; this is the mechanical
// bridge that the old free-floating browser mesh did not contain.
module center_clutch_selector_support_arm() {
    x = CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM
        + CENTER_SELECTOR_SHOE_SUPPORT_ARM_X_OFFSET_MM;
    shoe_front_z = CENTER_SELECTOR_SHOE_Z_MM
        + CENTER_SELECTOR_SHOE_D / 2;
    bridge_z0 = shoe_front_z
        - CENTER_SELECTOR_SHOE_SUPPORT_BRIDGE_OVERLAP_MM;
    bridge_z1 = CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM
        + CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T / 2;
    support_y0 = CENTER_SELECTOR_SHOE_TARGET_Y_MM
        - CENTER_SELECTOR_SHOE_SUPPORT_Y_T / 2;
    support_y1 = CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM
        + CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Y_OVERHANG_MM;
    color("#92a4b0")
        union() {
            // Depth bridge: overlap the shoe body by 0.30 mm and terminate
            // inside the chain-plane support arm.
            translate([
                x - CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM / 2,
                support_y0,
                min(bridge_z0, bridge_z1)
            ])
                cube([
                    CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM,
                    CENTER_SELECTOR_SHOE_SUPPORT_Y_T,
                    abs(bridge_z1 - bridge_z0)
                ]);
            // Vertical-in-Y drop: the chain link/roller bracket sees the
            // support through its center datum rather than relying on gravity.
            translate([
                x - CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM / 2,
                support_y0,
                CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM
                    - CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T / 2
            ])
                cube([
                    CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM,
                    support_y1 - support_y0,
                    CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T
                ]);
        }
}

// Positive CSG witness for the chain-supported selector shoe.  This is not a
// collision test: the sphere is a small inspection volume centered on the
// authored chain pin datum and must intersect the printed support arm with a
// positive volume.  It is exported only by the geometry validator.
module center_selector_chain_contact_reference() {
    translate([
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM,
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM,
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM
    ])
        sphere(d = CENTER_SELECTOR_SHOE_CHAIN_CONTACT_D_MM, $fn = 48);
}

module selected_center_selector_chain_support_contact_part() {
    intersection() {
        selected_center_selector_shoe_part();
        center_selector_chain_contact_reference();
    }
}

// Empty CSG witness used by the center first-article sweep. It is intentionally
// separate from the selector/rail witness so the trigger gap is checked as a
// real solid intersection at both travel endpoints.
module selected_center_selector_male_collision_part() {
    intersection() {
        selected_center_selector_shoe_part();
        center_gt2_male(CENTER_GT2_COL, CENTER_GT2_ROW, ENGAGED);
    }
}

module selected_center_carriage_rail_collision_part() {
    intersection() {
        center_clutch_guide_rails(CENTER_GT2_COL, CENTER_GT2_ROW);
        center_clutch_input_carriage(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            ENGAGED
        );
    }
}

module selected_center_input_rotor_carriage_collision_part() {
    intersection() {
        center_gt2_male(CENTER_GT2_COL, CENTER_GT2_ROW, ENGAGED);
        center_clutch_input_carriage(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            ENGAGED
        );
    }
}

module selected_center_stops_carriage_collision_part() {
    intersection() {
        center_clutch_stops(CENTER_GT2_COL, CENTER_GT2_ROW);
        center_clutch_input_carriage(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            ENGAGED
        );
    }
}

module selected_center_guide_stop_collision_part() {
    intersection() {
        center_clutch_guide_rails(CENTER_GT2_COL, CENTER_GT2_ROW);
        center_clutch_stops(CENTER_GT2_COL, CENTER_GT2_ROW);
    }
}

module selected_center_selector_shoe_part() {
    color("#c8d3dc")
        union() {
            translate([
                clutch_col_x(CENTER_GT2_COL)
                    + CENTER_SELECTOR_SHOE_TANGENT_OFFSET_MM,
                CENTER_SELECTOR_SHOE_TARGET_Y_MM,
                CENTER_SELECTOR_SHOE_Z_MM
            ])
                rotate([-90, 0, 0])
                    center_clutch_selector_shoe();
            center_clutch_selector_support_arm();
        }
}

module selected_center_input_shaft_part() {
    center_clutch_input_shaft(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_output_shaft_part() {
    center_clutch_output_shaft(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_input_bearings_part() {
    center_clutch_input_bearings(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_output_bearings_part() {
    center_clutch_output_bearings(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_upper_clutch_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_male(selected_col(), selected_row(), ENGAGED);
    else
        clutch_upper_carrier(selected_col(), selected_row(), ENGAGED, false);
}

module selected_upper_spur_part() {
    col = selected_col();
    row = selected_row();
    if (is_center_gt2_station(col, row))
        center_gt2_male(col, row, ENGAGED);
    else
        spur_gear_z(
            clutch_col_x(col),
            clutch_upper_y(row, ENGAGED),
            DRIVE_AXIS_Z,
            CLUTCH_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            CLUTCH_GEAR_TOOTH_DEPTH,
            CLUTCH_GEAR_T,
            ROD_D + 2 * ROD_CLEARANCE
        );
}

module selected_upper_dog_part() {
    col = selected_col();
    row = selected_row();
    if (is_center_gt2_station(col, row))
        center_gt2_male(col, row, ENGAGED);
    else
        dog_face_y(
            clutch_col_x(col),
            clutch_upper_dog_y(row, ENGAGED),
            DRIVE_AXIS_Z,
            CLUTCH_DOG_TEETH,
            false
        );
}

module selected_lower_takeoff_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_female(selected_col(), selected_row());
    else
        clutch_lower_takeoff(selected_col(), selected_row());
}

module selected_lower_dog_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_female(selected_col(), selected_row());
    else
        dog_face_y(
            clutch_col_x(selected_col()),
            clutch_fixed_dog_y(selected_row()),
            DRIVE_AXIS_Z,
            CLUTCH_DOG_TEETH,
            true
        );
}

module selected_rear_pulley_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_female(selected_col(), selected_row());
    else
        timing_pulley_y(
            clutch_col_x(selected_col()),
            clutch_takeoff_pulley_y(selected_row()),
            DRIVE_AXIS_Z,
            TIMING_TEETH,
            "round"
        );
}

module selected_spring_part() {
    if (!is_center_gt2_station(selected_col(), selected_row()))
        clutch_spring_only(selected_col(), selected_row(), ENGAGED);
}

module selected_screw_part() {
    col = selected_col();
    row = selected_row();
    if (!is_center_gt2_station(col, row))
        t_countersunk_screw_y(
            clutch_col_x(col),
            DRIVE_AXIS_Z,
            clutch_screw_top_y(row, ENGAGED)
        );
}

module selected_fork_part() {
    if (!is_center_gt2_station(selected_col(), selected_row()))
        clutch_fork(selected_col(), selected_row(), ENGAGED);
}

module selected_drawer_belt_part() {
    col = selected_col();
    row = selected_row();
    color(COLOR_BELT, 0.18)
        if (is_center_gt2_station(col, row))
            center_gt2_belt_loop_z(
                clutch_col_x(col),
                center_gt2_z(),
                CENTER_GT2_FRONT_PULLEY_Z,
                center_gt2_belt_y(row)
            );
        else
            belt_loop_z(
                clutch_col_x(col),
                DRIVE_AXIS_Z,
                FRONT_PULLEY_Z,
                drawer_belt_y(row)
            );
}

module selected_front_compound_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_front_compound(selected_col(), selected_row());
    else
        drawer_front_compound(selected_col(), selected_row());
}

module selected_front_pulley_part() {
    if (is_center_gt2_station(selected_col(), selected_row()))
        center_gt2_front_pulley_y(
            clutch_col_x(selected_col()),
            center_gt2_belt_y(selected_row()),
            CENTER_GT2_FRONT_PULLEY_Z
        );
    else
        timing_pulley_y(
            clutch_col_x(selected_col()),
            drawer_belt_y(selected_row()),
            FRONT_PULLEY_Z,
            TIMING_TEETH,
            "round"
        );
}

module selected_front_gear_part() {
    col = selected_col();
    row = selected_row();
    if (is_center_gt2_station(col, row))
        spur_gear_y(
            clutch_col_x(col),
            center_gt2_front_gear_y(row),
            CENTER_GT2_FRONT_PULLEY_Z,
            FRONT_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            FRONT_GEAR_TOOTH_DEPTH,
            FRONT_GEAR_T,
            ROUND_BORE_D
        );
    else
        spur_gear_y(
            clutch_col_x(col),
            drawer_front_gear_y(row),
            FRONT_PULLEY_Z,
            FRONT_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            FRONT_GEAR_TOOTH_DEPTH,
            FRONT_GEAR_T
        );
}

module selected_drawer_rack_part() {
    row = selected_row();
    if (is_center_gt2_station(selected_col(), row))
        horizontal_drawer_rack(
            clutch_col_x(selected_col()),
            WORLD_PARTITION_FRONT_Z + 1.5,
            CENTER_GT2_FRONT_PULLEY_Z - 3.5,
            center_gt2_front_gear_y(row)
        );
    else
        horizontal_drawer_rack(
            clutch_col_x(selected_col()),
            WORLD_PARTITION_FRONT_Z + 1.5,
            FRONT_PULLEY_Z - 3.5,
            drawer_front_gear_y(row)
        );
}

module clutch_detail() {
    // A selected station is rendered in place.  The migrated center station
    // is magnetic and has no legacy spring/screw/fork; EXPLODE only separates
    // the visual reference without changing its mating datums.
    col = selected_col();
    row = selected_row();
    x = clutch_col_x(col);
    z = DRIVE_AXIS_Z;
    if (is_center_gt2_station(col, row)) {
        center_gt2_clutch(col, row, ENGAGED);
        // The center detail must show the real selector shoe/support bridge as
        // well as the carrier.  The assembly branch emits the shoe separately
        // to keep it as one browser part; this detail branch owns the complete
        // first-article close-up and therefore adds it here exactly once.
        selected_center_selector_shoe_part();
    } else if (SHOW_LEGACY_STATIONS)
        translate([0, 0, -CLUTCH_EXPLODE])
            clutch_station(col, row, ENGAGED, true);
    if (CLUTCH_EXPLODE > 0
        && SHOW_LEGACY_STATIONS
        && !is_center_gt2_station(col, row))
        color(COLOR_RACK, 0.45)
            translate([
                x - 1.0,
                clutch_upper_open_y(row) - 1.0,
                z - CLUTCH_EXPLODE - 1.0
            ])
                cube([2.0, 30, 2.0]);
}
//#endregion

//#region 公开 API：输出入口
module clutch_scene_geometry() {
    if (CLUTCH_PART == "assembly") {
        clutch_cabinet_context();
        world_axes_marker();
        power_bus();
        all_clutches();
        selected_center_selector_shoe_part();
        drawer_drive();
        if (SHOW_LEGACY_STATIONS
            && !is_center_gt2_station(selected_col(), selected_row()))
            clutch_fork(selected_col(), selected_row(), ENGAGED);
    } else if (CLUTCH_PART == "cabinet") {
        // Export the shell alone as a watertight printed part; internal panels and
        // drawer ghosts are visual context only and intentionally do not enter it.
        color(COLOR_CABINET) clutch_cabinet_shell();
    } else if (CLUTCH_PART == "cabinet_context") {
        // Preview-only cabinet orientation and compartment datum. This remains
        // separate from the printable shell so the folder can toggle the grid.
        clutch_cabinet_context();
    } else if (CLUTCH_PART == "power_bus") {
        power_bus();
    } else if (CLUTCH_PART == "all_vertical_axes") {
        all_vertical_axes();
    } else if (CLUTCH_PART == "drawer_drive") {
        drawer_drive();
    } else if (CLUTCH_PART == "clutch") {
        all_clutches();
    } else if (CLUTCH_PART == "clutch_detail") {
        clutch_detail();
    } else if (CLUTCH_PART == "motor") {
        power_motor_vertical();
    } else if (CLUTCH_PART == "motor_body") {
        selected_power_motor_body_part();
    } else if (CLUTCH_PART == "motor_shaft") {
        selected_power_motor_shaft_part();
    } else if (CLUTCH_PART == "left_d_axis") {
        selected_left_d_axis_part();
    } else if (CLUTCH_PART == "tensioner_t_solid") {
        selected_tensioner_t_solid_part();
    } else if (CLUTCH_PART == "side_axes") {
        side_axes();
    } else if (CLUTCH_PART == "column") {
        selected_column_part();
    } else if (CLUTCH_PART == "vertical_rack") {
        selected_vertical_rack_part();
    } else if (CLUTCH_PART == "column_sync_belt_bottom") {
        selected_column_sync_belt_bottom_part();
    } else if (CLUTCH_PART == "column_sync_belt_top") {
        selected_column_sync_belt_top_part();
    } else if (CLUTCH_PART == "column_sync_tensioner") {
        selected_column_sync_tensioner_part();
    } else if (CLUTCH_PART == "center_input_rotor") {
        selected_center_input_rotor_part();
    } else if (CLUTCH_PART == "center_output_rotor") {
        selected_center_output_rotor_part();
    } else if (CLUTCH_PART == "center_input_carriage") {
        selected_center_input_carriage_part();
    } else if (CLUTCH_PART == "center_output_cage") {
        selected_center_output_cage_part();
    } else if (CLUTCH_PART == "center_guide_rails") {
        selected_center_guide_rails_part();
    } else if (CLUTCH_PART == "center_linear_bearings") {
        selected_center_linear_bearings_part();
    } else if (CLUTCH_PART == "center_linear_bearing_retainers") {
        selected_center_linear_bearing_retainers_part();
    } else if (CLUTCH_PART == "center_linear_bearing_fit_coupon") {
        selected_center_linear_bearing_fit_coupon_part();
    } else if (CLUTCH_PART == "center_stops") {
        selected_center_stops_part();
    } else if (CLUTCH_PART == "center_mechanism_plate") {
        selected_center_mechanism_plate_part();
    } else if (CLUTCH_PART == "center_plate_belt_collision") {
        selected_center_plate_belt_collision_part();
    } else if (CLUTCH_PART == "center_clutch_pair_collision") {
        selected_center_clutch_pair_collision_part();
    } else if (CLUTCH_PART == "center_selector_rail_collision") {
        selected_center_selector_rail_collision_part();
    } else if (CLUTCH_PART == "center_selector_male_collision") {
        selected_center_selector_male_collision_part();
    } else if (CLUTCH_PART == "center_selector_chain_support_contact") {
        selected_center_selector_chain_support_contact_part();
    } else if (CLUTCH_PART == "center_carriage_rail_collision") {
        selected_center_carriage_rail_collision_part();
    } else if (CLUTCH_PART == "center_input_rotor_carriage_collision") {
        selected_center_input_rotor_carriage_collision_part();
    } else if (CLUTCH_PART == "center_stops_carriage_collision") {
        selected_center_stops_carriage_collision_part();
    } else if (CLUTCH_PART == "center_guide_stop_collision") {
        selected_center_guide_stop_collision_part();
    } else if (CLUTCH_PART == "center_selector_shoe") {
        selected_center_selector_shoe_part();
    } else if (CLUTCH_PART == "center_input_shaft") {
        selected_center_input_shaft_part();
    } else if (CLUTCH_PART == "center_output_shaft") {
        selected_center_output_shaft_part();
    } else if (CLUTCH_PART == "center_input_bearings") {
        selected_center_input_bearings_part();
    } else if (CLUTCH_PART == "center_output_bearings") {
        selected_center_output_bearings_part();
    } else if (CLUTCH_PART == "contract") {
        // Contract mode intentionally emits no geometry. The machine-readable
        // echo below is parsed by the export helper.
    } else if (CLUTCH_PART == "upper_clutch") {
        selected_upper_clutch_part();
    } else if (CLUTCH_PART == "upper_spur") {
        selected_upper_spur_part();
    } else if (CLUTCH_PART == "upper_dog") {
        selected_upper_dog_part();
    } else if (CLUTCH_PART == "lower_takeoff") {
        selected_lower_takeoff_part();
    } else if (CLUTCH_PART == "lower_dog") {
        selected_lower_dog_part();
    } else if (CLUTCH_PART == "rear_pulley") {
        selected_rear_pulley_part();
    } else if (CLUTCH_PART == "spring") {
        selected_spring_part();
    } else if (CLUTCH_PART == "screw") {
        selected_screw_part();
    } else if (CLUTCH_PART == "fork") {
        selected_fork_part();
    } else if (CLUTCH_PART == "drawer_belt") {
        selected_drawer_belt_part();
    } else if (CLUTCH_PART == "front_compound") {
        selected_front_compound_part();
    } else if (CLUTCH_PART == "front_pulley") {
        selected_front_pulley_part();
    } else if (CLUTCH_PART == "front_gear") {
        selected_front_gear_part();
    } else if (CLUTCH_PART == "drawer_rack") {
        selected_drawer_rack_part();
    } else if (CLUTCH_PART == "world_axes") {
        world_axes_marker();
    } else {
        assert(false, str("unknown CLUTCH_PART: ", CLUTCH_PART));
    }
}

clutch_scene_geometry();
//#endregion

//#region 业务逻辑与检查
echo("cabinet_clutch", "W", W, "H", H, "D", D);
echo("world_axes", "x=width", "y=height(+up)", "z=depth(+front)", "front_z", 0, "rear_z", -D);
echo("rear_view_sides", "right", "-X/toward_x0", "left", "+X/toward_xW", "tensioner", "right", "motor", "left");
echo("drive_axis", "motor_column", MOTOR_COLUMN, "x_motor", MOTOR_X, "x_plus_max_column", clutch_col_x(N_COL - 1), "motor_face_y", MOTOR_FACE_Y, "z_base", DRIVE_AXIS_Z_BASE, "z", DRIVE_AXIS_Z, "rear_shift_z", DRAWER_DRIVE_REAR_SHIFT_Z, "front_interface_z", FRONT_PULLEY_Z, "belt_teeth", DRAWER_BELT_TEETH, "y_bottom", BUS_BOTTOM_Y, "y_top", BUS_TOP_Y);
echo("drive_clearance", "snake_chain_center_z", SNAKE_CHAIN_CENTER_Z, "snake_chain_rear_edge_z", SNAKE_CHAIN_REAR_EDGE_Z, "pulley_front_edge_z", DRIVE_AXIS_Z + TIMING_FLANGE_R, "clearance", SNAKE_CHAIN_REAR_EDGE_Z - (DRIVE_AXIS_Z + TIMING_FLANGE_R));
echo("snake_motor_boss", "center_x", SNAKE_MOTOR_MOUNT_CENTER_X, "seat_center_z", SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z, "stage1_h", SNAKE_MOTOR_BOSS_STAGE1_H, "stage1_top_y", SNAKE_MOTOR_BOSS_STAGE1_TOP_Y, "guide_h", SNAKE_MOTOR_BOSS_GUIDE_H, "guide_top_y", SNAKE_MOTOR_BOSS_GUIDE_TOP_Y, "guide_od", SNAKE_MOTOR_BOSS_GUIDE_OD, "bore_d", SNAKE_MOTOR_BOSS_GUIDE_BORE_D);
echo("vertical_axes", "active_count", ACTIVE_VERTICAL_AXIS_COUNT, "planned_count", PLANNED_VERTICAL_AXIS_COUNT, "layout", "five drawer-columns; motor directly coupled to +X-most column; no separate D-drive column", "gear_body_length", VERTICAL_GEAR_LENGTH, "end_clearance", VERTICAL_GEAR_END_CLEARANCE, "pulley_axial_width", COLUMN_SYNC_PULLEY_AXIAL_WIDTH, "belt_width", GT2_BELT_WIDTH);
echo("left_axis", "profile", "D", "d", ROD_D, "pulley_bore", "D");
echo("timing", "pitch", TIMING_PITCH_MM, "teeth", TIMING_TEETH, "pitch_r", TIMING_PITCH_R, "outer_d", 2 * TIMING_OUTER_R, "flange_d", TIMING_FLANGE_D);
echo("belt", "axial_width_world_y", TIMING_BELT_W, "base_thickness_xz", TIMING_BELT_T, "base_inner_r", TIMING_BELT_BASE_INNER_R, "base_outer_r", TIMING_BELT_BASE_OUTER_R, "tooth_pitch", TIMING_PITCH_MM, "tooth_h", TIMING_BELT_TOOTH_H);
echo("column_sync_gt2", "pitch_mm", GT2_PULLEY_PITCH_MM, "pulley_teeth", GT2_PULLEY_TEETH, "belt_teeth", COLUMN_SYNC_BELT_TEETH, "belt_length_mm", COLUMN_SYNC_BELT_LENGTH_MM, "center_distance_mm", COLUMN_SYNC_BELT_CENTER_DISTANCE, "tensioner_nominal_x", COLUMN_SYNC_TENSIONER_NOMINAL_X, "tensioner_x", COLUMN_SYNC_TENSIONER_X, "adjustment_direction", "positive screw-out -> world -X");
echo("center_gt2", "enabled", true, "legacy_stations", SHOW_LEGACY_STATIONS, "cell_col_row", CENTER_GT2_COL, CENTER_GT2_ROW, "mating_axis_z", center_gt2_z(), "shaft_axis_z", DRIVE_AXIS_Z, "shaft_z_offset", gt2_center_distance(), "long_profile", str(GT2_LONG_TEETH, "T/", GT2_LONG_PITCH_MM, "mm"), "male_profile", str(GT2_MALE_TEETH, "T/", GT2_MALE_PITCH_MM, "mm"), "belt", str(CENTER_GT2_BELT_TEETH, "T/", GT2_PULLEY_PITCH_MM, "mm/", GT2_BELT_WIDTH, "mm"), "belt_center_distance", CENTER_GT2_BELT_CENTER_DISTANCE, "front_pulley_z", CENTER_GT2_FRONT_PULLEY_Z, "belt_y", center_gt2_belt_y(CENTER_GT2_ROW), "front_gear_y", center_gt2_front_gear_y(CENTER_GT2_ROW), "guide_outer_d", 2 * gt2_belt_guide_r(), "mother_outer_d", 2 * GT2_MOTHER_OUTER_R, "lower_retainer_t", GT2_BELT_LOWER_RETAINER_T, "mother_pocket_depth", GT2_MOTHER_POCKET_DEPTH, "engage_stroke", GT2_CLUTCH_ENGAGE_STROKE_MM);
echo("tensioner_skp_parametric", "source", "弹簧加力的滑动张紧轮调节滑台.skp", "axis_map", "SKP+Y(green)->world+X, SKP+X(red)->world+Y, SKP+Z(blue)->world-Z (same Z axis, rearward)", "native_bbox_xyz", TENSIONER_SKP_NATIVE_SIZE_X, TENSIONER_SKP_NATIVE_SIZE_Y, TENSIONER_SKP_NATIVE_SIZE_Z, "world_bbox_xyz", TENSIONER_SKP_WORLD_SIZE_X, TENSIONER_SKP_WORLD_SIZE_Y, TENSIONER_SKP_WORLD_SIZE_Z, "world_center", TENSIONER_SKP_WORLD_CENTER_X, TENSIONER_SKP_WORLD_CENTER_Y, TENSIONER_SKP_WORLD_CENTER_Z, "mesh_import", false, "parametric_csg", true);
echo("clutch", "open_gap", CLUTCH_OPEN_GAP, "drop", CLUTCH_DROP_MM, "selected", selected_col(), selected_row(), "engaged", ENGAGED);
// These values are intentionally composed from the shared parameter file,
// rather than repeated as browser-owned geometry constants.
// Machine-readable source marker. The export helper parses this line and
// writes the same object into cabinet_chain_motion.json. Geometry values are
// deliberately composed from the shared pair/carrier parameters so OpenSCAD
// remains the only mechanical source of truth.
echo(
    "CENTER_CLUTCH_CONTRACT_DYNAMIC",
    "version=1",
    "axis=+Y",
    "role=input/output",
    "verticalLayoutMode=center-clutch-lift",
    str("centerClutchVerticalLiftMm=", CENTER_CLUTCH_VERTICAL_LIFT_MM),
    str("axisXMm=", clutch_col_x(CENTER_GT2_COL)),
    str("axisZMm=", center_gt2_z()),
    str("inputBaseYMm=", center_gt2_male_base_y(CENTER_GT2_ROW)),
    str("maleBottomYMm=", center_gt2_male_base_y(CENTER_GT2_ROW)),
    str("outputBaseYMm=", center_gt2_female_base_y(CENTER_GT2_ROW)),
    str("openGapMm=", GT2_MOTHER_GAP),
    str("dogInsertionMm=", GT2_MOTHER_EFFECTIVE_INSERTION),
    str("strokeMm=", GT2_CLUTCH_ENGAGE_STROKE_MM),
    str("pocketDepthMm=", GT2_MOTHER_POCKET_DEPTH),
    str("bottomClearanceMm=", GT2_MOTHER_BOTTOM_CLEARANCE),
    str("magnetNonContactClearanceMm=", GT2_MAGNET_NONCONTACT_CLEARANCE_MM),
    str("femaleMagnetProjectionMm=", GT2_FEMALE_MAGNET_PROJECTION_MM),
    str("magnetNominalDiameterMm=", GT2_MAGNET_NOMINAL_D),
    str("gearCenterDistanceMm=", gt2_center_distance()),
    str("longPitchRadiusMm=", gt2_long_pitch_r()),
    str("inputPitchRadiusMm=", gt2_male_pitch_r()),
    str("gearMeshClearanceMm=", GT2_GEAR_MESH_CLEARANCE),
    str("dogPocketPhaseDeg=", GT2_MOTHER_POCKET_PHASE_DEG),
    str("longTipRadiusMm=", gt2_long_tip_r()),
    str("inputTipRadiusMm=", gt2_male_tip_r()),
    str("beltEnvelopeRadiusMm=", gt2_belt_envelope_r()),
    str("beltGuideRadiusMm=", gt2_belt_guide_r()),
    str("motherOuterRadiusMm=", GT2_MOTHER_OUTER_R),
    str("selectorTriggerSpacingMm=", GT2_ACTUATOR_TRIGGER_SPACING_MM),
    str("railY0Mm=", center_clutch_rail_y0(CENTER_GT2_ROW)),
    str("railY1Mm=", center_clutch_rail_y1(CENTER_GT2_ROW)),
    str("guideRodDiameterMm=", CENTER_CLUTCH_GUIDE_ROD_D),
    str("guideRodCaptureMm=", CENTER_CLUTCH_GUIDE_ROD_CAPTURE),
    str("guideRodY0Mm=", center_clutch_rail_y0(CENTER_GT2_ROW)
        - CENTER_CLUTCH_GUIDE_ROD_CAPTURE),
    str("guideRodY1Mm=", center_clutch_rail_y1(CENTER_GT2_ROW)
        + CENTER_CLUTCH_GUIDE_ROD_CAPTURE),
    str("linearBearingNominalIdMm=", CENTER_CLUTCH_LINEAR_BEARING_ID),
    str("linearBearingNominalOdMm=", CENTER_CLUTCH_LINEAR_BEARING_OD),
    str("linearBearingNominalLengthMm=", CENTER_CLUTCH_LINEAR_BEARING_L),
    str("linearBearingCount=", CENTER_CLUTCH_LINEAR_BEARING_COUNT),
    str("linearBearingSeatDiameterMm=", CENTER_CLUTCH_LINEAR_BEARING_SEAT_D),
    str("linearBearingSeatDepthMm=", CENTER_CLUTCH_LINEAR_BEARING_SEAT_DEPTH),
    str("linearBearingHolderOuterDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_OD),
    str("linearBearingHolderLengthMm=",
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_L),
    str("linearBearingHolderBackShoulderMm=",
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_BACK_SHOULDER_T),
    str("linearBearingHolderFrontNeckDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_D),
    str("linearBearingHolderFrontNeckLengthMm=",
        CENTER_CLUTCH_LINEAR_BEARING_HOLDER_FRONT_NECK_L),
    str("linearBearingRetainerInnerDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_ID),
    str("linearBearingRetainerOuterDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_OD),
    str("linearBearingRetainerThicknessMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_T),
    str("linearBearingRetainerLipOuterDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_LIP_OD),
    str("linearBearingRetainerSkirtInnerDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_ID),
    str("linearBearingRetainerSkirtOuterDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_OD),
    str("linearBearingRetainerSkirtLengthMm=",
        CENTER_CLUTCH_LINEAR_BEARING_RETAINER_SKIRT_L),
    str("linearBearingSeatRadialClearanceMm=",
        CENTER_CLUTCH_LINEAR_BEARING_SEAT_RADIAL_CLEARANCE),
    str("linearBearingRodNominalClearanceMm=",
        CENTER_CLUTCH_LINEAR_BEARING_ROD_NOMINAL_CLEARANCE),
    "linearBearingModel=LM3UU-cutaway-reference",
    "linearBearingFitCouponPart=cabinet-clutch/center_linear_bearing_fit_coupon",
    str("linearBearingFitCouponRodSpacingMm=",
        CENTER_CLUTCH_FIT_COUPON_ROD_SPACING),
    "linearBearingFitCouponSeatVariantsMm=7.20/7.30/7.40",
    str("openStopY0Mm=", center_clutch_open_stop_y(CENTER_GT2_ROW)),
    str("openStopY1Mm=", center_clutch_open_stop_y(CENTER_GT2_ROW) + CENTER_CLUTCH_STOP_PAD_T),
    str("engagedStopY0Mm=", center_clutch_engaged_stop_y(CENTER_GT2_ROW)),
    str("engagedStopY1Mm=", center_clutch_engaged_stop_y(CENTER_GT2_ROW) + CENTER_CLUTCH_STOP_PAD_T),
    str("openTabY0Mm=", center_clutch_carriage_shoe_y0(CENTER_GT2_ROW)),
    str("openTabY1Mm=", center_clutch_carriage_shoe_y1(CENTER_GT2_ROW)),
    str("engagedTabY0Mm=", center_clutch_engaged_carriage_shoe_y0(CENTER_GT2_ROW)),
    str("engagedTabY1Mm=", center_clutch_engaged_carriage_shoe_y1(CENTER_GT2_ROW)),
    str("bearingSeatDiameterMm=", CENTER_CLUTCH_BEARING_SEAT_D),
    str("bearingSeatDepthMm=", CENTER_CLUTCH_BEARING_SEAT_DEPTH),
    str("bearingBackShoulderMm=", CENTER_CLUTCH_BEARING_BACK_SHOULDER_T),
    str("bearingReferenceCenterOffsetMm=", CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET),
    str("bearingCenterOffsetMm=", CENTER_CLUTCH_BEARING_CENTER_OFFSET),
    str("bearingPairSpacingMm=", CENTER_CLUTCH_BEARING_PAIR_SPACING),
    str("bearingBlockThicknessMm=", CENTER_CLUTCH_BEARING_BLOCK_T),
    str("bearingBlockWidthMm=", CENTER_CLUTCH_BEARING_BLOCK_X),
    str("bearingBlockHeightMm=", CENTER_CLUTCH_BEARING_BLOCK_Z),
    str("guideRailXOffsetMm=", CENTER_CLUTCH_RAIL_X_OFFSET),
    str("guideRailZOffsetMm=", CENTER_CLUTCH_RAIL_Z_OFFSET),
    str("stopPadWidthMm=", CENTER_CLUTCH_STOP_PAD_W),
    str("stopPadXOffsetMm=", CENTER_CLUTCH_STOP_PAD_X_OFFSET),
    str("carriageUprightCenterXOffsetMm=",
        CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET),
    str("carriageUprightWidthMm=", CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T),
    str("carriageUprightZ0Mm=", CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0),
    str("carriageUprightHeightMm=", CENTER_CLUTCH_CARRIAGE_UPRIGHT_H),
    str("carriageUprightY0Mm=", CENTER_CLUTCH_CARRIAGE_UPRIGHT_Y0),
    str("carriageUprightLengthMm=", CENTER_CLUTCH_CARRIAGE_UPRIGHT_L),
    str("plateWidthMm=", CENTER_CLUTCH_PLATE_W),
    str("carriageUprightRadialClearanceMm=", sqrt(
        pow(
            CENTER_CLUTCH_CARRIAGE_UPRIGHT_CENTER_X_OFFSET
                - CENTER_CLUTCH_CARRIAGE_UPRIGHT_X_T / 2,
            2
        )
        + pow(CENTER_CLUTCH_CARRIAGE_UPRIGHT_Z0, 2)
    ) - gt2_male_tip_r()),
    str("plateKeyWidthMm=", CENTER_CLUTCH_PLATE_KEY_W),
    str("plateKeyHeightMm=", CENTER_CLUTCH_PLATE_KEY_H),
    str("plateKeyClearanceMm=", CENTER_CLUTCH_SUPPORT_KEY_CLEAR),
    str("plateM3ClearanceMm=", CENTER_CLUTCH_M3_CLEAR_D),
    str("plateBeltPassageHalfWidthMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X),
    str("plateBeltPassageAxialWidthMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y),
    str("plateBeltPassageRadialClearanceMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR),
    str("plateBeltPassageAxialClearanceMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR),
    "plateSupport=partition-through-M3",
    str("selectorShoeTangentOffsetMm=", CENTER_SELECTOR_SHOE_TANGENT_OFFSET_MM),
    str("selectorShoeNormalOffsetMm=", CENTER_SELECTOR_SHOE_NORMAL_OFFSET_MM),
    str("selectorShoeTargetYMm=", CENTER_SELECTOR_SHOE_TARGET_Y_MM),
    str("selectorShoeZMm=", CENTER_SELECTOR_SHOE_Z_MM),
    str("selectorShoeAnchorXMm=", clutch_col_x(CENTER_GT2_COL)
        + CENTER_SELECTOR_SHOE_TANGENT_OFFSET_MM),
    str("selectorShoeAnchorYMm=", CENTER_SELECTOR_SHOE_TARGET_Y_MM),
    str("selectorShoeAnchorZMm=", CENTER_SELECTOR_SHOE_Z_MM),
    str("selectorShoeMagnetFaceOffsetMm=",
        CENTER_SELECTOR_SHOE_MAGNET_FACE_OFFSET_MM),
    str("selectorShoeMagnetFaceYMm=", CENTER_SELECTOR_SHOE_TARGET_Y_MM
        + CENTER_SELECTOR_SHOE_MAGNET_FACE_OFFSET_MM),
    str("selectorShoeTriggerClearanceMm=",
        CENTER_SELECTOR_SHOE_TRIGGER_CLEARANCE_MM),
    "selectorShoeMagnetAxis=+Y",
    str("selectorShoeChainAttachYMm=",
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM),
    str("selectorShoeChainAttachZMm=",
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM),
    str("selectorShoeChainAttachXMm=",
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM),
    str("selectorShoeChainContactDiameterMm=",
        CENTER_SELECTOR_SHOE_CHAIN_CONTACT_D_MM),
    str("selectorShoeSupportXOffsetMm=",
        CENTER_SELECTOR_SHOE_SUPPORT_X_OFFSET_MM),
    str("selectorShoeSupportArmXOffsetMm=",
        CENTER_SELECTOR_SHOE_SUPPORT_ARM_X_OFFSET_MM),
    str("selectorShoeSupportXWidthMm=",
        CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM),
    str("selectorShoeSupportChainYOverhangMm=",
        CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Y_OVERHANG_MM),
    str("selectorShoeSupportChainZT=",
        CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T),
    str("selectorShoeSupportBridgeOverlapMm=",
        CENTER_SELECTOR_SHOE_SUPPORT_BRIDGE_OVERLAP_MM),
    str("selectorShoeSupportDropMm=",
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM
            - CENTER_SELECTOR_SHOE_TARGET_Y_MM),
    str("selectorShoeSupportReachMm=",
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM
            + CENTER_SELECTOR_SHOE_SUPPORT_CHAIN_Z_T / 2
            - (CENTER_SELECTOR_SHOE_Z_MM + CENTER_SELECTOR_SHOE_D / 2
            - CENTER_SELECTOR_SHOE_SUPPORT_BRIDGE_OVERLAP_MM)),
    "rotaryBearingArrangement=two-per-rotor-axially-spaced",
    "linearBearingArrangement=left-right-one-per-guide-rod",
    "selectorShoeChainSupportPart=cabinet-clutch/center_selector_chain_support_contact",
    str("selectorShoeBodyWidthMm=", CENTER_SELECTOR_SHOE_W),
    str("selectorShoeBodyDepthMm=", CENTER_SELECTOR_SHOE_D),
    str("selectorShoeBodyHeightMm=", CENTER_SELECTOR_SHOE_H),
    str("selectorShoePocketRimHeightMm=", CENTER_SELECTOR_SHOE_POCKET_RIM_H),
    "selectorShoeCoordinateFrame=native-world",
    str("inputShaftStartMm=", CENTER_CLUTCH_SHAFT_INPUT_START),
    str("inputShaftLengthMm=", CENTER_CLUTCH_SHAFT_INPUT_LENGTH),
    str("outputShaftStartMm=", CENTER_CLUTCH_SHAFT_OUTPUT_START),
    str("outputShaftLengthMm=", CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH),
    str("inputGearBandThicknessMm=", GT2_MALE_GEAR_T),
    str("dBoreDepthMm=", GT2_D_BORE_DEPTH),
    "bearingNominal=3x6x2",
    "bearingCountPerRotor=2",
    "bearingCount=4",
    str("shaftDiameterMm=", GT2_D_AXIS_D),
    str("shaftCount=", 2),
    str("shaftCollarOdMm=", CENTER_CLUTCH_SHAFT_COLLAR_OD),
    str("shaftCollarBoreMm=", CENTER_CLUTCH_SHAFT_COLLAR_BORE_D),
    "matingMagnetCount=2",
    "selectorMagnetCount=2",
    "totalMagnetCount=4",
    "actuation=permanent-magnet",
    "engageOnlyWhenStopped=true",
    "releaseBeforeReturn=true",
    "centerCol=2",
    "centerRow=2",
    "inputPart=cabinet-clutch/center_input_rotor",
    "outputPart=cabinet-clutch/center_output_rotor",
    "inputCarriagePart=cabinet-clutch/center_input_carriage",
    "outputCagePart=cabinet-clutch/center_output_cage",
    "mechanismPlatePart=cabinet-clutch/center_mechanism_plate",
    "guidePart=cabinet-clutch/center_guide_rails",
    "linearBearingPart=cabinet-clutch/center_linear_bearings_reference",
    "linearBearingRetainerPart=cabinet-clutch/center_linear_bearing_retainers",
    "stopPart=cabinet-clutch/center_stops",
    "selectorShoePart=cabinet-clutch/center_selector_shoe"
);

// The native shoe is mechanically attached to the chain reference, not only
// placed near it in the browser.  Keep these checks beside the contract echo
// so a changed chain layer or station datum fails before export.
assert(abs(
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM
        - (clutch_col_x(CENTER_GT2_COL)
            + CENTER_SELECTOR_SHOE_SUPPORT_X_OFFSET_MM)
    ) < 0.001,
    "selector shoe chain attach X must be derived from the support arm");
assert(abs(
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM
        - world_row_center_y(CENTER_GT2_ROW)
    ) < 0.001,
    "selector shoe chain attach Y must stay on the R3C3 row datum");
assert(abs(
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Z_MM - SNAKE_CHAIN_CENTER_Z
    ) < 0.001,
    "selector shoe chain attach Z must stay on the snake-chain plane");
assert(CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM > 0
        && CENTER_SELECTOR_SHOE_CHAIN_CONTACT_D_MM > 0,
    "selector shoe chain support and contact witness must have positive size");
assert(
        CENTER_SELECTOR_SHOE_CHAIN_ATTACH_X_MM
            + CENTER_SELECTOR_SHOE_SUPPORT_ARM_X_OFFSET_MM
            - CENTER_SELECTOR_SHOE_SUPPORT_X_WIDTH_MM / 2
        >= clutch_col_x(CENTER_GT2_COL)
            + CENTER_CLUTCH_RAIL_X_OFFSET
            + CENTER_CLUTCH_GUIDE_ROD_D / 2
            + 0.45 - 0.001,
    "selector shoe chain support arm must clear the right guide rod");
assert(CENTER_SELECTOR_SHOE_CHAIN_ATTACH_Y_MM
        > CENTER_SELECTOR_SHOE_TARGET_Y_MM,
    "selector shoe chain support must bridge from the shoe toward the chain");

assert(
    CLUTCH_PART == "assembly"
    || CLUTCH_PART == "cabinet"
    || CLUTCH_PART == "cabinet_context"
    || CLUTCH_PART == "power_bus"
    || CLUTCH_PART == "all_vertical_axes"
    || CLUTCH_PART == "drawer_drive"
    || CLUTCH_PART == "clutch"
    || CLUTCH_PART == "clutch_detail"
    || CLUTCH_PART == "motor"
    || CLUTCH_PART == "motor_body"
    || CLUTCH_PART == "motor_shaft"
    || CLUTCH_PART == "left_d_axis"
    || CLUTCH_PART == "tensioner_t_solid"
    || CLUTCH_PART == "side_axes"
    || CLUTCH_PART == "column"
    || CLUTCH_PART == "vertical_rack"
    || CLUTCH_PART == "column_sync_belt_bottom"
    || CLUTCH_PART == "column_sync_belt_top"
    || CLUTCH_PART == "column_sync_tensioner"
    || CLUTCH_PART == "center_input_rotor"
    || CLUTCH_PART == "center_output_rotor"
    || CLUTCH_PART == "center_input_carriage"
    || CLUTCH_PART == "center_output_cage"
    || CLUTCH_PART == "center_guide_rails"
    || CLUTCH_PART == "center_linear_bearings"
    || CLUTCH_PART == "center_linear_bearing_retainers"
    || CLUTCH_PART == "center_linear_bearing_fit_coupon"
    || CLUTCH_PART == "center_stops"
    || CLUTCH_PART == "center_mechanism_plate"
    || CLUTCH_PART == "center_plate_belt_collision"
    || CLUTCH_PART == "center_clutch_pair_collision"
    || CLUTCH_PART == "center_selector_rail_collision"
    || CLUTCH_PART == "center_selector_male_collision"
    || CLUTCH_PART == "center_selector_chain_support_contact"
    || CLUTCH_PART == "center_carriage_rail_collision"
    || CLUTCH_PART == "center_input_rotor_carriage_collision"
    || CLUTCH_PART == "center_stops_carriage_collision"
    || CLUTCH_PART == "center_guide_stop_collision"
    || CLUTCH_PART == "center_input_shaft"
    || CLUTCH_PART == "center_output_shaft"
    || CLUTCH_PART == "center_input_bearings"
    || CLUTCH_PART == "center_output_bearings"
    || CLUTCH_PART == "center_selector_shoe"
    || CLUTCH_PART == "contract"
    || CLUTCH_PART == "upper_clutch"
    || CLUTCH_PART == "upper_spur"
    || CLUTCH_PART == "upper_dog"
    || CLUTCH_PART == "lower_takeoff"
    || CLUTCH_PART == "lower_dog"
    || CLUTCH_PART == "rear_pulley"
    || CLUTCH_PART == "spring"
    || CLUTCH_PART == "screw"
    || CLUTCH_PART == "fork"
    || CLUTCH_PART == "drawer_belt"
    || CLUTCH_PART == "front_compound"
    || CLUTCH_PART == "front_pulley"
    || CLUTCH_PART == "front_gear"
    || CLUTCH_PART == "drawer_rack"
    || CLUTCH_PART == "world_axes"
);
assert(abs(CLUTCH_OPEN_GAP - 2 * CLUTCH_DOG_TOOTH_H) < 0.001, "open clutch gap must be two dog tooth heights");
assert(abs(TIMING_BELT_W - TIMING_PULLEY_W) < 0.001,
    "timing belt axial width must match the mating pulley width along world Y");
assert(abs((TIMING_BELT_BASE_OUTER_R - TIMING_BELT_BASE_INNER_R) - TIMING_BELT_T) < 0.001,
    "timing belt base radial thickness must equal TIMING_BELT_T");
assert(TIMING_BELT_BASE_OUTER_R < TIMING_FLANGE_R,
    "timing belt base must remain inside the larger pulley retaining flange");
assert(TIMING_BELT_TOOTH_H < TIMING_TOOTH_DEPTH,
    "belt tooth height must stay below the mating pulley tooth depth");
assert(TIMING_BELT_TOOTH_TIP < TIMING_PITCH_MM * 0.40,
    "belt tooth tip must fit the 0.40-pitch pulley root gap");
assert(GT2_LONG_TEETH == VERTICAL_GEAR_TEETH
        && abs(GT2_LONG_PITCH_MM - VERTICAL_GEAR_PITCH_MM) < 0.001,
    "center GT2 long-gear datum must match the cabinet vertical shaft");
assert(GT2_MALE_TEETH == VERTICAL_GEAR_TEETH
        && abs(GT2_MALE_PITCH_MM - VERTICAL_GEAR_PITCH_MM) < 0.001,
    "center GT2 male gear must match the cabinet vertical shaft");
assert(CENTER_GT2_BELT_TEETH == 80,
    "center drawer belt is the selected 160 mm / 80T 2GT loop");
assert(CENTER_GT2_BELT_CENTER_DISTANCE > 0,
    "center 2GT belt center distance must be positive");
assert(CENTER_GT2_Z > DRIVE_AXIS_Z,
    "center clutch axis must be on the vertical shaft +Z side");
assert(CENTER_GT2_BELT_BASE_OUTER_R < gt2_belt_guide_r(),
    "center 2GT belt back envelope must stay inside its guide wall");
assert(CENTER_GT2_FRONT_PULLEY_Z < 0
        && CENTER_GT2_FRONT_PULLEY_Z > WORLD_PARTITION_FRONT_Z,
    "center 2GT front pulley must stay in the drawer bay");
assert(COLUMN_SYNC_BELT_TEETH == 226,
    "column sync must use the selected 226T / 452 mm 2GT loop");
assert(abs(COLUMN_SYNC_BELT_LENGTH_MM
        - COLUMN_SYNC_BELT_TEETH * GT2_PULLEY_PITCH_MM) < 0.001,
    "column sync belt length must be derived from 2GT pitch");
assert(COLUMN_SYNC_TENSIONER_NOMINAL_X < MOTOR_X,
    "column sync tensioner must be on the -X side of the motor");
assert(VERTICAL_TENSIONER_OFFSET_X >= 0,
    "positive tensioner adjustment is screw-out toward world -X");
assert(COLUMN_SYNC_BELT_BASE_OUTER_R < gt2_belt_guide_r(),
    "column sync 2GT belt back envelope must stay inside its guide wall");
assert(GT2_PULLEY_FACE_T >= GT2_BELT_WIDTH + 0.80,
    "every column GT2 pulley face must be wider than the 6 mm belt");
assert(COLUMN_SYNC_PULLEY_AXIAL_WIDTH > GT2_BELT_WIDTH,
    "column GT2 guide stack must be wider than the belt");
assert(VERTICAL_GEAR_LENGTH > 0,
    "vertical gear body must remain positive after pulley clearance");
assert(N_COL == 5, "current clutch layout requires five drawer transmission columns");
assert(abs(MOTOR_X - clutch_col_x(N_COL - 1)) < 0.001,
    "motor must be centered on the +X-most drawer column");
assert(ACTIVE_VERTICAL_AXIS_COUNT == N_COL,
    "active axes must be the five drawer columns; motor shares one column");
assert(PLANNED_VERTICAL_AXIS_COUNT == N_COL + 1,
    "future independent tensioner boundary is reserved outside the five columns");
assert(DRIVE_AXIS_Z < WORLD_PARTITION_BACK_Z - 1.0, "drive bus must be behind the partition");
assert(DRIVE_AXIS_Z + TIMING_OUTER_R < WORLD_PARTITION_BACK_Z - 0.50, "rear pulley OD must clear the partition");
assert(DRIVE_AXIS_Z - TIMING_OUTER_R > -D + WORLD_BACK_PANEL_T + 1.0, "rear belt must clear the back panel");
assert(SNAKE_MOTOR_MOUNT_CENTER_X - SNAKE_MOTOR_MOUNT_SEAT_CENTER_X
        > WALL
    && SNAKE_MOTOR_MOUNT_CENTER_X + SNAKE_MOTOR_MOUNT_SEAT_CENTER_X
        < W - WALL,
    "snake motor boss rails must stay inside the cabinet side walls");
assert(SNAKE_MOTOR_BOSS_STAGE1_EMBED > 0
    && SNAKE_MOTOR_BOSS_STAGE1_EMBED < WALL,
    "snake motor boss first step must fuse into the cabinet floor");
assert(SNAKE_MOTOR_BOSS_STAGE1_TOP_Y > WALL
    && SNAKE_MOTOR_BOSS_STAGE1_TOP_Y < 7.0,
    "snake motor boss first step must expose as a low floor stop");
assert(SNAKE_MOTOR_BOSS_GUIDE_OD > SNAKE_MOTOR_BOSS_GUIDE_BORE_D,
    "snake motor boss guide must leave an annular wall");
assert(SNAKE_MOTOR_BOSS_GUIDE_TOP_Y < WORLD_GRID_ORIGIN_Y,
    "snake motor boss guides must remain below the drawer grid");
assert(SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z
        - SNAKE_MOTOR_BOSS_RAIL_L / 2 > -D + WALL
    && SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z
        + SNAKE_MOTOR_BOSS_RAIL_L / 2 < -WALL,
    "snake motor boss rails must stay inside the rear depth");
assert(SNAKE_CHAIN_REAR_EDGE_Z - (DRIVE_AXIS_Z + TIMING_FLANGE_R)
        >= DRAWER_BUS_CHAIN_CLEARANCE,
    "drawer drive rear pulley must stay behind the snake-chain envelope");
assert(BUS_BOTTOM_Y > WALL + 2.0, "bottom bus pulley must clear the cabinet floor");
assert(BUS_TOP_Y < H - WALL - 1.0, "top bus pulley must clear the cabinet roof");
assert(TENSIONER_SKP_NATIVE_SIZE_X > 0
    && TENSIONER_SKP_NATIVE_SIZE_Y > 0
    && TENSIONER_SKP_NATIVE_SIZE_Z > 0,
    "SKP reference bbox dimensions must be positive");
assert(TENSIONER_SKP_WORLD_SIZE_X > TENSIONER_SKP_WORLD_SIZE_Z,
    "mapped SKP dimensions must satisfy world X > Z");
assert(TENSIONER_SKP_WORLD_SIZE_Z > TENSIONER_SKP_WORLD_SIZE_Y,
    "mapped SKP dimensions must satisfy world Z > Y");
assert(TIMING_FLANGE_R > TIMING_OUTER_R, "timing pulley retaining flange must exceed toothed outer circle");
assert(FRONT_PULLEY_Z < 0 && FRONT_PULLEY_Z > WORLD_PARTITION_FRONT_Z, "front pulley must stay in the drawer bay");
assert(abs(FRONT_PULLEY_Z - DRAWER_FRONT_INTERFACE_Z) < TIMING_PITCH_MM / 2 + 0.01,
    "belt tooth count must keep the front pulley near the drawer interface datum");
assert(SELECTED_COLUMN >= 0 && SELECTED_COLUMN < N_COL, "SELECTED_COLUMN out of range");
assert(SELECTED_ROW >= 0 && SELECTED_ROW < N_ROW, "SELECTED_ROW out of range");
//#endregion

//#region 方法/工具
// Preview examples:
//   openscad -D 'CLUTCH_PART="assembly"' -o assembly.stl cabinet_clutch.scad
//   openscad -D 'CLUTCH_PART="clutch_detail"' -D 'CLUTCH_EXPLODE=8' -D 'ENGAGED=true' -o detail.stl cabinet_clutch.scad
//   openscad -D 'CLUTCH_PART="power_bus"' -o power_bus.stl cabinet_clutch.scad
//#endregion
