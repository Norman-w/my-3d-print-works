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
// the fixed LM3UU seat is printed integral with the mechanism plate, while the
// stepped input shaft and bearings are purchased references
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
SELECTED_ROW = is_undef(SELECTED_ROW) ? 1 : SELECTED_ROW;
// Start the physical validation scene with one known-good center clutch.
// SHOW_LEGACY_STATIONS controls only the retired non-center clutch diagnostics;
// all 15 stations in the default world use the same canonical center assembly
// instance, with the center station kept as the one animated/native source.
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
include <../ch1_03c_params.scad>
include <../parts/drawer_drive_bearings.scad>
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
// The center station is located on the drawer-bottom drive layer.  The front
// pinion is the vertical datum for this layer; the 2GT pulley sits immediately
// below it and the whole clutch pair follows the same belt plane.  Keep the
// old -D override as a compatibility alias, but default the drive-layer
// correction to zero so no unexplained row-center lift can return.
CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM = is_undef(
    CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM
)
    ? (is_undef(CENTER_CLUTCH_VERTICAL_LIFT_MM)
        ? 0.00
        : CENTER_CLUTCH_VERTICAL_LIFT_MM)
    : CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM;
CENTER_CLUTCH_VERTICAL_LIFT_MM = CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM;
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
// The partition is pierced by the belt's XZ plane.  Its X opening follows
// the radial envelope; its Y opening follows the belt axial width, not the
// radial belt thickness.
PARTITION_BELT_PASSAGE_RADIAL_CLEAR = 0.45;
PARTITION_BELT_PASSAGE_AXIAL_CLEAR = 0.45;
// The front/rear compartment partition gets one real, identical 2GT belt
// window per drawer cell. The old 3M partition-window envelope is removed;
// this is not the final removable rear panel at z=-D.
PARTITION_BELT_PASSAGE_WINDOW_RADIAL_CLEAR =
    PARTITION_BELT_PASSAGE_RADIAL_CLEAR;
PARTITION_BELT_PASSAGE_WINDOW_AXIAL_CLEAR =
    PARTITION_BELT_PASSAGE_AXIAL_CLEAR;
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
SNAKE_MOTOR_BOSS_BASE_D = MOTOR_MOUNT_BOSS_STAGE1_BASE_D;
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
// The lower timing pulley sits above the chain return envelope.  Give the
// printed spline shaft a longer lower D stub so a purchased 3×6×2 bearing can
// sit in the fixed partition bar below that pulley; the upper stub remains the
// original short pulley engagement.
VERTICAL_GEAR_BOTTOM_END_STUB_LENGTH = 12.0;
VERTICAL_GEAR_TOP_END_STUB_LENGTH = 6.0;
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
// rack is directly attached under each drawer and moves in +Z with it; the
// fixed front pinion only transmits torque and never carries drawer weight.
DRAWER_RACK_PITCH = 3.0;
DRAWER_RACK_BODY_Y = CENTER_FRONT_RACK_BODY_HEIGHT;
DRAWER_RACK_BODY_X = CENTER_FRONT_RACK_BODY_X;
DRAWER_RACK_TOOTH_H = CENTER_FRONT_RACK_TOOTH_HEIGHT_X;
DRAWER_RACK_TOOTH_OVERHANG_X = CENTER_FRONT_RACK_TOOTH_OVERHANG_X;
DRAWER_RACK_TOOTH_Y_MARGIN = CENTER_FRONT_RACK_TOOTH_Y_MARGIN;
DRAWER_RACK_TO_DRAWER_GAP = 0.00;
DRAWER_GUIDE_RAIL_GAP = 0.30;
DRAWER_GUIDE_C_SLOT_H = DRAWER_GUIDE_681_OD
    + 2 * DRAWER_GUIDE_RAIL_GAP;
DRAWER_GUIDE_C_TOP_LIP_T = 1.20;
DRAWER_GUIDE_C_BOTTOM_RAIL_H = DRAWER_GUIDE_681_OD
    + 2 * DRAWER_GUIDE_RAIL_GAP;
// The cabinet divider/side panel is the C-slot's vertical member. The printed
// rail contributes only the lower support and upper retaining lip, starting at
// that panel's inner face and extending into the current drawer cell. This is
// deliberately not a second wall placed outside the divider: an independent
// wall was the reason the old rail crossed into the neighboring cell.
DRAWER_GUIDE_C_DEPTH = 4.50;
DRAWER_GUIDE_C_FLANGE_T = 2.40;
DRAWER_GUIDE_PARTITION_SUPPORT_T = WORLD_DIV_T;
DRAWER_GUIDE_RAIL_ATTACH_OVERLAP = EPS;
// The drawer side is inset from the partition inner face by DRAWER_CLEAR. The
// flange projects back toward the partition-facing guide, leaving a positive
// end gap at the free end of the inward lip.
DRAWER_GUIDE_C_FLANGE_PROJECTION = 3.00;
DRAWER_GUIDE_C_FLANGE_CLEARANCE = 0.30;
DRAWER_GUIDE_C_FLANGE_END_CLEARANCE = DRAWER_GUIDE_C_DEPTH
    - DRAWER_CLEAR
    - DRAWER_GUIDE_C_FLANGE_PROJECTION;
// The +Z/front roller is the actual lower support for the drawer-side flange.
// Keep nominal contact at the support datum; the 0.30 mm running clearance is
// reserved for the tail roller against the C-slot top/bottom faces.
DRAWER_GUIDE_C_FRONT_SUPPORT_CLEARANCE = 0.00;
DRAWER_GUIDE_ROLLER_Y_OFFSET = 4.00;
DRAWER_GUIDE_ROLLER_Z_MARGIN = 6.00;
DRAWER_GUIDE_TAIL_BEARING_Y_OFFSET = 0.00;
FRONT_GEAR_TEETH = CENTER_FRONT_RACK_GEAR_TEETH;
FRONT_GEAR_TOOTH_DEPTH = CENTER_FRONT_RACK_GEAR_TOOTH_DEPTH;
FRONT_GEAR_T = CENTER_FRONT_RACK_GEAR_THICKNESS;
FRONT_GEAR_PITCH_R = FRONT_GEAR_TEETH * CLUTCH_PITCH_MM / (2 * PI);
FRONT_GEAR_ROOT_R = FRONT_GEAR_PITCH_R - FRONT_GEAR_TOOTH_DEPTH;
FRONT_GEAR_OUTER_R = FRONT_GEAR_PITCH_R + FRONT_GEAR_TOOTH_DEPTH;
DRAWER_PINION_SUPPORT_X = 12.0;
DRAWER_PINION_SUPPORT_CHEEK_Z = 14.0;
DRAWER_PINION_SUPPORT_CHEEK_Y = 3.0;
DRAWER_PINION_SUPPORT_CHEEK_GAP = 0.30;
DRAWER_PINION_SUPPORT_CHEEK_OFFSET =
    FRONT_GEAR_T / 2
    + DRAWER_PINION_SUPPORT_CHEEK_GAP
    + DRAWER_PINION_SUPPORT_CHEEK_Y / 2;
DRAWER_PINION_SUPPORT_SIDE_X = FRONT_GEAR_OUTER_R + 1.20;
DRAWER_PINION_SUPPORT_SIDE_T = 1.40;
// The center first article no longer stacks the timing pulley immediately
// below the front pinion.  It leaves a shelf-thickness bearing in the gap and
// sends the lower 2GT pulley into the next drawer bay on the same D shaft.
CENTER_GT2_FRONT_TIMING_BEARING_GEAR_GAP =
    CENTER_FRONT_DRIVE_BEARING_GEAR_GAP;
CENTER_GT2_FRONT_TIMING_BEARING_PULLEY_GAP =
    COMPOUND_LAYER_GAP + DRAWER_FRONT_TIMING_BEARING_RETAINER_T;
CENTER_GT2_FRONT_D_SHAFT_OVERLAP = 0.50;

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
//   cabinet        closed cabinet shell for standalone geometry checks
//   cabinet_frame  canonical preview frame: outer frame + explicit +X side
//                  plate + front grid + lower face; the front/rear partition
//                  is a separate installed part so it cannot hide the grid
//   cabinet_context canonical frame + optional drawer context
//   power_bus      active motor + five-column 2GT bus and adjustable return wheel
//   all_vertical_axes  active D drive + five drawer axes
//   drawer_drive   rear/front compound wheels, +Z drawer belts and racks
//   clutch         center clutch by default; old stations require SHOW_LEGACY_STATIONS
//   clutch_detail  selected center mechanism (or a legacy station when enabled)
//   motor/motor_body/motor_shaft/left_d_axis/side_axes/column/vertical_rack
//   column_sync_belt_bottom/column_sync_belt_top/column_sync_tensioner
//   center_station_template_assembly  one local center-station assembly kit;
//                                    Three.js places fourteen world instances
//   vertical_spline_bearing_support/vertical_spline_bearings
//   vertical_spline_support_chain_collision/vertical_spline_support_drive_collision
//   vertical_spline_support_partition_window_collision
//   tensioner_t_solid
//   upper_clutch/upper_spur/upper_dog/lower_takeoff/lower_dog/rear_pulley
//   spring/screw/fork/drawer_belt/front_compound/front_pulley/front_gear/drawer_rack
//   world_axes                 native +X/+Y/+Z diagnostic triad at the origin
//                  individual verification pieces for the one-by-one workflow
//
// The center replacement uses the finished CH1 03C pair: a +Z-offset axis-Y
// input male gear with a rounded-triangle/magnet nose enters the fixed output
// female receiver above it. The female body also carries the 2GT rear pulley.
// cabinet_clutch_carrier.scad keeps the male end to one D-round-D shaft: its
// Ø3 round section slides directly in one fixed LM3UU held by a rectangular
// bar formed as part of the mechanism plate, while the lower D enters the Ø8 round
// sleeve with a Ø5×5 magnet pocket. The output side has two independent D
// shafts and two 3×6×2 bearing references in its fixed cage. The other 24
// legacy stations are intentionally suppressed until this physical prototype
// is approved.
// Each of the five drawer-motor spline shafts receives one fixed 3×6×2 bearing
// in a removable 3 mm lower carrier. Eight plain circular Ø5 mm floor bosses
// pass through Ø5.2 mm carrier holes and are clamped by top-entry screws;
// four round Y+ bearing pillars and one C5 motor-side tower run down to the
// carrier top and carry the radial load. The C5 tower uses two symmetric,
// Z-deep rounded trapezoid braces: each brace flares outward at the carrier
// and closes inward at the bearing cap, leaving the motor envelope captured
// without relying on two thin legs. The carrier stays in the open rear cavity
// and is not fused to the partition.
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

function drawer_bottom_y(row) = world_row_y(row) + DRAWER_CLEAR;

function drawer_rack_y(row) = drawer_bottom_y(row)
    - DRAWER_RACK_TO_DRAWER_GAP
    - DRAWER_RACK_BODY_Y / 2;

function drawer_guide_y(row) = drawer_bottom_y(row)
    + DRAWER_GUIDE_ROLLER_Y_OFFSET;

function drawer_left_x(col) = world_col_x(col) + DRAWER_CLEAR;

function drawer_right_x(col) = world_col_x(col)
    + WORLD_BAY_W - DRAWER_CLEAR;

// The left service cheek/internal divider and the right divider/+X side panel
// already provide the vertical C-slot members. These are their inner faces;
// every guide lip grows from here toward the center of its own drawer cell.
function drawer_left_guide_partition_face_x(col) = world_col_x(col);

function drawer_right_guide_partition_face_x(col) = world_col_x(col)
    + WORLD_BAY_W;

function drawer_left_guide_rail_end_x(col) =
    drawer_left_guide_partition_face_x(col) + DRAWER_GUIDE_C_DEPTH;

function drawer_right_guide_rail_end_x(col) =
    drawer_right_guide_partition_face_x(col) - DRAWER_GUIDE_C_DEPTH;

function drawer_left_guide_tail_bearing_x(col) = drawer_left_x(col)
    + DRAWER_GUIDE_C_FLANGE_PROJECTION / 2;

function drawer_right_guide_tail_bearing_x(col) = drawer_right_x(col)
    - DRAWER_GUIDE_C_FLANGE_PROJECTION / 2;

function drawer_left_guide_front_bearing_x(col) =
    drawer_left_guide_tail_bearing_x(col);

function drawer_right_guide_front_bearing_x(col) =
    drawer_right_guide_tail_bearing_x(col);

function drawer_guide_slot_bottom_y(row) = drawer_guide_y(row)
    - DRAWER_GUIDE_C_SLOT_H / 2;

function drawer_guide_flange_y(row) = drawer_guide_y(row);

function drawer_guide_front_bearing_y(row) = drawer_guide_flange_y(row)
    - DRAWER_GUIDE_C_FLANGE_T / 2
    - DRAWER_GUIDE_C_FRONT_SUPPORT_CLEARANCE
    - DRAWER_GUIDE_681_OD / 2;

function drawer_rack_z0() = WORLD_PARTITION_FRONT_Z + 1.5;

function drawer_rack_z1(front_z) = front_z - 3.5;

function drawer_guide_z0(front_z) = drawer_rack_z0() + 2.0;

function drawer_guide_z1(front_z) = drawer_rack_z1(front_z) - 2.0;

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
    drawer_rack_y(row);

function selected_col() = min(max(0, SELECTED_COLUMN), N_COL - 1);

function selected_row() = min(max(0, SELECTED_ROW), N_ROW - 1);

// Only the center station is migrated to the finished CH1 03C mechanism.
// Columns and rows are zero-based, so this is the middle cell of the 5×3
// drawer field.  Its new mating axis is deliberately on the +Z side of the
// existing vertical 12T / 3 mm shaft.
CENTER_GT2_COL = floor(N_COL / 2);
CENTER_GT2_ROW = floor(N_ROW / 2);
CENTER_GT2_FRONT_PULLEY_ROW = CENTER_GT2_ROW - 1;
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
PARTITION_BELT_PASSAGE_WINDOW_SLOT_CENTER_OFFSET =
    CENTER_GT2_BELT_BASE_INNER_R + CENTER_GT2_BELT_T / 2;
PARTITION_BELT_PASSAGE_WINDOW_SLOT_HALF_X = CENTER_GT2_BELT_T / 2
    + CENTER_GT2_BELT_TOOTH_H
    + PARTITION_BELT_PASSAGE_WINDOW_RADIAL_CLEAR
    + GT2_BELT_RADIAL_CLEARANCE;
PARTITION_BELT_PASSAGE_WINDOW_HALF_X =
    PARTITION_BELT_PASSAGE_WINDOW_SLOT_CENTER_OFFSET
    + PARTITION_BELT_PASSAGE_WINDOW_SLOT_HALF_X;
PARTITION_BELT_PASSAGE_WINDOW_AXIAL_WIDTH = GT2_BELT_WIDTH
    + 2 * PARTITION_BELT_PASSAGE_WINDOW_AXIAL_CLEAR;

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

function center_gt2_front_gear_y(row) =
    drawer_rack_y(row) + CENTER_FRONT_DRIVE_LIFT_MM;

function center_gt2_front_pinion_lower_y(row) =
    center_gt2_front_gear_y(row) - FRONT_GEAR_T / 2;

function center_gt2_front_timing_bearing_upper_y(row) =
    center_gt2_front_pinion_lower_y(row)
        - CENTER_GT2_FRONT_TIMING_BEARING_GEAR_GAP;

function center_gt2_front_timing_bearing_center_y(row) =
    center_gt2_front_timing_bearing_upper_y(row)
        - DRAWER_FRONT_TIMING_BEARING_W / 2;

function center_gt2_front_timing_bearing_lower_y(row) =
    center_gt2_front_timing_bearing_center_y(row)
        - DRAWER_FRONT_TIMING_BEARING_W / 2;

function center_gt2_front_shelf_lower_y(row) =
    world_row_y(row) - WORLD_SHELF_T;

function center_gt2_front_bearing_boss_bottom_y(row) =
    center_gt2_front_timing_bearing_lower_y(row)
        - DRAWER_FRONT_TIMING_BEARING_RETAINER_T
        - CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS;

function center_gt2_front_timing_pulley_row(row) = row - 1;

function center_gt2_front_pulley_top_offset_y() =
    GT2_PULLEY_FACE_T / 2 + GT2_BELT_GUIDE_LIP_T;

// The front pinion meshes with the lifted rack datum above the intact shelf.
// The timing pulley is deliberately kept in the next lower drawer bay; the
// extra vertical separation is carried by the longer D shaft and the
// shelf-thickness bearing, rather than by sinking the rack into the shelf.
function center_gt2_belt_y(row) =
    center_gt2_front_timing_bearing_lower_y(row)
        - CENTER_FRONT_DRIVE_LIFT_MM
        - CENTER_GT2_FRONT_TIMING_BEARING_PULLEY_GAP
        - center_gt2_front_pulley_top_offset_y()
        + CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM;

function center_gt2_female_base_y(row) =
    center_gt2_belt_y(row)
        + GT2_BELT_LOWER_RETAINER_T
        + GT2_PULLEY_FACE_T / 2;

function center_gt2_male_base_y(row) =
    center_gt2_female_base_y(row)
        - GT2_MOTHER_GAP
        - gt2_female_total_h()
        - gt2_male_total_h();

function center_gt2_male_tip_y(row) =
    center_gt2_male_base_y(row) + gt2_male_total_h();

function center_gt2_pulley_base_y(belt_y) =
    belt_y - GT2_BELT_LOWER_RETAINER_T - GT2_PULLEY_FACE_T / 2;

function center_gt2_pulley_top_y(belt_y) =
    center_gt2_pulley_base_y(belt_y)
        + GT2_BELT_LOWER_RETAINER_T
        + GT2_PULLEY_FACE_T
        + GT2_BELT_GUIDE_LIP_T;

function center_gt2_front_d_shaft_start_y(row) =
    center_gt2_pulley_base_y(center_gt2_belt_y(row))
        - CENTER_GT2_FRONT_D_SHAFT_OVERLAP;

function center_gt2_front_d_shaft_end_y(row) =
    center_gt2_front_gear_y(row)
        + FRONT_GEAR_T / 2
        + CENTER_GT2_FRONT_D_SHAFT_OVERLAP;

function center_gt2_front_d_shaft_length(row) =
    center_gt2_front_d_shaft_end_y(row)
        - center_gt2_front_d_shaft_start_y(row);

// The front/rear partition is one repeated datum: every drive cell sends its
// timing belt into the next lower bay, just as center R3C3 sends its belt into
// CENTER_GT2_FRONT_PULLEY_ROW.  The portal keeps the same normalized
// in-bay position as that center pulley.  This is deliberately separate from
// the live station belt function above because the legacy 3M mechanisms may
// retain their own pulley stack while the partition openings share one
// normalized placement.
function drawer_partition_belt_y(row) =
    center_gt2_belt_y(CENTER_GT2_ROW)
        + world_row_center_y(
            row + CENTER_GT2_FRONT_PULLEY_ROW - CENTER_GT2_ROW
        )
        - world_row_center_y(CENTER_GT2_FRONT_PULLEY_ROW);

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

module spur_gear_y(
    x,
    y,
    z,
    teeth,
    pitch_mm,
    tooth_depth,
    thickness,
    bore_d = 3.2,
    bore_type = "round"
) {
    pitch_r = teeth * pitch_mm / (2 * PI);
    // The profile is in XZ and the axis is world +Y.
    translate([x, y - thickness / 2, z])
        rotate([-90, 0, 0])
            difference() {
                linear_extrude(height = thickness, convexity = 8)
                    gear_profile_2d(teeth, pitch_r - tooth_depth, pitch_r + tooth_depth);
                if (bore_type == "d")
                    linear_extrude(height = thickness + 2 * EPS)
                        d_profile_2d(bore_d, ROD_FLAT_DEPTH, ROD_CLEARANCE);
                else
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

// The active R3C3 belt is a closed loop in XZ around the center clutch pulley
// and the drawer-front pulley.  At either intermediate plate (the cabinet
// partition or the removable mechanism plate) its section is not one wide
// rectangle: it is two straight radial strips at +/- the pitch-radius datum.
// Keep the bridge between those strips solid and derive both cuts from the
// same belt envelope used by center_gt2_belt_loop_z().  Legacy stations are
// intentionally not included here because their clutches/belts are hidden
// and are not the current mechanical assembly truth.
module center_gt2_belt_straight_passage_slots(
    x,
    y,
    z0,
    z_depth,
    radial_clear,
    axial_clear
) {
    path_min_z = min(CENTER_GT2_Z, CENTER_GT2_FRONT_PULLEY_Z);
    path_max_z = max(CENTER_GT2_Z, CENTER_GT2_FRONT_PULLEY_Z);
    slot_center_offset = CENTER_GT2_BELT_BASE_INNER_R
        + CENTER_GT2_BELT_T / 2;
    // The belt back envelope occupies +/- T/2 around each strip centre, but
    // the printed tooth prism extends inward by CENTER_GT2_BELT_TOOTH_H.
    // Include that real tooth envelope before applying the plate clearance;
    // otherwise the inner tooth tips still bite the solid bridge.
    slot_half_x = CENTER_GT2_BELT_T / 2
        + CENTER_GT2_BELT_TOOTH_H
        + radial_clear;
    assert(z_depth > 0, "center belt passage depth must be positive");
    assert(radial_clear >= 0 && axial_clear >= 0,
        "center belt passage clearances must be non-negative");
    assert(z0 > path_min_z - EPS
            && z0 + z_depth < path_max_z + EPS,
        "belt passage plate must cross the center belt straight run");
    for (side = [-1, 1])
        translate([
            x + side * slot_center_offset - slot_half_x,
            y - GT2_BELT_WIDTH / 2 - axial_clear,
            z0
        ])
            cube([
                2 * slot_half_x,
                GT2_BELT_WIDTH + 2 * axial_clear,
                z_depth
            ]);
}

// The front/rear compartment partition is perpendicular to the belt's
// straight Z run. It therefore needs one real window covering the two belt
// strips and the small bridge between them. This is intentionally separate
// from the mechanism plate's two-slot cut: the partition is the fixed cabinet
// datum, while the removable plate keeps its bridge for stiffness.
module center_gt2_belt_partition_window(
    x,
    y,
    z0,
    z_depth,
    radial_clear,
    axial_clear
) {
    path_min_z = min(CENTER_GT2_Z, CENTER_GT2_FRONT_PULLEY_Z);
    path_max_z = max(CENTER_GT2_Z, CENTER_GT2_FRONT_PULLEY_Z);
    slot_center_offset = PARTITION_BELT_PASSAGE_WINDOW_SLOT_CENTER_OFFSET;
    slot_half_x = CENTER_GT2_BELT_T / 2
        + CENTER_GT2_BELT_TOOTH_H
        + radial_clear;
    window_half_x = slot_center_offset + slot_half_x;
    assert(z_depth > 0, "center belt partition window depth must be positive");
    assert(radial_clear >= 0 && axial_clear >= 0,
        "partition belt passage clearances must be non-negative");
    assert(z0 > path_min_z - EPS
            && z0 + z_depth < path_max_z + EPS,
        "partition belt window must cross the center belt straight run");
    translate([
        x - window_half_x,
        y - GT2_BELT_WIDTH / 2 - axial_clear,
        z0
    ])
        cube([
            2 * window_half_x,
            GT2_BELT_WIDTH + 2 * axial_clear,
            z_depth
        ]);
}

module all_drawer_belt_partition_windows() {
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1]) {
            // Every cell uses the same center 2GT straight-run envelope;
            // there is no wider legacy 3M partition opening anymore.
            center_gt2_belt_partition_window(
                clutch_col_x(col),
                drawer_partition_belt_y(row),
                WORLD_PARTITION_BACK_Z - EPS,
                WORLD_PARTITION_T + 2 * EPS,
                GT2_BELT_RADIAL_CLEARANCE
                    + PARTITION_BELT_PASSAGE_WINDOW_RADIAL_CLEAR,
                PARTITION_BELT_PASSAGE_WINDOW_AXIAL_CLEAR
            );
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
                ROD_FLAT_DEPTH,
                VERTICAL_GEAR_BOTTOM_END_STUB_LENGTH,
                VERTICAL_GEAR_TOP_END_STUB_LENGTH
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
    rack_face_x = center_front_rack_face_x(x);
    rack_body_y = y - DRAWER_RACK_BODY_Y / 2;
    color(COLOR_RACK) {
        // The top of this solid backing is flush with the drawer underside;
        // the whole rack therefore follows the drawer in +Z. Its tooth height
        // is radial in X, so the fixed +Y-axis pinion can mesh with it.
        translate([rack_face_x, rack_body_y, z0])
            cube([DRAWER_RACK_BODY_X, DRAWER_RACK_BODY_Y, length]);
        for (rack_z = [z0 + DRAWER_RACK_PITCH / 2:DRAWER_RACK_PITCH:z1 - DRAWER_RACK_PITCH / 2])
            translate([
                rack_face_x - DRAWER_RACK_TOOTH_H,
                rack_body_y + DRAWER_RACK_TOOTH_Y_MARGIN,
                rack_z - 0.42
            ])
                cube([
                    DRAWER_RACK_TOOTH_H + DRAWER_RACK_TOOTH_OVERHANG_X,
                    DRAWER_RACK_BODY_Y - 2 * DRAWER_RACK_TOOTH_Y_MARGIN,
                    0.84
                ]);
    }
}

module drawer_c_guide_rail_at(col, row, front_z, side) {
    z0 = drawer_guide_z0(front_z);
    z1 = drawer_guide_z1(front_z);
    length = z1 - z0;
    partition_face_x = side < 0
        ? drawer_left_guide_partition_face_x(col)
        : drawer_right_guide_partition_face_x(col);
    rail_end_x = side < 0
        ? drawer_left_guide_rail_end_x(col)
        : drawer_right_guide_rail_end_x(col);
    // Start a tiny amount inside the real divider/side panel so the two
    // separately previewed meshes have a positive structural overlap. There
    // is no printed C-slot back wall here: the cabinet panel is that wall.
    x_min = side < 0
        ? partition_face_x - DRAWER_GUIDE_RAIL_ATTACH_OVERLAP
        : rail_end_x;
    depth = abs(rail_end_x - partition_face_x)
        + DRAWER_GUIDE_RAIL_ATTACH_OVERLAP;
    y = drawer_guide_y(row);
    slot_bottom = drawer_guide_slot_bottom_y(row);
    total_bottom = slot_bottom - DRAWER_GUIDE_C_BOTTOM_RAIL_H;
    front_bearing_x = side < 0
        ? drawer_left_guide_front_bearing_x(col)
        : drawer_right_guide_front_bearing_x(col);
    front_bearing_y = drawer_guide_front_bearing_y(row);
    difference() {
        color("#657f8c")
            union() {
                // The fixed divider/side panel is the vertical member of the
                // C. These two inward lips are the only new guide geometry;
                // left grows +X and right grows -X into this cell.
                translate([x_min, total_bottom, z0])
                    cube([
                        depth,
                        DRAWER_GUIDE_C_BOTTOM_RAIL_H,
                        length
                    ]);
                translate([
                    x_min,
                    slot_bottom + DRAWER_GUIDE_C_SLOT_H,
                    z0
                ])
                    cube([
                        depth,
                        DRAWER_GUIDE_C_TOP_LIP_T,
                        length
                    ]);
            }
        // The front support 681 is seated in the lower inward lip, with its
        // axis along X. Only the local seat is opened; the lip remains a
        // solid captive support along the rest of its Z travel.
        translate([
            front_bearing_x,
            front_bearing_y,
            z1 - DRAWER_GUIDE_ROLLER_Z_MARGIN
        ])
            rotate([0, 90, 0])
                cylinder(
                    d = DRAWER_GUIDE_681_SEAT_D,
                    h = DRAWER_GUIDE_681_W + 2 * EPS,
                    center = true,
                    $fn = 48
                );
    }
}

module drawer_c_guide_flanges_at(col, row, front_z) {
    z0 = drawer_guide_z0(front_z);
    z1 = drawer_guide_z1(front_z);
    length = z1 - z0;
    y = drawer_guide_flange_y(row);
    color("#9a77c7") {
        // The drawer-side bearing flange now points toward the drawer centre,
        // matching the partition-integral inward lips. It no longer projects
        // through the divider into the neighboring cell.
        translate([
            drawer_left_x(col),
            y - DRAWER_GUIDE_C_FLANGE_T / 2,
            z0
        ])
            cube([
                DRAWER_GUIDE_C_FLANGE_PROJECTION,
                DRAWER_GUIDE_C_FLANGE_T,
                length
            ]);
        translate([
            drawer_right_x(col) - DRAWER_GUIDE_C_FLANGE_PROJECTION,
            y - DRAWER_GUIDE_C_FLANGE_T / 2,
            z0
        ])
            cube([
                DRAWER_GUIDE_C_FLANGE_PROJECTION,
                DRAWER_GUIDE_C_FLANGE_T,
                length
            ]);
    }
}

module drawer_rack_guide_rails_at(col, row, front_z) {
    drawer_c_guide_rail_at(col, row, front_z, -1);
    drawer_c_guide_rail_at(col, row, front_z, 1);
}

module drawer_rack_guide_rollers(col, row, front_z) {
    z0 = drawer_guide_z0(front_z);
    z1 = drawer_guide_z1(front_z);
    tail_z = z0 + DRAWER_GUIDE_ROLLER_Z_MARGIN;
    front_z_bearing = z1 - DRAWER_GUIDE_ROLLER_Z_MARGIN;
    // Two tail bearings travel with the drawer flange. Their axes are ±X,
    // and their outer rings react the drawer's ±Y load in the C slots.
    color("#cfd4da") {
        drawer_drive_681_bearing_x(
            drawer_left_guide_tail_bearing_x(col),
            drawer_guide_flange_y(row) + DRAWER_GUIDE_TAIL_BEARING_Y_OFFSET,
            tail_z
        );
        drawer_drive_681_bearing_x(
            drawer_right_guide_tail_bearing_x(col),
            drawer_guide_flange_y(row) + DRAWER_GUIDE_TAIL_BEARING_Y_OFFSET,
            tail_z
        );
        // Two fixed front lower bearings lift the drawer-side flange at the
        // +Z/front end. They sit in the C rail's bottom support, also on X.
        drawer_drive_681_bearing_x(
            drawer_left_guide_front_bearing_x(col),
            drawer_guide_front_bearing_y(row),
            front_z_bearing
        );
        drawer_drive_681_bearing_x(
            drawer_right_guide_front_bearing_x(col),
            drawer_guide_front_bearing_y(row),
            front_z_bearing
        );
    }
}

module drawer_front_pinion_bearing_support(
    x,
    gear_y,
    z,
    include_lower_mr63 = true,
    include_bearings = true
) {
    // Legacy stations retain two separate fixed cheeks.  The center station
    // replaces the lower cheek with the shelf-thickness timing-bearing
    // support below, so the D shaft can continue to the lower pulley without
    // stacking two supports into the same inter-layer gap.
    bearing_sides = include_lower_mr63 ? [-1, 1] : [1];
    for (side = bearing_sides) {
        bearing_y = gear_y + side * DRAWER_PINION_SUPPORT_CHEEK_OFFSET;
        color("#536d78")
            difference() {
                translate([
                    x - DRAWER_PINION_SUPPORT_X / 2,
                    bearing_y - DRAWER_PINION_SUPPORT_CHEEK_Y / 2,
                    z - DRAWER_PINION_SUPPORT_CHEEK_Z / 2
                ])
                    cube([
                        DRAWER_PINION_SUPPORT_X,
                        DRAWER_PINION_SUPPORT_CHEEK_Y,
                        DRAWER_PINION_SUPPORT_CHEEK_Z
                    ]);
                cylinder_y(
                    x,
                    bearing_y - DRAWER_PINION_SUPPORT_CHEEK_Y / 2 - EPS,
                    z,
                    DRAWER_PINION_MR63_SEAT_D,
                    DRAWER_PINION_SUPPORT_CHEEK_Y + 2 * EPS
                );
                // M3 clearance holes let each cheek fasten to a fixed front
                // frame; the holes are not used to retain the bearing.
                for (mx = [-4.0, 4.0])
                    translate([
                        x + mx,
                        bearing_y,
                        z - DRAWER_PINION_SUPPORT_CHEEK_Z / 2 - EPS
                    ])
                        cylinder(
                            d = 3.40,
                            h = DRAWER_PINION_SUPPORT_CHEEK_Z + 2 * EPS,
                            $fn = 40
                        );
            }
        if (include_bearings)
            color("#cfd4da")
                drawer_drive_mr63_bearing_y(x, bearing_y, z);
    }
}

// This is the shelf-integrated bearing support. The front rack and pinion are
// above the shelf, so there is no rack slot or circular pinion cut in the
// shelf. A printed Ø8 mm reinforcement disc sits below the shelf and carries
// the lower Ø6.10 bearing seat; the Ø3.40 through-bore leaves the annulus
// that prevents the 3×6×2 bearing from dropping into the next bay.
module center_gt2_front_shelf_bearing_boss(
    col,
    row,
    front_z,
    include_bearing = false
) {
    x = clutch_col_x(col);
    bearing_lower_y = center_gt2_front_timing_bearing_lower_y(row);
    boss_bottom_y = bearing_lower_y
        - DRAWER_FRONT_TIMING_BEARING_RETAINER_T
        - CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS;
    difference() {
        color("#536d78")
            cylinder_y(
                x,
                boss_bottom_y,
                front_z,
                CENTER_FRONT_BEARING_REINFORCEMENT_DISC_DIAMETER,
                CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS
                    + DRAWER_FRONT_TIMING_BEARING_RETAINER_T
                    + EPS
            );
        cylinder_y(
            x,
            bearing_lower_y - EPS,
            front_z,
            DRAWER_FRONT_TIMING_BEARING_SEAT_D,
            DRAWER_FRONT_TIMING_BEARING_W + 2 * EPS
        );
        cylinder_y(
            x,
            boss_bottom_y - EPS,
            front_z,
            DRAWER_FRONT_TIMING_BEARING_RETAINER_BORE_D,
            DRAWER_FRONT_TIMING_BEARING_RETAINER_T
                + CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS
                + 2 * EPS
        );
    }
    if (include_bearing)
        color("#cfd4da")
            drawer_drive_front_timing_bearing_y(
                x,
                center_gt2_front_timing_bearing_center_y(row),
                front_z
            );
}

module center_gt2_front_shelf_bearing_cuts(col, row, front_z) {
    x = clutch_col_x(col);
    bearing_lower_y = center_gt2_front_timing_bearing_lower_y(row);
    boss_bottom_y = center_gt2_front_bearing_boss_bottom_y(row);
    cylinder_y(
        x,
        bearing_lower_y - EPS,
        front_z,
        DRAWER_FRONT_TIMING_BEARING_SEAT_D,
        DRAWER_FRONT_TIMING_BEARING_W + 2 * EPS
    );
    cylinder_y(
        x,
        boss_bottom_y - EPS,
        front_z,
        DRAWER_FRONT_TIMING_BEARING_RETAINER_BORE_D,
        DRAWER_FRONT_TIMING_BEARING_RETAINER_T
            + CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS
            + 2 * EPS
    );
}

module drawer_front_drive_guide_system(col, row, front_z) {
    // These two drawer-side runners enter the inward-facing C slots; they
    // move with the drawer and carry the tail bearing pair.
    drawer_c_guide_flanges_at(col, row, front_z);
    drawer_rack_guide_rails_at(col, row, front_z);
    drawer_rack_guide_rollers(col, row, front_z);
    if (is_center_gt2_station(col, row)) {
        // The center pinion has no upper MR63 cheek. Its only front-drive
        // rotary support is the 3×6×2 bearing seated in the shelf-integrated
        // stepped boss.
        center_gt2_front_shelf_bearing_boss(col, row, front_z, true);
    } else {
        drawer_front_pinion_bearing_support(
            clutch_col_x(col),
            drawer_front_gear_y(row),
            front_z,
            true
        );
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
        if (j == CENTER_GT2_ROW)
            difference() {
                union() {
                    translate([
                        WORLD_GRID_ORIGIN_X,
                        world_row_y(j) - WORLD_SHELF_T,
                        WORLD_PARTITION_FRONT_Z
                    ])
                        cube([
                            WORLD_GRID_W + EPS,
                            WORLD_SHELF_T,
                            -WORLD_PARTITION_FRONT_Z + EPS
                        ]);
                    // The shelf and this stepped boss are one cabinet feature;
                    // only the metal 3×6×2 bearing is shown as a purchase item.
                    center_gt2_front_shelf_bearing_boss(
                        CENTER_GT2_COL,
                        j,
                        CENTER_GT2_FRONT_PULLEY_Z,
                        false
                    );
                }
                center_gt2_front_shelf_bearing_cuts(
                    CENTER_GT2_COL,
                    j,
                    CENTER_GT2_FRONT_PULLEY_Z
                );
            }
        else
            translate([WORLD_GRID_ORIGIN_X, world_row_y(j) - WORLD_SHELF_T, WORLD_PARTITION_FRONT_Z])
                cube([WORLD_GRID_W + EPS, WORLD_SHELF_T, -WORLD_PARTITION_FRONT_Z + EPS]);
    translate([WORLD_GRID_ORIGIN_X, WORLD_GRID_ORIGIN_Y - WORLD_SHELF_T, WORLD_PARTITION_FRONT_Z])
        cube([WORLD_GRID_W + EPS, WORLD_SHELF_T, -WORLD_PARTITION_FRONT_Z + EPS]);
}

// Canonical cabinet-frame geometry for the browser and assembly context.
//
// The user-facing cabinet is deliberately an open structural frame, not a
// second closed shell: the outer XZ/YZ frame members run through the full
// depth, but the drawer XZ shelves and YZ dividers exist only in the front
// drawer bay (-FRONT_NET..0).  The rear box (-D..-FRONT_NET) stays one open,
// unobstructed cavity.  The XY front plane has only the lower service face.
// This avoids the coincident shell/context pair that previously hid the
// mechanism and made the cabinet look like two overlapping models.
module cabinet_frame_outer() {
    union() {
        // Full-depth lower and upper XZ frame members.
        translate([0, 0, -D])
            cube([W, WALL, D]);
        translate([0, H - WALL, -D])
            cube([W, WALL, D]);

        // Full-depth left YZ frame member.  The +X member is a named plate
        // below so the assembly tree can distinguish it from the rails.
        translate([0, 0, -D])
            cube([WALL, H, D]);
    }
}

module cabinet_frame_xplus_side_panel() {
    // Solid YZ side plate at the +X boundary.  It runs through the rear
    // cavity and is the datum for the right-hand side of the open frame.
    translate([W - WALL, 0, -D])
        cube([WALL, H, D]);
}

module cabinet_frame_grid() {
    // Drawer-area shelves, including the shelf over the lower service bay.
    // Do not extend these into the rear box: its full depth remains open.
    for (j = [0:N_ROW - 1])
        translate([
            WORLD_GRID_ORIGIN_X,
            world_row_y(j) - WORLD_SHELF_T,
            WORLD_PARTITION_FRONT_Z
        ])
            cube([WORLD_GRID_W, WORLD_SHELF_T, -WORLD_PARTITION_FRONT_Z]);

    // Drawer-area vertical dividers; each spans only the front drawer bay.
    for (i = [1:N_COL - 1])
        translate([
            world_col_x(i) - WORLD_DIV_T,
            WORLD_GRID_ORIGIN_Y,
            WORLD_PARTITION_FRONT_Z
        ])
            cube([WORLD_DIV_T, WORLD_GRID_H, -WORLD_PARTITION_FRONT_Z]);
}

module cabinet_frame_front_service_cheek() {
    // The left 20 mm return/service corridor has its own full-height front
    // divider. The printable cabinet already has this as front_service_cheek
    // in cabinet.scad; the canonical preview frame had accidentally omitted
    // it, leaving one vertical board missing at the left edge of the 5-column
    // drawer grid. Keep the small EPS overlap so it fuses to the shelves and
    // to the service floor without creating a naked coincident edge.
    translate([
        WALL - EPS,
        WORLD_GRID_ORIGIN_Y,
        WORLD_PARTITION_FRONT_Z
    ])
        cube([
            SERVICE_W + 2 * EPS,
            WORLD_GRID_H + EPS,
            -WORLD_PARTITION_FRONT_Z + EPS
        ]);
}

module cabinet_frame_front_lower_face() {
    // Only the front lower service bay is a solid XY face.  The upper drawer
    // fronts remain open so the layers and mechanism can be inspected.
    translate([0, 0, -WALL])
        cube([W, WORLD_GRID_ORIGIN_Y, WALL]);
}

module clutch_cabinet_frame() {
    difference() {
        union() {
            cabinet_frame_outer();
            cabinet_frame_xplus_side_panel();
            cabinet_frame_grid();
            cabinet_frame_front_service_cheek();
            cabinet_frame_front_lower_face();
            // The world preview uses this open frame as its single cabinet
            // carrier. Keep the motor's four round base bosses and Ø5 x 12
            // guide posts in that same canonical mesh; they used to exist
            // only in clutch_cabinet_shell(), so the close-up showed them
            // while the world assembly silently omitted them.
            snake_motor_mount_bosses();
            vertical_spline_bearing_floor_bosses();
        }
        snake_motor_mount_boss_floor_bores();
        vertical_spline_bearing_floor_boss_pilot_holes();
    }
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
    // Reuse the same four round base bosses, solid guide posts, and top-open
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
            vertical_spline_bearing_floor_bosses();
        }
        snake_motor_mount_boss_floor_bores();
        vertical_spline_bearing_floor_boss_pilot_holes();
    }
}

module clutch_partition_with_belt_passages() {
    cabinet_frame_partition_with_belt_passage();
}

// The full-size XY plate at the rear edge of the drawer bay is the fixed
// front/rear compartment partition. It is not the thin removable rear panel
// at z=-D: the rear service cavity behind this partition remains open through
// the outer frame. Every drawer cell has its own true belt passage and the
// same four-corner Boss mounting datum; the center cell is the 2GT first
// article and the other cells retain their 3M envelope.
module cabinet_frame_partition_with_belt_passage() {
    difference() {
        union() {
            world_partition_plate();
            // Repeat the same relative Boss pattern in every one of the 15
            // drawer cells. The center mechanism plate is the reference
            // geometry; the other cells receive the same mounting datums.
            for (row = [0:N_ROW - 1])
                for (col = [0:N_COL - 1])
                    center_clutch_partition_mount_bosses(col, row);
        }
        // Fifteen actual drawer-cell windows: center R3C3 uses the migrated
        // 2GT straight run; the other fourteen use the 3M envelope. All
        // fifteen windows use the center cell's normalized relative Y datum.
        // The final rear panel is not part of these cuts.
        all_drawer_belt_partition_windows();
    }
}

module clutch_cabinet_context(include_drawers = true, include_partition = true) {
    color(COLOR_CABINET, 0.38) clutch_cabinet_frame();
    if (include_partition)
        // Keep the installed partition separate from the frame mesh. This is
        // a display/assembly split only; its fixed location and real passage
        // remain defined by clutch_partition_with_belt_passages().
        color(COLOR_CABINET, 0.16) clutch_partition_with_belt_passages();
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
    vertical_spline_bearing_support_bars();
    vertical_spline_bearing_references();
    power_column_sync_belts();
    column_sync_tensioner();
}
//#endregion

// The center prototype is deliberately split into one removable mechanism
// plate with integral fixed LM3UU and output bearing-bar seats, stepped input
// shaft/sleeve and purchased-part references. Keeping this include after the
// world-coordinate helpers
// makes the carrier consume the same station datums as the rotors.
include <cabinet_clutch_carrier.scad>

// The snake-chain service runs use the bottom edge of the open male-sleeve
// magnet as their vertical datum.  The chain source is authored in XZ and is
// rotated into the browser's native world frame, so its path "z" becomes the
// world Y height. The lower guide loop has its own raised center so the
// shifted return run remains floor-safe without changing the 03C pin count.
SNAKE_CHAIN_HEIGHT_DATUM = "input-sleeve-magnet-bottom";
SNAKE_CHAIN_REFERENCE_ROW = CENTER_GT2_ROW - 1;
SNAKE_CHAIN_LINK_TOP_OFFSET_MM = h2 / 2;
SNAKE_CHAIN_INPUT_SLEEVE_MAGNET_OPEN_BOTTOM_Y_MM =
    center_clutch_input_sleeve_bottom_y(CENTER_GT2_ROW) + 0.10;
SNAKE_CHAIN_REFERENCE_PATH_CENTER_Y_MM =
    row_center_z(SNAKE_CHAIN_REFERENCE_ROW);
SNAKE_CHAIN_VERTICAL_SHIFT_MM =
    SNAKE_CHAIN_INPUT_SLEEVE_MAGNET_OPEN_BOTTOM_Y_MM
        - SNAKE_CHAIN_LINK_TOP_OFFSET_MM
        - SNAKE_CHAIN_REFERENCE_PATH_CENTER_Y_MM;
SNAKE_CHAIN_SERVICE_PATH_CENTER_Y_MM =
    row_center_z(0) - ROW_PITCH + SNAKE_CHAIN_VERTICAL_SHIFT_MM;
// The service run is shifted down to the magnet datum.  The paired upper
// return guide and lower service-press guide are deliberately staggered in
// opposite X directions; the corrected internal-tangent route is re-solved
// by scripts/solve_cabinet_chain.py and closes at 260 pins.
SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y_MM = 41.20;
SNAKE_CHAIN_RETURN_DRIVE_X_TRIM_MM = -4.00;
SNAKE_CHAIN_SERVICE_PRESS_X_TRIM_MM = 16.00;
SNAKE_CHAIN_MOTOR_X_OFFSET_MM = -2.00;
SNAKE_CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX = 182;
SNAKE_CHAIN_TRIGGER_MAGNET_D = GT2_MAGNET_NOMINAL_D;
SNAKE_CHAIN_TRIGGER_MAGNET_L = GT2_MAGNET_POCKET_H;
SNAKE_CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM =
    (h2 - SNAKE_CHAIN_TRIGGER_MAGNET_D) / 2;
SNAKE_CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM = 0.00;
SNAKE_CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM = outer_face + 0.05;

// The five long Y-axis spline shafts are radially captured at their lower D
// stubs by one removable 3 mm carrier whose bottom is coplanar with the
// cabinet floor top. Eight plain circular Ø5 mm floor bosses pass through its
// Ø5.2 mm holes and clamp the carrier from its top; they sit in the four gaps
// between the five bearing towers. The bearing towers rise from that carrier
// in +Y.
// The C5 tower uses two Z-deep rounded trapezoid braces so the purchased motor
// body remains clear while the bearing load has a broad, printable path into
// the removable carrier. The top offset is the motor-clearance datum; the
// larger bottom offset and root section make the XY profile read /|   |\\.
SNAKE_CHAIN_GUIDE_TEETH = 8;
SNAKE_CHAIN_DRIVE_TEETH = 12;
SNAKE_CHAIN_GUIDE_PITCH_R_MM =
    P / (2 * sin(180 / SNAKE_CHAIN_GUIDE_TEETH));
SNAKE_CHAIN_DRIVE_PITCH_R_MM =
    P / (2 * sin(180 / SNAKE_CHAIN_DRIVE_TEETH));
SNAKE_CHAIN_GUIDE_OUTER_R_MM =
    SNAKE_CHAIN_GUIDE_PITCH_R_MM + 0.12 * P;
SNAKE_CHAIN_DRIVE_OUTER_R_MM =
    SNAKE_CHAIN_DRIVE_PITCH_R_MM + 0.38 * P;
SNAKE_CHAIN_GUIDE_ANCHOR_DX_MM =
    SNAKE_CHAIN_DRIVE_PITCH_R_MM - SNAKE_CHAIN_GUIDE_PITCH_R_MM;
SNAKE_CHAIN_WALL_INSET_MM =
    WALL + SNAKE_CHAIN_DRIVE_OUTER_R_MM + 0.40;
SNAKE_CHAIN_LEFT_VERTICAL_GUIDE_X_MM =
    clutch_col_x(0)
        - ((W - SNAKE_CHAIN_WALL_INSET_MM)
            - clutch_col_x(N_COL - 1))
        - SNAKE_CHAIN_GUIDE_ANCHOR_DX_MM;
SNAKE_CHAIN_RIGHT_VERTICAL_GUIDE_X_MM =
    W - SNAKE_CHAIN_WALL_INSET_MM + SNAKE_CHAIN_GUIDE_ANCHOR_DX_MM;
SNAKE_CHAIN_RETURN_DRIVE_X_MM =
    SNAKE_CHAIN_WALL_INSET_MM
        + 2 * SNAKE_CHAIN_DRIVE_PITCH_R_MM
        + SNAKE_CHAIN_GUIDE_PITCH_R_MM
        + SNAKE_CHAIN_RETURN_DRIVE_X_TRIM_MM;
SNAKE_CHAIN_SERVICE_PRESS_X_MM =
    SNAKE_CHAIN_WALL_INSET_MM
        + 2 * SNAKE_CHAIN_DRIVE_PITCH_R_MM
        + SNAKE_CHAIN_GUIDE_PITCH_R_MM
        + SNAKE_CHAIN_SERVICE_PRESS_X_TRIM_MM;

VERTICAL_SPLINE_BEARING_NOMINAL = "3x6x2";
VERTICAL_SPLINE_BEARING_ID_MM = 3.0;
VERTICAL_SPLINE_BEARING_OD_MM = 6.0;
VERTICAL_SPLINE_BEARING_WIDTH_MM = 2.0;
VERTICAL_SPLINE_BEARING_SEAT_D_MM = 6.10;
VERTICAL_SPLINE_BEARING_CHAIN_TOP_Y_MM =
    SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y_MM
        + SNAKE_CHAIN_GUIDE_OUTER_R_MM;
VERTICAL_SPLINE_BEARING_LOWER_PULLEY_BOTTOM_Y_MM =
    BUS_BOTTOM_Y - GT2_BELT_LOWER_RETAINER_T - GT2_PULLEY_FACE_T / 2;
// The carrier bottom is coplanar with the cabinet floor top.  Each floor Boss
// is a plain Ø5 mm cylinder that passes through the carrier's Ø5.2 mm hole;
// its top is flush with the carrier top so a washer or wide-head M3 screw can
// clamp the plate from above.  The blind pilot remains inside the Boss/floor
// material for an M3 self-tapping screw.
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM = 3.0;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_OD_MM = 5.0;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_BASE_OD_MM =
    VERTICAL_SPLINE_BEARING_FLOOR_BOSS_OD_MM;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_BASE_H_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_HEIGHT_MM =
    VERTICAL_SPLINE_BEARING_FLOOR_BOSS_BASE_H_MM;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM =
    WALL + VERTICAL_SPLINE_BEARING_FLOOR_BOSS_HEIGHT_MM;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_D_MM = 2.4;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_DEPTH_MM = 3.0;
VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_BOTTOM_Y_MM =
    VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM
        - VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_DEPTH_MM;
// The new carrier is a wider XZ plate sitting directly on circular floor
// bosses. The eight bosses are placed in the four gaps between adjacent
// bearing towers, so no locating cylinder occupies a tower footprint.
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X0_MM = 48.0;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X1_MM = 245.0;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X_LENGTH_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X1_MM
        - VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X0_MM;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM = DRIVE_AXIS_Z - 10.0;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z1_MM = DRIVE_AXIS_Z + 10.0;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z_LENGTH_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z1_MM
        - VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM = WALL;
VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM
        + VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM;
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_XS = [
    (clutch_col_x(0) + clutch_col_x(1)) / 2,
    (clutch_col_x(1) + clutch_col_x(2)) / 2,
    (clutch_col_x(2) + clutch_col_x(3)) / 2,
    (clutch_col_x(3) + clutch_col_x(4)) / 2
];
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_ZS = [
    DRIVE_AXIS_Z - 5.5,
    DRIVE_AXIS_Z + 5.5
];
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNT = 8;
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_CLEAR_D_MM = 5.2;
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_D_MM = 0.0;
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_DEPTH_MM = 0.0;
VERTICAL_SPLINE_BEARING_CARRIER_BOSS_MOUNT =
    "top-washer-or-wide-head-M3-over-5.2-hole";

VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM =
    VERTICAL_SPLINE_BEARING_CHAIN_TOP_Y_MM + 0.55;
VERTICAL_SPLINE_BEARING_CAP_T_MM = 2.20;
VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM =
    VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM
        + VERTICAL_SPLINE_BEARING_CAP_T_MM;
VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM = 2.0;
VERTICAL_SPLINE_BEARING_SEAT_SHOULDER_T_MM =
    VERTICAL_SPLINE_BEARING_CAP_T_MM
        - VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM;
VERTICAL_SPLINE_BEARING_SEAT_BOTTOM_Y_MM =
    VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM
        - VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM;
VERTICAL_SPLINE_BEARING_CENTER_Y_MM =
    VERTICAL_SPLINE_BEARING_SEAT_BOTTOM_Y_MM
        + VERTICAL_SPLINE_BEARING_WIDTH_MM / 2;
VERTICAL_SPLINE_BEARING_CAP_X_WIDTH_MM = 14.0;
VERTICAL_SPLINE_BEARING_CAP_Z_DEPTH_MM = 14.0;
VERTICAL_SPLINE_BEARING_TOWER_BODY_X_WIDTH_MM = 12.0;
VERTICAL_SPLINE_BEARING_TOWER_BODY_Z_DEPTH_MM = 12.0;
VERTICAL_SPLINE_BEARING_TOWER_COLUMN_DIAMETER_MM =
    VERTICAL_SPLINE_BEARING_TOWER_BODY_X_WIDTH_MM;
VERTICAL_SPLINE_BEARING_TOWER_BORE_D_MM = 3.6;
VERTICAL_SPLINE_BEARING_TOWER_ROOT_FLARE_H_MM = 5.5;
// The four ordinary columns keep the round load-transfer collar and the long
// round pillar.  C5 is the motor-side exception: its split support is a pair
// of Z-deep rounded trapezoid braces, continuous from the carrier to the cap.
VERTICAL_SPLINE_BEARING_TOWER_ROOT_X_WIDTH_MM = 20.0;
VERTICAL_SPLINE_BEARING_TOWER_ROOT_Z_DEPTH_MM = 20.0;
VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM = 4.5;
VERTICAL_SPLINE_BEARING_C5_RAIL_Z_DEPTH_MM = 16.4;
VERTICAL_SPLINE_BEARING_C5_RAIL_CENTER_OFFSET_X_MM = 8.0;
VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CENTER_OFFSET_X_MM = 10.5;
VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_WIDTH_MM = 6.4;
VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_Z_DEPTH_MM = 18.4;
VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM = 1.2;
VERTICAL_SPLINE_BEARING_C5_RAIL_PROFILE =
    "rounded-trapezoid-xy-with-rounded-xz-section";
VERTICAL_SPLINE_BEARING_C5_RAIL_CLEARANCE_MM =
    VERTICAL_SPLINE_BEARING_C5_RAIL_CENTER_OFFSET_X_MM
        - VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM / 2
        - 5.0;
VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CLEARANCE_MM =
    VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CENTER_OFFSET_X_MM
        - VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_WIDTH_MM / 2
        - 5.0;
VERTICAL_SPLINE_BEARING_CAP_C5_X_WIDTH_MM = 20.0;
VERTICAL_SPLINE_BEARING_CAP_C5_Z_DEPTH_MM = 18.0;
VERTICAL_SPLINE_BEARING_SUPPORT_MODE =
    "removable-floor-carrier-with-y-rising-bearing-towers";

// Compatibility aliases for the existing contract/preview API. They now
// describe the carrier/cap envelope; no partition keys or detour solids are
// generated anymore.
VERTICAL_SPLINE_BEARING_BAR_X_WIDTH_MM =
    VERTICAL_SPLINE_BEARING_CAP_X_WIDTH_MM;
VERTICAL_SPLINE_BEARING_BAR_Y_THICKNESS_MM =
    VERTICAL_SPLINE_BEARING_CAP_T_MM;
VERTICAL_SPLINE_BEARING_BAR_Z_MARGIN_MM = 0.0;
VERTICAL_SPLINE_BEARING_PARTITION_OVERLAP_MM = 0.0;
VERTICAL_SPLINE_BEARING_PARTITION_KEY_WIDTH_MM = 0.0;
VERTICAL_SPLINE_BEARING_PARTITION_KEY_CLEARANCE_MM = 0.0;
VERTICAL_SPLINE_BEARING_BAR_Y0_MM = VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM;
VERTICAL_SPLINE_BEARING_BAR_Y1_MM = VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM;
VERTICAL_SPLINE_BEARING_BAR_Z_MIN_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM;
VERTICAL_SPLINE_BEARING_BAR_Z_MAX_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z1_MM;
VERTICAL_SPLINE_BEARING_BAR_Z_LENGTH_MM =
    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z_LENGTH_MM;
VERTICAL_SPLINE_BEARING_PARTITION_KEY_Z_MAX_MM =
    WORLD_PARTITION_FRONT_Z;
VERTICAL_SPLINE_BEARING_PARTITION_KEY_Z_LENGTH_MM = 0.0;
VERTICAL_SPLINE_BEARING_RETURN_GUIDE_CLEARANCE_MM =
    VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM
        - VERTICAL_SPLINE_BEARING_CHAIN_TOP_Y_MM;
VERTICAL_SPLINE_BEARING_LOWER_PULLEY_CLEARANCE_MM =
    VERTICAL_SPLINE_BEARING_LOWER_PULLEY_BOTTOM_Y_MM
        - VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM;
VERTICAL_SPLINE_BEARING_RETURN_DRIVE_CLEARANCE_MM =
    clutch_col_x(0)
        - VERTICAL_SPLINE_BEARING_CAP_X_WIDTH_MM / 2
        - (SNAKE_CHAIN_RETURN_DRIVE_X_MM
            + SNAKE_CHAIN_DRIVE_OUTER_R_MM);
VERTICAL_SPLINE_BEARING_DETOUR_COLUMN = 0;
VERTICAL_SPLINE_BEARING_DETOUR_X_OFFSET_MM = 0.0;
VERTICAL_SPLINE_BEARING_DETOUR_X_MM = clutch_col_x(0);
VERTICAL_SPLINE_BEARING_DETOUR_Z_CLEARANCE_MM = 0.0;
VERTICAL_SPLINE_BEARING_DETOUR_CHAIN_CLEARANCE_MM = 0.0;

function vertical_spline_bearing_carrier_boss_xs() = [
    for (x = VERTICAL_SPLINE_BEARING_CARRIER_BOSS_XS) x
];

function vertical_spline_bearing_carrier_boss_zs() = [
    for (z = VERTICAL_SPLINE_BEARING_CARRIER_BOSS_ZS) z
];

module vertical_spline_bearing_floor_bosses() {
    for (x = vertical_spline_bearing_carrier_boss_xs())
        for (z = vertical_spline_bearing_carrier_boss_zs()) {
            // One plain circular post, fused directly to the cabinet floor.
            // There is no stepped or shaped locating foot.
            cylinder_y(
                x,
                WALL - EPS,
                z,
                VERTICAL_SPLINE_BEARING_FLOOR_BOSS_OD_MM,
                VERTICAL_SPLINE_BEARING_FLOOR_BOSS_HEIGHT_MM + EPS
            );
        }
}

module vertical_spline_bearing_floor_boss_pilot_holes() {
    for (x = vertical_spline_bearing_carrier_boss_xs())
        for (z = vertical_spline_bearing_carrier_boss_zs())
            cylinder_y(
                x,
                VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_BOTTOM_Y_MM,
                z,
                VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_D_MM,
                VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_DEPTH_MM + EPS
            );
}

module vertical_spline_bearing_carrier_plate() {
    difference() {
        translate([
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X0_MM,
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM,
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM
        ])
            cube([
                VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X_LENGTH_MM,
                VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM,
                VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z_LENGTH_MM
            ]);
        for (x = vertical_spline_bearing_carrier_boss_xs())
            for (z = vertical_spline_bearing_carrier_boss_zs()) {
                // Clearance around the self-tapping screw shank.
                cylinder_y(
                    x,
                    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM - EPS,
                    z,
                    VERTICAL_SPLINE_BEARING_CARRIER_BOSS_CLEAR_D_MM,
                    VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM + 2 * EPS
                );
            }
    }
}

module vertical_spline_round_column_y(x, z, y0, d, h) {
    cylinder_y(x, y0, z, d, h);
}

module vertical_spline_rounded_prism_y(x, z, y0, w, d, h, r = 1.0) {
    hull()
        for (dx = [-w / 2 + r, w / 2 - r])
            for (dz = [-d / 2 + r, d / 2 - r])
                cylinder_y(x + dx, y0, z + dz, 2 * r, h);
}

module vertical_spline_tapered_root_y(
    x,
    z,
    y0,
    h,
    root_w,
    root_d,
    body_w,
    body_d
) {
    hull() {
        vertical_spline_rounded_prism_y(
            x,
            z,
            y0,
            root_w,
            root_d,
            EPS,
            min(root_w, root_d) / 2 - 0.20
        );
        vertical_spline_rounded_prism_y(
            x,
            z,
            y0 + h - EPS,
            body_w,
            body_d,
            EPS,
            min(body_w, body_d) / 2 - 0.20
        );
    }
}

module vertical_spline_bearing_tower(x, z, cap_w = VERTICAL_SPLINE_BEARING_CAP_X_WIDTH_MM) {
    root_top_y = VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM
        + VERTICAL_SPLINE_BEARING_TOWER_ROOT_FLARE_H_MM;
    body_y0 = root_top_y - 0.20;
    difference() {
        union() {
            vertical_spline_round_column_y(
                x,
                z,
                VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM,
                VERTICAL_SPLINE_BEARING_TOWER_ROOT_X_WIDTH_MM,
                VERTICAL_SPLINE_BEARING_TOWER_ROOT_FLARE_H_MM + EPS
            );
            vertical_spline_round_column_y(
                x,
                z,
                body_y0,
                VERTICAL_SPLINE_BEARING_TOWER_COLUMN_DIAMETER_MM,
                VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM - body_y0
            );
            vertical_spline_rounded_prism_y(
                x,
                z,
                VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM,
                cap_w,
                VERTICAL_SPLINE_BEARING_CAP_Z_DEPTH_MM,
                VERTICAL_SPLINE_BEARING_CAP_T_MM,
                1.2
            );
        }
        cylinder_y(
            x,
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM - EPS,
            z,
            VERTICAL_SPLINE_BEARING_TOWER_BORE_D_MM,
            VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM
                - VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM
                + 2 * EPS
        );
        // The 6.10 mm printed pocket opens from +Y and leaves a 0.20 mm
        // shoulder under the 2 mm purchased bearing.
        cylinder_y(
            x,
            VERTICAL_SPLINE_BEARING_SEAT_BOTTOM_Y_MM - EPS,
            z,
            VERTICAL_SPLINE_BEARING_SEAT_D_MM,
            VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM + 2 * EPS
        );
    }
}

module vertical_spline_c5_trapezoid_brace_y(x, z, side) {
    // The brace is a single printable solid.  In the XY rear view its two
    // side members flare from the carrier and lean inward toward the cap;
    // in XZ it is a rounded rectangle, not a 3.2 mm circular whisker.
    x_bottom = x
        + side * VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CENTER_OFFSET_X_MM;
    x_top = x
        + side * VERTICAL_SPLINE_BEARING_C5_RAIL_CENTER_OFFSET_X_MM;
    hull() {
        vertical_spline_rounded_prism_y(
            x_bottom,
            z,
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM,
            VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_WIDTH_MM,
            VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_Z_DEPTH_MM,
            EPS,
            VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM
        );
        vertical_spline_rounded_prism_y(
            x_top,
            z,
            VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM - EPS,
            VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM,
            VERTICAL_SPLINE_BEARING_C5_RAIL_Z_DEPTH_MM,
            EPS,
            VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM
        );
    }
}

module vertical_spline_bearing_c5_tower(x, z) {
    difference() {
        union() {
            for (side = [-1, 1]) {
                vertical_spline_c5_trapezoid_brace_y(x, z, side);
            }
            vertical_spline_rounded_prism_y(
                x,
                z,
                VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM,
                VERTICAL_SPLINE_BEARING_CAP_C5_X_WIDTH_MM,
                VERTICAL_SPLINE_BEARING_CAP_C5_Z_DEPTH_MM,
                VERTICAL_SPLINE_BEARING_CAP_T_MM,
                1.2
            );
        }
        cylinder_y(
            x,
            VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM - EPS,
            z,
            VERTICAL_SPLINE_BEARING_TOWER_BORE_D_MM,
            VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM
                - VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM
                + 2 * EPS
        );
        cylinder_y(
            x,
            VERTICAL_SPLINE_BEARING_SEAT_BOTTOM_Y_MM - EPS,
            z,
            VERTICAL_SPLINE_BEARING_SEAT_D_MM,
            VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM + 2 * EPS
        );
    }
}

module vertical_spline_bearing_support_bars() {
    color("#718096") {
        vertical_spline_bearing_carrier_plate();
        for (i = [0:N_COL - 2])
            vertical_spline_bearing_tower(clutch_col_x(i), DRIVE_AXIS_Z);
        vertical_spline_bearing_c5_tower(
            clutch_col_x(N_COL - 1),
            DRIVE_AXIS_Z
        );
    }
}

module vertical_spline_bearing_reference_y(x) {
    color("#cfd4da")
        translate([x, VERTICAL_SPLINE_BEARING_CENTER_Y_MM, DRIVE_AXIS_Z])
            rotate([90, 0, 0])
                difference() {
                    cylinder(
                        d = VERTICAL_SPLINE_BEARING_OD_MM,
                        h = VERTICAL_SPLINE_BEARING_WIDTH_MM,
                        center = true,
                        $fn = 64
                    );
                    cylinder(
                        d = VERTICAL_SPLINE_BEARING_ID_MM,
                        h = VERTICAL_SPLINE_BEARING_WIDTH_MM + 2 * EPS,
                        center = true,
                        $fn = 48
                    );
                }
}

module vertical_spline_bearing_references() {
    for (i = [0:N_COL - 1])
        vertical_spline_bearing_reference_y(clutch_col_x(i));
}

module vertical_spline_chain_clearance_envelope() {
    // World-space conservative envelopes for the lower snake return: both
    // fixed 8T side guides and the 12T return drive. The support candidate is
    // tested against these volumes before it is added to the partition union.
    for (x = [
        SNAKE_CHAIN_LEFT_VERTICAL_GUIDE_X_MM,
        SNAKE_CHAIN_RIGHT_VERTICAL_GUIDE_X_MM
    ])
        translate([
            x,
            SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y_MM,
            SNAKE_CHAIN_CENTER_Z - SNAKE_CHAIN_HALF_DEPTH
        ])
            cylinder(
                d = 2 * SNAKE_CHAIN_GUIDE_OUTER_R_MM,
                h = 2 * SNAKE_CHAIN_HALF_DEPTH,
                $fn = 64
            );
    translate([
        SNAKE_CHAIN_RETURN_DRIVE_X_MM,
        SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y_MM,
        SNAKE_CHAIN_CENTER_Z - SNAKE_CHAIN_HALF_DEPTH
    ])
        cylinder(
            d = 2 * SNAKE_CHAIN_DRIVE_OUTER_R_MM,
            h = 2 * SNAKE_CHAIN_HALF_DEPTH,
            $fn = 96
        );
}

module selected_vertical_spline_bearing_support_part() {
    vertical_spline_bearing_support_bars();
}

module selected_vertical_spline_bearing_references_part() {
    vertical_spline_bearing_references();
}

module selected_vertical_spline_support_chain_collision_part() {
    intersection() {
        vertical_spline_bearing_support_bars();
        vertical_spline_chain_clearance_envelope();
    }
}

module selected_vertical_spline_support_drive_collision_part() {
    intersection() {
        vertical_spline_bearing_support_bars();
        all_vertical_axes();
    }
}

module selected_vertical_spline_support_partition_window_collision_part() {
    intersection() {
        vertical_spline_bearing_support_bars();
        all_drawer_belt_partition_windows();
    }
}

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
// tangentially. The service plate keeps the output rotor fixed in Y; the male
// rotor, its stepped D-round-D shaft and its M5 magnetic sleeve move together.
module center_gt2_male(col, row, engaged = false) {
    x = clutch_col_x(col);
    z = center_gt2_z();
    // The explicit travel override is intentionally shared by the rotor, the
    // stepped shaft, sleeve and magnet. Using the boolean only here would make
    // an intermediate CSG sample look stationary while the shaft moved.
    insertion_shift = CENTER_CLUTCH_TRAVEL_MM;
    color("#718b99")
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

module center_gt2_clutch(col, row, engaged = false, include_plate = false) {
    center_clutch_carrier(col, row, engaged, true, include_plate);
    center_gt2_female(col, row);
    center_gt2_male(col, row, engaged);
}

module all_clutches() {
    center_station_engaged =
        ENGAGED
            && CENTER_GT2_COL == selected_col()
            && CENTER_GT2_ROW == selected_row();
    // The rear cavity has one continuous printed carrier strip per drawer
    // row.  Station mechanisms below are instances and deliberately do not
    // carry fifteen duplicate local plates.
    color("#536d78") center_clutch_mechanism_row_plates();
    center_gt2_clutch(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        center_station_engaged,
        false
    );

    // Keep the world assembly complete: the fourteen non-center stations are
    // translated instances of the same finished center clutch. They are
    // static references in OpenSCAD; only R3C3 is driven by the browser demo.
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1])
            if (!is_center_gt2_station(col, row))
                center_station_clutch_instance(col, row, false);

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

module drawer_front_belt_at(col, row) {
    x = clutch_col_x(col);
    if (is_center_gt2_station(col, row))
        color(COLOR_BELT, 0.18)
            center_gt2_belt_loop_z(
                x,
                center_gt2_z(),
                CENTER_GT2_FRONT_PULLEY_Z,
                center_gt2_belt_y(row)
            );
    else
        color(COLOR_BELT, 0.14)
            belt_loop_z(
                x,
                DRIVE_AXIS_Z,
                FRONT_PULLEY_Z,
                drawer_belt_y(row)
            );
}

module drawer_front_pulley_at(col, row) {
    x = clutch_col_x(col);
    if (is_center_gt2_station(col, row))
        center_gt2_front_pulley_y(
            x,
            center_gt2_belt_y(row),
            CENTER_GT2_FRONT_PULLEY_Z
        );
    else
        color(COLOR_TIMING)
            timing_pulley_y(
                x,
                drawer_belt_y(row),
                FRONT_PULLEY_Z,
                TIMING_TEETH,
                "round"
            );
}

module drawer_front_gear_at(col, row) {
    x = clutch_col_x(col);
    if (is_center_gt2_station(col, row))
        color(COLOR_GEAR)
            spur_gear_y(
                x,
                center_gt2_front_gear_y(row),
                CENTER_GT2_FRONT_PULLEY_Z,
                FRONT_GEAR_TEETH,
                CLUTCH_PITCH_MM,
                FRONT_GEAR_TOOTH_DEPTH,
                FRONT_GEAR_T,
                ROD_D,
                "d"
            );
    else
        color(COLOR_GEAR)
            spur_gear_y(
                x,
                drawer_front_gear_y(row),
                FRONT_PULLEY_Z,
                FRONT_GEAR_TEETH,
                CLUTCH_PITCH_MM,
                FRONT_GEAR_TOOTH_DEPTH,
                FRONT_GEAR_T
            );
}

module drawer_front_axis_at(col, row) {
    x = clutch_col_x(col);
    if (is_center_gt2_station(col, row))
        color(COLOR_SHAFT)
            d_rod_y(
                x,
                center_gt2_front_d_shaft_start_y(row),
                CENTER_GT2_FRONT_PULLEY_Z,
                center_gt2_front_d_shaft_length(row),
                ROD_D
            );
    else {
        belt_y = drawer_belt_y(row);
        gear_y = drawer_front_gear_y(row);
        y0 = min(
            belt_y - TIMING_PULLEY_W / 2 - 0.25,
            gear_y - FRONT_GEAR_T / 2 - 0.25
        );
        y1 = max(
            belt_y - TIMING_PULLEY_W / 2 - 0.25,
            gear_y - FRONT_GEAR_T / 2 - 0.25
        );
        color(COLOR_SHAFT)
            cylinder_y(x, y0, FRONT_PULLEY_Z, CLUTCH_HUB_D, y1 - y0 + 0.50);
    }
}

module drawer_front_compound(col, row) {
    drawer_front_pulley_at(col, row);
    drawer_front_gear_at(col, row);
    drawer_front_axis_at(col, row);
}

module drawer_front_drive(col, row) {
    x = clutch_col_x(col);
    drawer_front_belt_at(col, row);
    drawer_front_compound(col, row);
    horizontal_drawer_rack(
        x,
        WORLD_PARTITION_FRONT_Z + 1.5,
        FRONT_PULLEY_Z - 3.5,
        drawer_front_gear_y(row)
    );
    drawer_front_drive_guide_system(col, row, FRONT_PULLEY_Z);
}

module center_gt2_front_pulley_y(x, belt_y, z, bore = "d") {
    base_y = center_gt2_pulley_base_y(belt_y);
    color(COLOR_TIMING)
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

module center_gt2_front_compound(col, row) {
    x = clutch_col_x(col);
    front_z = CENTER_GT2_FRONT_PULLEY_Z;
    belt_y = center_gt2_belt_y(row);
    gear_y = center_gt2_front_gear_y(row);

    center_gt2_front_pulley_y(x, belt_y, front_z);
    // The front output remains the deliberately coarse rack pinion.  Its
    // lower timing wheel now lives in the next drawer bay and is joined by a
    // continuous D shaft through the shelf-thickness bearing.
    color(COLOR_GEAR)
        spur_gear_y(
            x,
            gear_y,
            front_z,
            FRONT_GEAR_TEETH,
            CLUTCH_PITCH_MM,
            FRONT_GEAR_TOOTH_DEPTH,
            FRONT_GEAR_T,
            ROD_D,
            "d"
        );
    color(COLOR_SHAFT)
        d_rod_y(
            x,
            center_gt2_front_d_shaft_start_y(row),
            front_z,
            center_gt2_front_d_shaft_length(row),
            ROD_D
        );
}

module center_gt2_drawer_drive(col, row) {
    x = clutch_col_x(col);
    drawer_front_belt_at(col, row);
    drawer_front_compound(col, row);
    horizontal_drawer_rack(
        x,
        WORLD_PARTITION_FRONT_Z + 1.5,
        CENTER_GT2_FRONT_PULLEY_Z - 3.5,
        center_gt2_front_gear_y(row)
    );
    drawer_front_drive_guide_system(col, row, CENTER_GT2_FRONT_PULLEY_Z);
}

// One canonical center-station assembly.  The source is authored once at the
// real R3C3 datum; every other station is a translated instance of this exact
// geometry.  This prevents the old round-bore/legacy-MR63 drawer-side branch
// from silently becoming fourteen different mechanisms.
module center_station_instance_transform(col, row) {
    translate([
        clutch_col_x(col) - clutch_col_x(CENTER_GT2_COL),
        world_row_center_y(row) - world_row_center_y(CENTER_GT2_ROW),
        0
    ])
        children();
}

module center_station_clutch_instance(col, row, engaged = false) {
    center_station_instance_transform(col, row)
        center_gt2_clutch(CENTER_GT2_COL, CENTER_GT2_ROW, engaged, false);
}

module center_station_drawer_drive_instance(col, row) {
    center_station_instance_transform(col, row)
        center_gt2_drawer_drive(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module center_station_assembly_instance(col, row, engaged = false) {
    center_station_instance_transform(col, row) {
        center_gt2_clutch(CENTER_GT2_COL, CENTER_GT2_ROW, engaged, false);
        center_gt2_drawer_drive(CENTER_GT2_COL, CENTER_GT2_ROW);
    }
}

module drawer_side_assembly(col, row) {
    // Compatibility name retained for callers outside this file. It now
    // resolves to the center-proven 2GT drawer drive, never the old branch.
    center_station_drawer_drive_instance(col, row);
}

module drawer_drive() {
    // All fifteen drawer drive assemblies are instances of the center
    // station's finished 2GT/rack/guide geometry. The center source remains
    // the native animated station; the other fourteen are translated copies.
    for (row = [0:N_ROW - 1])
        for (col = [0:N_COL - 1])
            center_station_drawer_drive_instance(col, row);
}

// The browser exports one local center-station kit. Three.js creates fourteen
// translated instances from that single STL and keeps the center cell's
// component IDs for the native animation. The local origin is the center
// station axis; Z remains the authored cabinet datum.
module center_station_template_frame() {
    translate([
        -clutch_col_x(CENTER_GT2_COL),
        -world_row_center_y(CENTER_GT2_ROW),
        0
    ])
        children();
}

module selected_center_station_template_assembly_part() {
    center_station_template_frame()
        center_station_assembly_instance(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            false
        );
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
    // Retained only as an empty compatibility entry point. The current male
    // end has no printed carriage; its shaft slides directly in the fixed
    // integral LM3UU seat in the mechanism plate.
}

module selected_center_input_sleeve_part() {
    center_clutch_input_sleeve(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_input_sleeve_magnet_part() {
    center_clutch_input_sleeve_magnet_reference(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        ENGAGED
    );
}

module selected_center_output_bearing_bar_part() {
    // Diagnostic-only standalone view of the output support. The canonical
    // printed part is center_mechanism_plate, which contains this bar.
    center_clutch_output_bearing_bar_y(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_guide_rails_part() {
    center_clutch_guide_rails(CENTER_GT2_COL, CENTER_GT2_ROW);
}

module selected_center_linear_bearings_part() {
    center_clutch_linear_bearings(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        false
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
    // This one STL is the complete three-row rear carrier: each row spans
    // five stations, while every station's LM3UU/output bearing supports and
    // four screw holes remain generated from the same source datum.
    center_clutch_mechanism_row_plates();
}

// Standalone inspection export for the fixed front/rear compartment
// partition. The canonical cabinet_frame already contains the same solid, so
// this part is published only as a hidden inspection/reference mesh and never
// as a second installed partition in the default assembly.
module selected_cabinet_partition_part() {
    cabinet_frame_partition_with_belt_passage();
}

// Collision witness for the first-article audit. The service plate sits in
// the rear-to-front belt span, so this must export as an empty intersection
// after the plate's real through-passage is cut. It is diagnostic only and is
// never included in the default manifest.
module selected_center_plate_belt_collision_part() {
    intersection() {
        center_clutch_mechanism_row_plates();
        union()
            for (row = [0:N_ROW - 1])
                for (col = [0:N_COL - 1])
                    center_gt2_belt_loop_z(
                        clutch_col_x(col),
                        center_gt2_z(),
                        CENTER_GT2_FRONT_PULLEY_Z,
                        center_gt2_belt_y(row)
                    );
    }
}

// Empty CSG witness for the cabinet's internal rear datum plate. This is a
// separate check from the removable mechanism plate because the cabinet plate
// has its own larger print clearance and must still clear the same real R3C3
// belt straight run without opening phantom legacy-station holes.
module selected_center_partition_belt_collision_part() {
    intersection() {
        clutch_partition_with_belt_passages();
        center_gt2_belt_loop_z(
            clutch_col_x(CENTER_GT2_COL),
            CENTER_GT2_Z,
            CENTER_GT2_FRONT_PULLEY_Z,
            center_gt2_belt_y(CENTER_GT2_ROW)
        );
    }
}

// These actual CSG intersections are exported only by the geometry gate. An
// Empty result is the required witness: the pair may contact through its
// designed tooth envelope, while the stepped shaft, fixed LM3UU seat and
// sleeve must retain real clearance throughout the open and engaged datums.
module selected_center_clutch_pair_collision_part() {
    intersection() {
        center_gt2_male(CENTER_GT2_COL, CENTER_GT2_ROW, ENGAGED);
        center_gt2_female(CENTER_GT2_COL, CENTER_GT2_ROW);
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

// The retainer caps travel with the input carriage, but they extend past the
// carriage stop shoe.  Keep this witness separate from the carriage witness:
// a cap/stop collision is a real hard bind even when the carrier body itself
// only touches the designed stop face.
module selected_center_stops_retainer_collision_part() {
    intersection() {
        center_clutch_stops(CENTER_GT2_COL, CENTER_GT2_ROW);
        center_clutch_linear_bearing_retainers(
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
            ROD_D,
            "d"
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
            drawer_rack_z0(),
            drawer_rack_z1(CENTER_GT2_FRONT_PULLEY_Z),
            center_gt2_front_gear_y(row)
        );
    else
        horizontal_drawer_rack(
            clutch_col_x(selected_col()),
            WORLD_PARTITION_FRONT_Z + 1.5,
            FRONT_PULLEY_Z - 3.5,
            drawer_front_gear_y(row)
        );
    drawer_c_guide_flanges_at(
        selected_col(),
        row,
        is_center_gt2_station(selected_col(), row)
            ? CENTER_GT2_FRONT_PULLEY_Z
            : FRONT_PULLEY_Z
    );
}

module selected_drawer_rack_guide_rollers_part() {
    drawer_rack_guide_rollers(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        CENTER_GT2_FRONT_PULLEY_Z
    );
}

module selected_drawer_rack_guide_rails_part() {
    drawer_rack_guide_rails_at(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        CENTER_GT2_FRONT_PULLEY_Z
    );
}

// Empty CSG witness: the moving drawer flanges must remain inside the slot
// envelope and must not enter either inward guide lip. A non-empty result is
// a real geometric collision, not a merely analytic warning. The fixed
// divider/side-panel vertical member is intentionally not part of this
// witness because the flange is allowed to pass beside its inner face.
module selected_drawer_guide_flange_rail_collision_part() {
    intersection() {
        drawer_c_guide_flanges_at(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            CENTER_GT2_FRONT_PULLEY_Z
        );
        drawer_rack_guide_rails_at(
            CENTER_GT2_COL,
            CENTER_GT2_ROW,
            CENTER_GT2_FRONT_PULLEY_Z
        );
    }
}

// Empty CSG witness: the center drawer rack and front pinion must not enter
// the intact printable center shelf or its integrated 3×6×2 bearing boss.
// The rack/pinion are deliberately above the shelf; a non-empty result means
// a future height change has buried the drive into the shelf again.
module selected_drawer_front_drive_shelf_collision_part() {
    intersection() {
        union() {
            horizontal_drawer_rack(
                clutch_col_x(CENTER_GT2_COL),
                drawer_rack_z0(),
                drawer_rack_z1(CENTER_GT2_FRONT_PULLEY_Z),
                center_gt2_front_gear_y(CENTER_GT2_ROW)
            );
            selected_front_gear_part();
        }
        world_bay_grid();
    }
}

module selected_drawer_front_pinion_bearing_support_part() {
    drawer_front_pinion_bearing_support(
        clutch_col_x(CENTER_GT2_COL),
        center_gt2_front_gear_y(CENTER_GT2_ROW),
        CENTER_GT2_FRONT_PULLEY_Z,
        false
    );
}

module selected_drawer_front_pinion_bearings_part() {
    x = clutch_col_x(CENTER_GT2_COL);
    gear_y = center_gt2_front_gear_y(CENTER_GT2_ROW);
    for (side = [1])
        drawer_drive_mr63_bearing_y(
            x,
            gear_y + side * DRAWER_PINION_SUPPORT_CHEEK_OFFSET,
            CENTER_GT2_FRONT_PULLEY_Z
        );
}

module selected_front_timing_bearing_support_part() {
    center_gt2_front_shelf_bearing_boss(
        CENTER_GT2_COL,
        CENTER_GT2_ROW,
        CENTER_GT2_FRONT_PULLEY_Z,
        false
    );
}

module selected_front_timing_bearing_part() {
    drawer_drive_front_timing_bearing_y(
        clutch_col_x(CENTER_GT2_COL),
        center_gt2_front_timing_bearing_center_y(CENTER_GT2_ROW),
        CENTER_GT2_FRONT_PULLEY_Z
    );
}

module selected_front_d_axis_part() {
    color(COLOR_SHAFT)
        d_rod_y(
            clutch_col_x(CENTER_GT2_COL),
            center_gt2_front_d_shaft_start_y(CENTER_GT2_ROW),
            CENTER_GT2_FRONT_PULLEY_Z,
            center_gt2_front_d_shaft_length(CENTER_GT2_ROW),
            ROD_D
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
        // Detail mode is a single-station inspection view.  The world
        // assembly uses the shared row carrier above; this local plate is
        // intentionally only a diagnostic overlay for the selected station.
        center_gt2_clutch(col, row, ENGAGED, true);
        // The center detail contains the current plate with integral seats,
        // output D-round shaft, D-round-D input shaft/sleeve and the sleeve
        // magnet interface.  The retired selector shoe/support arm is not
        // part of the canonical assembly or any one-by-one export.
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
        drawer_drive();
        if (SHOW_LEGACY_STATIONS
            && !is_center_gt2_station(selected_col(), selected_row()))
            clutch_fork(selected_col(), selected_row(), ENGAGED);
    } else if (CLUTCH_PART == "cabinet") {
        // Export the shell alone as a watertight printed part; internal panels and
        // drawer ghosts are visual context only and intentionally do not enter it.
        color(COLOR_CABINET) clutch_cabinet_shell();
    } else if (CLUTCH_PART == "cabinet_frame") {
        // Canonical non-duplicated cabinet structure for the root preview.
        color(COLOR_CABINET) clutch_cabinet_frame();
    } else if (CLUTCH_PART == "cabinet_partition") {
        // Standalone inspection/reference mesh; cabinet_frame owns the
        // installed copy so this selector is not a second assembly body.
        color(COLOR_CABINET) selected_cabinet_partition_part();
    } else if (CLUTCH_PART == "cabinet_context") {
        // Compatibility alias: the context now uses the same single canonical
        // frame, with optional drawer ghosts, instead of a second wire shell.
        clutch_cabinet_context();
    } else if (CLUTCH_PART == "power_bus") {
        power_bus();
    } else if (CLUTCH_PART == "all_vertical_axes") {
        all_vertical_axes();
    } else if (CLUTCH_PART == "drawer_drive") {
        drawer_drive();
    } else if (CLUTCH_PART == "center_station_template_assembly") {
        selected_center_station_template_assembly_part();
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
    } else if (CLUTCH_PART == "vertical_spline_bearing_support") {
        selected_vertical_spline_bearing_support_part();
    } else if (CLUTCH_PART == "vertical_spline_bearings") {
        selected_vertical_spline_bearing_references_part();
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
    } else if (CLUTCH_PART == "center_input_sleeve") {
        selected_center_input_sleeve_part();
    } else if (CLUTCH_PART == "center_input_sleeve_magnet") {
        selected_center_input_sleeve_magnet_part();
    } else if (CLUTCH_PART == "center_input_carriage") {
        selected_center_input_carriage_part();
    } else if (CLUTCH_PART == "center_output_bearing_bar") {
        selected_center_output_bearing_bar_part();
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
    } else if (CLUTCH_PART == "center_partition_belt_collision") {
        selected_center_partition_belt_collision_part();
    } else if (CLUTCH_PART == "vertical_spline_support_chain_collision") {
        selected_vertical_spline_support_chain_collision_part();
    } else if (CLUTCH_PART == "vertical_spline_support_drive_collision") {
        selected_vertical_spline_support_drive_collision_part();
    } else if (CLUTCH_PART == "vertical_spline_support_partition_window_collision") {
        selected_vertical_spline_support_partition_window_collision_part();
    } else if (CLUTCH_PART == "center_clutch_pair_collision") {
        selected_center_clutch_pair_collision_part();
    } else if (CLUTCH_PART == "center_carriage_rail_collision") {
        selected_center_carriage_rail_collision_part();
    } else if (CLUTCH_PART == "center_input_rotor_carriage_collision") {
        selected_center_input_rotor_carriage_collision_part();
    } else if (CLUTCH_PART == "center_stops_carriage_collision") {
        selected_center_stops_carriage_collision_part();
    } else if (CLUTCH_PART == "center_stops_retainer_collision") {
        selected_center_stops_retainer_collision_part();
    } else if (CLUTCH_PART == "center_guide_stop_collision") {
        selected_center_guide_stop_collision_part();
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
    } else if (CLUTCH_PART == "drawer_rack_guide_rollers") {
        selected_drawer_rack_guide_rollers_part();
    } else if (CLUTCH_PART == "drawer_rack_guide_rails") {
        selected_drawer_rack_guide_rails_part();
    } else if (CLUTCH_PART == "drawer_guide_flange_rail_collision") {
        selected_drawer_guide_flange_rail_collision_part();
    } else if (CLUTCH_PART == "drawer_front_drive_shelf_collision") {
        selected_drawer_front_drive_shelf_collision_part();
    } else if (CLUTCH_PART == "drawer_front_pinion_bearing_support") {
        selected_drawer_front_pinion_bearing_support_part();
    } else if (CLUTCH_PART == "drawer_front_pinion_bearings") {
        selected_drawer_front_pinion_bearings_part();
    } else if (CLUTCH_PART == "front_timing_bearing_support") {
        selected_front_timing_bearing_support_part();
    } else if (CLUTCH_PART == "front_timing_bearing") {
        selected_front_timing_bearing_part();
    } else if (CLUTCH_PART == "front_d_axis") {
        selected_front_d_axis_part();
    } else if (CLUTCH_PART == "world_axes") {
        world_axes_marker();
    } else {
        assert(false, str("unknown CLUTCH_PART: ", CLUTCH_PART));
    }
}

clutch_scene_geometry();
//#endregion

echo(
    "CENTER_CLUTCH_CONTRACT_DYNAMIC",
    "version=1",
    "axis=+Y",
    "role=input/output",
    "verticalLayoutMode=drawer-bottom-drive-layer-lower-pulley",
    str("centerClutchDriveLayerOffsetMm=", CENTER_CLUTCH_DRIVE_LAYER_OFFSET_MM),
    str("centerClutchVerticalLiftMm=", CENTER_CLUTCH_VERTICAL_LIFT_MM),
    str("drawerLayerCount=", N_ROW),
    str("drawerColumnCount=", N_COL),
    str("serviceLayerCount=", SERVICE_LAYERS),
    str("drawerBayHeightMm=", BAY_H),
    str("drawerShelfThicknessMm=", WORLD_SHELF_T),
    str("cabinetWidthMm=", W),
    str("serviceWidthMm=", SERVICE_W),
    str("gridWidthMm=", WORLD_GRID_W),
    str("drawerBayWidthMm=", WORLD_BAY_W),
    str("drawerColumnPitchMm=", WORLD_COL_PITCH),
    "rearClutchCarrierMode=row-strip",
    str("rearClutchRowPlateCount=", N_ROW),
    str("rearClutchRowPlateStationCount=", N_COL),
    str("rearClutchRowPlateLengthMm=", center_clutch_row_plate_length()),
    str("rearClutchRowPlateX0Mm=", center_clutch_row_plate_x0()),
    str("rearClutchRowPlateX1Mm=", center_clutch_row_plate_x1()),
    str("rearClutchRowPlateLeftClearanceMm=",
        center_clutch_row_plate_left_clearance()),
    str("rearClutchRowPlateRightClearanceMm=",
        center_clutch_row_plate_right_clearance()),
    str("drawerStationTemplateOriginXMm=", clutch_col_x(0)),
    str("drawerStationTemplateOriginYMm=", world_row_center_y(0)),
    str("drawerStationColumnPitchMm=", WORLD_COL_PITCH),
    str("drawerStationRowPitchMm=", WORLD_ROW_PITCH),
    str("drawerStationInstanceCount=", N_COL * N_ROW - 1),
    str("drawerRackBodyWidthMm=", DRAWER_RACK_BODY_X),
    str("drawerRackBodyHeightMm=", DRAWER_RACK_BODY_Y),
    str("drawerRackToothHeightMm=", DRAWER_RACK_TOOTH_H),
    str("drawerRackToothOverhangMm=", DRAWER_RACK_TOOTH_OVERHANG_X),
    str("centerFrontDriveLiftMm=", CENTER_FRONT_DRIVE_LIFT_MM),
    str("frontRackAboveShelfGapMm=", CENTER_FRONT_RACK_ABOVE_SHELF_GAP),
    str("drawerRackLowerYMm=",
        center_gt2_front_gear_y(CENTER_GT2_ROW) - DRAWER_RACK_BODY_Y / 2),
    str("drawerShelfTopYMm=", world_row_y(CENTER_GT2_ROW)),
    str("frontTimingBearingReinforcementDiscDiameterMm=",
        CENTER_FRONT_BEARING_REINFORCEMENT_DISC_DIAMETER),
    str("frontTimingBearingReinforcementDiscThicknessMm=",
        CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS),
    "drawerRackMount=drawer-bottom-moving",
    "drawerMassLoadPath=side-slides-not-rack",
    "drawerGuideBearing=681-1x3x1-X-axis-C-slot",
    "drawerGuideRail=partition-integral-inward-C-lips",
    "drawerGuideRailSupport=existing-divider-or-side-panel-vertical-member",
    "drawerGuideFlangeDirection=toward-drawer-center",
    "drawerGuideBearingArrangement=tail-moving-plus-front-lower-fixed",
    "drawerGuideBearingAxis=+X/-X",
    "drawerGuideLoadPath=Y-support-Z-travel",
    "drawerFrontPinionBearing=integral-shelf-stepped-3x6x2",
    str("drawerGuideRailClearanceMm=", DRAWER_GUIDE_RAIL_GAP),
    str("drawerGuidePartitionThicknessMm=", DRAWER_GUIDE_PARTITION_SUPPORT_T),
    str("drawerGuideRailAttachOverlapMm=", DRAWER_GUIDE_RAIL_ATTACH_OVERLAP),
    str("drawerGuideBearingSeatDiameterMm=", DRAWER_GUIDE_681_SEAT_D),
    str("drawerGuideSlotHeightMm=", DRAWER_GUIDE_C_SLOT_H),
    str("drawerGuideRailDepthMm=", DRAWER_GUIDE_C_DEPTH),
    str("drawerGuideFlangeThicknessMm=", DRAWER_GUIDE_C_FLANGE_T),
    str("drawerGuideFlangeProjectionMm=", DRAWER_GUIDE_C_FLANGE_PROJECTION),
    str("drawerGuideFlangeClearanceMm=", DRAWER_GUIDE_C_FLANGE_CLEARANCE),
    str("drawerGuideDrawerEdgeInsetMm=", DRAWER_CLEAR),
    str("drawerGuideFlangeEndClearanceMm=", DRAWER_GUIDE_C_FLANGE_END_CLEARANCE),
    str("drawerGuideFrontSupportClearanceMm=", DRAWER_GUIDE_C_FRONT_SUPPORT_CLEARANCE),
    "drawerGuideTailBearingAxis=+X/-X",
    "drawerGuideFrontBearingAxis=+X/-X",
    str("drawerFrontPinionBearingSeatDiameterMm=", DRAWER_PINION_MR63_SEAT_D),
    str("axisXMm=", clutch_col_x(CENTER_GT2_COL)),
    str("axisZMm=", center_gt2_z()),
    str("verticalSplineBearingNominal=", VERTICAL_SPLINE_BEARING_NOMINAL),
    str("verticalSplineBearingCount=", N_COL),
    str("verticalSplineBearingIdMm=", VERTICAL_SPLINE_BEARING_ID_MM),
    str("verticalSplineBearingOdMm=", VERTICAL_SPLINE_BEARING_OD_MM),
    str("verticalSplineBearingWidthMm=", VERTICAL_SPLINE_BEARING_WIDTH_MM),
    str("verticalSplineBearingSeatDiameterMm=", VERTICAL_SPLINE_BEARING_SEAT_D_MM),
    str("verticalSplineBearingSeatDepthMm=", VERTICAL_SPLINE_BEARING_SEAT_DEPTH_MM),
    str("verticalSplineBearingSeatShoulderMm=", VERTICAL_SPLINE_BEARING_SEAT_SHOULDER_T_MM),
    str("verticalSplineBearingSeatBottomYMm=", VERTICAL_SPLINE_BEARING_SEAT_BOTTOM_Y_MM),
    str("verticalSplineBearingAxisZMm=", DRIVE_AXIS_Z),
    str("verticalSplineBearingCenterYMm=", VERTICAL_SPLINE_BEARING_CENTER_Y_MM),
    str("verticalSplineBearingCapBottomYMm=", VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM),
    str("verticalSplineBearingCapTopYMm=", VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM),
    str("verticalSplineBearingCarrierPlateX0Mm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X0_MM),
    str("verticalSplineBearingCarrierPlateX1Mm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X1_MM),
    str("verticalSplineBearingCarrierPlateXLengthMm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X_LENGTH_MM),
    str("verticalSplineBearingCarrierPlateZ0Mm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM),
    str("verticalSplineBearingCarrierPlateZ1Mm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z1_MM),
    str("verticalSplineBearingCarrierPlateZLengthMm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z_LENGTH_MM),
    str("verticalSplineBearingCarrierPlateBottomYMm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM),
    str("verticalSplineBearingCarrierPlateTopYMm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM),
    str("verticalSplineBearingCarrierPlateThicknessMm=", VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM),
    str("verticalSplineBearingCarrierBossCount=", VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNT),
    str("verticalSplineBearingFloorBossOdMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_OD_MM),
    str("verticalSplineBearingFloorBossBaseOdMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_BASE_OD_MM),
    str("verticalSplineBearingFloorBossBaseHeightMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_BASE_H_MM),
    str("verticalSplineBearingFloorBossTopYMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM),
    str("verticalSplineBearingFloorBossHeightMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_HEIGHT_MM),
    str("verticalSplineBearingFloorBossPilotDiameterMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_D_MM),
    str("verticalSplineBearingFloorBossPilotDepthMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_DEPTH_MM),
    str("verticalSplineBearingFloorBossPilotBottomYMm=", VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_BOTTOM_Y_MM),
    str("verticalSplineBearingCarrierBossClearDiameterMm=", VERTICAL_SPLINE_BEARING_CARRIER_BOSS_CLEAR_D_MM),
    str("verticalSplineBearingCarrierBossCounterboreDiameterMm=", VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_D_MM),
    str("verticalSplineBearingCarrierBossCounterboreDepthMm=", VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_DEPTH_MM),
    str("verticalSplineBearingCarrierBossMount=", VERTICAL_SPLINE_BEARING_CARRIER_BOSS_MOUNT),
    str("verticalSplineBearingTowerBodyXWidthMm=", VERTICAL_SPLINE_BEARING_TOWER_BODY_X_WIDTH_MM),
    str("verticalSplineBearingTowerBodyZDepthMm=", VERTICAL_SPLINE_BEARING_TOWER_BODY_Z_DEPTH_MM),
    str("verticalSplineBearingTowerBoreDiameterMm=", VERTICAL_SPLINE_BEARING_TOWER_BORE_D_MM),
    str("verticalSplineBearingTowerRootFlareHeightMm=", VERTICAL_SPLINE_BEARING_TOWER_ROOT_FLARE_H_MM),
    str("verticalSplineBearingTowerRootXWidthMm=", VERTICAL_SPLINE_BEARING_TOWER_ROOT_X_WIDTH_MM),
    str("verticalSplineBearingTowerRootZDepthMm=", VERTICAL_SPLINE_BEARING_TOWER_ROOT_Z_DEPTH_MM),
    str("verticalSplineBearingTowerColumnDiameterMm=", VERTICAL_SPLINE_BEARING_TOWER_COLUMN_DIAMETER_MM),
    str("verticalSplineBearingTowerCapC5XWidthMm=", VERTICAL_SPLINE_BEARING_CAP_C5_X_WIDTH_MM),
    str("verticalSplineBearingTowerCapZDepthMm=", VERTICAL_SPLINE_BEARING_CAP_Z_DEPTH_MM),
    str("verticalSplineBearingTowerCapC5ZDepthMm=", VERTICAL_SPLINE_BEARING_CAP_C5_Z_DEPTH_MM),
    str("verticalSplineBearingC5RailWidthMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM),
    str("verticalSplineBearingC5RailZDepthMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_Z_DEPTH_MM),
    str("verticalSplineBearingC5RailCenterOffsetXMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_CENTER_OFFSET_X_MM),
    str("verticalSplineBearingC5RailBottomCenterOffsetXMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CENTER_OFFSET_X_MM),
    str("verticalSplineBearingC5RailRootWidthMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_WIDTH_MM),
    str("verticalSplineBearingC5RailRootZDepthMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_Z_DEPTH_MM),
    str("verticalSplineBearingC5RailCornerRadiusMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM),
    str("verticalSplineBearingC5RailProfile=", VERTICAL_SPLINE_BEARING_C5_RAIL_PROFILE),
    str("verticalSplineBearingC5RailClearanceMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_CLEARANCE_MM),
    str("verticalSplineBearingC5RailBottomClearanceMm=", VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CLEARANCE_MM),
    str("verticalSplineBearingBarY0Mm=", VERTICAL_SPLINE_BEARING_BAR_Y0_MM),
    str("verticalSplineBearingBarY1Mm=", VERTICAL_SPLINE_BEARING_BAR_Y1_MM),
    str("verticalSplineBearingBarXWidthMm=", VERTICAL_SPLINE_BEARING_BAR_X_WIDTH_MM),
    str("verticalSplineBearingBarYThicknessMm=", VERTICAL_SPLINE_BEARING_BAR_Y_THICKNESS_MM),
    str("verticalSplineBearingBarZMinMm=", VERTICAL_SPLINE_BEARING_BAR_Z_MIN_MM),
    str("verticalSplineBearingBarZMaxMm=", VERTICAL_SPLINE_BEARING_BAR_Z_MAX_MM),
    str("verticalSplineBearingBarZLengthMm=", VERTICAL_SPLINE_BEARING_BAR_Z_LENGTH_MM),
    str("verticalSplineBearingPartitionOverlapMm=", VERTICAL_SPLINE_BEARING_PARTITION_OVERLAP_MM),
    str("verticalSplineBearingPartitionKeyWidthMm=", VERTICAL_SPLINE_BEARING_PARTITION_KEY_WIDTH_MM),
    str("verticalSplineBearingPartitionKeyClearanceMm=", VERTICAL_SPLINE_BEARING_PARTITION_KEY_CLEARANCE_MM),
    str("verticalSplineBearingPartitionKeyZLengthMm=", VERTICAL_SPLINE_BEARING_PARTITION_KEY_Z_LENGTH_MM),
    str("verticalSplineBearingChainTopYMm=", VERTICAL_SPLINE_BEARING_CHAIN_TOP_Y_MM),
    str("verticalSplineBearingLowerPulleyBottomYMm=", VERTICAL_SPLINE_BEARING_LOWER_PULLEY_BOTTOM_Y_MM),
    str("verticalSplineBearingReturnGuideClearanceMm=", VERTICAL_SPLINE_BEARING_RETURN_GUIDE_CLEARANCE_MM),
    str("verticalSplineBearingLowerPulleyClearanceMm=", VERTICAL_SPLINE_BEARING_LOWER_PULLEY_CLEARANCE_MM),
    str("verticalSplineBearingReturnDriveClearanceMm=", VERTICAL_SPLINE_BEARING_RETURN_DRIVE_CLEARANCE_MM),
    str("verticalSplineBearingDetourColumn=", VERTICAL_SPLINE_BEARING_DETOUR_COLUMN),
    str("verticalSplineBearingDetourXOffsetMm=", VERTICAL_SPLINE_BEARING_DETOUR_X_OFFSET_MM),
    str("verticalSplineBearingDetourXClearanceMm=", VERTICAL_SPLINE_BEARING_DETOUR_CHAIN_CLEARANCE_MM),
    str("verticalSplineBearingDetourZClearanceMm=", VERTICAL_SPLINE_BEARING_DETOUR_Z_CLEARANCE_MM),
    str("verticalSplineBearingLowerDStubLengthMm=", VERTICAL_GEAR_BOTTOM_END_STUB_LENGTH),
    str("verticalSplineBearingUpperDStubLengthMm=", VERTICAL_GEAR_TOP_END_STUB_LENGTH),
    str("verticalSplineBearingSupport=", VERTICAL_SPLINE_BEARING_SUPPORT_MODE),
    "verticalSplineBearingCarrierPart=cabinet-clutch/vertical_spline_bearing_support",
    "verticalSplineBearingSupportPart=cabinet-clutch/vertical_spline_bearing_support",
    "verticalSplineBearingsPart=cabinet-clutch/vertical_spline_bearings_reference",
    str("drawerBottomYMm=", drawer_bottom_y(CENTER_GT2_ROW)),
    str("drawerRackYMm=", center_gt2_front_gear_y(CENTER_GT2_ROW)),
    str("frontPinionCenterYMm=", center_gt2_front_gear_y(CENTER_GT2_ROW)),
    str("frontPinionLowerFaceYMm=",
        center_gt2_front_pinion_lower_y(CENTER_GT2_ROW)),
    str("frontTimingPulleyDrawerRow=", CENTER_GT2_FRONT_PULLEY_ROW),
    "frontTimingPulleyLayer=next-drawer-bay",
    str("frontTimingPulleyZMm=", CENTER_GT2_FRONT_PULLEY_Z),
    str("frontTimingBeltYMm=", center_gt2_belt_y(CENTER_GT2_ROW)),
    str("frontTimingPulleyCenterYMm=", center_gt2_belt_y(CENTER_GT2_ROW)),
    str("frontTimingPulleyBottomYMm=",
        center_gt2_pulley_base_y(center_gt2_belt_y(CENTER_GT2_ROW))),
    str("frontTimingPulleyTopYMm=",
        center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))),
    str("frontTimingPulleyToPinionGapMm=",
        center_gt2_front_pinion_lower_y(CENTER_GT2_ROW)
            - center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))),
    str("frontTimingBearingCenterYMm=",
        center_gt2_front_timing_bearing_center_y(CENTER_GT2_ROW)),
    str("frontTimingBearingUpperFaceYMm=",
        center_gt2_front_timing_bearing_upper_y(CENTER_GT2_ROW)),
    str("frontTimingBearingLowerFaceYMm=",
        center_gt2_front_timing_bearing_lower_y(CENTER_GT2_ROW)),
    str("frontTimingBearingWidthMm=", DRAWER_FRONT_TIMING_BEARING_W),
    str("frontTimingBearingIdMm=", DRAWER_FRONT_TIMING_BEARING_ID),
    str("frontTimingBearingOdMm=", DRAWER_FRONT_TIMING_BEARING_OD),
    str("frontTimingBearingSeatDiameterMm=",
        DRAWER_FRONT_TIMING_BEARING_SEAT_D),
    str("frontTimingBearingSeatDepthMm=", DRAWER_FRONT_TIMING_BEARING_W),
    str("frontTimingBearingRetainerThicknessMm=",
        DRAWER_FRONT_TIMING_BEARING_RETAINER_T),
    str("frontTimingBearingRetainerBoreDiameterMm=",
        DRAWER_FRONT_TIMING_BEARING_RETAINER_BORE_D),
    str("frontTimingBearingShelfLowerFaceYMm=",
        center_gt2_front_shelf_lower_y(CENTER_GT2_ROW)),
    str("frontTimingBearingBossFusionOverlapMm=", EPS),
    str("frontTimingBearingBossBottomYMm=",
        center_gt2_front_bearing_boss_bottom_y(CENTER_GT2_ROW)),
    str("frontTimingBearingGearClearanceMm=",
        CENTER_GT2_FRONT_TIMING_BEARING_GEAR_GAP),
    str("frontTimingBearingPulleyClearanceMm=",
        center_gt2_front_timing_bearing_lower_y(CENTER_GT2_ROW)
            - center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))),
    "frontTimingBearingSupport=integral-shelf-stepped-seat",
    "frontTimingBearingFit=press-fit-3x6x2-bottom-captive",
    "frontDshaftProfile=D",
    str("frontDshaftStartYMm=",
        center_gt2_front_d_shaft_start_y(CENTER_GT2_ROW)),
    str("frontDshaftEndYMm=",
        center_gt2_front_d_shaft_end_y(CENTER_GT2_ROW)),
    str("frontDshaftLengthMm=",
        center_gt2_front_d_shaft_length(CENTER_GT2_ROW)),
    str("frontPinionThicknessMm=", FRONT_GEAR_T),
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
    str("linearBearingNominalIdMm=", CENTER_CLUTCH_LINEAR_BEARING_ID),
    str("linearBearingNominalOdMm=", CENTER_CLUTCH_LINEAR_BEARING_OD),
    str("linearBearingNominalLengthMm=", CENTER_CLUTCH_LINEAR_BEARING_L),
    str("linearBearingCount=", CENTER_CLUTCH_LINEAR_BEARING_COUNT),
    str("linearBearingCenterYOffsetMm=",
        CENTER_CLUTCH_LINEAR_BEARING_CENTER_Y_OFFSET),
    str("linearBearingInputRotorClearanceMm=",
        CENTER_CLUTCH_LINEAR_BEARING_INPUT_ROTOR_CLEARANCE),
    str("linearBearingCenterYMm=",
        center_clutch_linear_bearing_center_y(CENTER_GT2_ROW)),
    str("linearBearingSeatDiameterMm=", CENTER_CLUTCH_LINEAR_BEARING_SEAT_D),
    str("linearBearingSeatRadialClearanceMm=",
        CENTER_CLUTCH_LINEAR_BEARING_SEAT_RADIAL_CLEARANCE),
    str("linearBearingBlockWidthMm=", CENTER_CLUTCH_LINEAR_BEARING_BLOCK_X),
    str("linearBearingBlockYLengthMm=", CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Y),
    str("linearBearingBlockZLengthMm=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_LENGTH),
    str("linearBearingBlockZMarginMm=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_Z_MARGIN),
    str("linearBearingBlockMountHoleDiameterMm=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_D),
    str("linearBearingBlockMountHoleCount=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_COUNT),
    str("linearBearingBlockMountXOffsetMm=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_X_OFFSET),
    str("linearBearingBlockMountYOffsetMm=",
        CENTER_CLUTCH_LINEAR_BEARING_BLOCK_MOUNT_Y_OFFSET),
    "linearBearingBlockMount=mechanism-plate-integral-press-fit",
    "linearBearingModel=LM3UU-cutaway-reference",
    "linearBearingMovesWithInput=false",
    "linearBearingFitCouponPart=cabinet-clutch/center_linear_bearing_fit_coupon",
    "linearBearingPart=cabinet-clutch/center_linear_bearings_reference",
    "linearBearingBlockPart=cabinet-clutch/center_mechanism_plate",
    str("inputShaftProfile=", GT2_INPUT_SHAFT_PROFILE),
    str("inputShaftUpperDStartMm=", CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_START),
    str("inputShaftUpperDLengthMm=", CENTER_CLUTCH_INPUT_SHAFT_UPPER_D_LENGTH),
    str("inputShaftRoundStartMm=", CENTER_CLUTCH_INPUT_SHAFT_ROUND_START),
    str("inputShaftRoundLengthMm=", CENTER_CLUTCH_INPUT_SHAFT_ROUND_LENGTH),
    str("inputShaftRoundDiameterMm=", CENTER_CLUTCH_INPUT_SHAFT_ROUND_D),
    str("inputShaftLowerDStartMm=", CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_START),
    str("inputShaftLowerDLengthMm=", CENTER_CLUTCH_INPUT_SHAFT_LOWER_D_LENGTH),
    str("inputSleeveTopOffsetMm=", CENTER_CLUTCH_INPUT_SLEEVE_TOP_OFFSET),
    str("inputSleeveUpperDHeightMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D_HEIGHT),
    str("inputSleeveUpperDDiameterMm=", CENTER_CLUTCH_INPUT_SLEEVE_UPPER_D),
    str("inputSleeveLowerRoundOuterDiameterMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_OD),
    str("inputSleeveLowerRoundHeightMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_LOWER_ROUND_HEIGHT),
    str("inputSleeveDSocketDepthMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_DEPTH),
    str("inputSleeveDSocketClearanceMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_D_SOCKET_CLEARANCE),
    str("inputSleeveMagnetNominalDiameterMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_D),
    str("inputSleeveMagnetNominalLengthMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_L),
    str("inputSleeveMagnetPocketDiameterMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_D),
    str("inputSleeveMagnetPocketDepthMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_POCKET_DEPTH),
    str("inputSleeveMagnetBottomClearanceMm=",
        CENTER_CLUTCH_INPUT_SLEEVE_MAGNET_BOTTOM_CLEARANCE),
    str("inputSleeveMagnetOpenBottomYMm=",
        SNAKE_CHAIN_INPUT_SLEEVE_MAGNET_OPEN_BOTTOM_Y_MM),
    str("snakeChainHeightDatum=", SNAKE_CHAIN_HEIGHT_DATUM),
    str("snakeChainLinkTopOffsetMm=", SNAKE_CHAIN_LINK_TOP_OFFSET_MM),
    str("snakeChainReferenceRow=", SNAKE_CHAIN_REFERENCE_ROW),
    str("snakeChainReferencePathCenterYMm=",
        SNAKE_CHAIN_REFERENCE_PATH_CENTER_Y_MM),
    str("snakeChainVerticalShiftMm=", SNAKE_CHAIN_VERTICAL_SHIFT_MM),
    str("snakeChainServicePathCenterYMm=",
        SNAKE_CHAIN_SERVICE_PATH_CENTER_Y_MM),
    str("snakeChainReturnGuideCenterYMm=",
        SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y_MM),
    str("snakeChainReturnDriveXTrimMm=",
        SNAKE_CHAIN_RETURN_DRIVE_X_TRIM_MM),
    str("snakeChainServicePressXTrimMm=",
        SNAKE_CHAIN_SERVICE_PRESS_X_TRIM_MM),
    str("snakeChainMotorXOffsetMm=", SNAKE_CHAIN_MOTOR_X_OFFSET_MM),
    str("snakeChainTriggerMagnetSegmentIndex=",
        SNAKE_CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX),
    str("snakeChainTriggerMagnetDiameterMm=", SNAKE_CHAIN_TRIGGER_MAGNET_D),
    str("snakeChainTriggerMagnetLengthMm=", SNAKE_CHAIN_TRIGGER_MAGNET_L),
    str("snakeChainTriggerMagnetNormalOffsetMm=",
        SNAKE_CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM),
    str("snakeChainTriggerMagnetTopClearanceMm=",
        SNAKE_CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM),
    str("snakeChainTriggerMagnetAxialStartOffsetMm=",
        SNAKE_CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM),
    "inputShaftPart=cabinet-clutch/center_input_shaft_reference",
    "inputSleevePart=cabinet-clutch/center_input_sleeve",
    "inputSleeveMagnetPart=cabinet-clutch/center_input_sleeve_magnet_reference",
    str("outputShaftStartMm=", CENTER_CLUTCH_SHAFT_OUTPUT_START),
    str("outputShaftLengthMm=", CENTER_CLUTCH_SHAFT_OUTPUT_LENGTH),
    str("outputShaftDStartMm=", CENTER_CLUTCH_SHAFT_OUTPUT_D_START),
    str("outputShaftDLengthMm=", CENTER_CLUTCH_SHAFT_OUTPUT_D_LENGTH),
    str("outputShaftRoundStartMm=", CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_START),
    str("outputShaftRoundLengthMm=", CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_LENGTH),
    str("outputShaftRoundDiameterMm=", CENTER_CLUTCH_SHAFT_OUTPUT_ROUND_D),
    str("outputShaftTopProtrusionMm=",
        CENTER_CLUTCH_SHAFT_OUTPUT_TOP_PROTRUSION),
    str("outputShaftMotherSocketOverlapMm=",
        CENTER_CLUTCH_SHAFT_OUTPUT_MOTHER_SOCKET_OVERLAP),
    str("outputShaftProfile=", CENTER_CLUTCH_SHAFT_OUTPUT_PROFILE),
    str("outputBearingCount=", 2),
    str("bearingCount=", 2),
    str("bearingNominal=3x6x2"),
    str("bearingSeatDiameterMm=", CENTER_CLUTCH_BEARING_SEAT_D),
    str("bearingSeatDepthMm=", CENTER_CLUTCH_BEARING_SEAT_DEPTH),
    str("bearingBackShoulderMm=", CENTER_CLUTCH_BEARING_BACK_SHOULDER_T),
    str("bearingReferenceCenterOffsetMm=",
        CENTER_CLUTCH_BEARING_REFERENCE_CENTER_OFFSET),
    str("bearingCenterOffsetMm=", CENTER_CLUTCH_BEARING_CENTER_OFFSET),
    str("bearingPairSpacingMm=", CENTER_CLUTCH_BEARING_PAIR_SPACING),
    str("outputBearingBarWidthMm=", CENTER_CLUTCH_BEARING_BLOCK_X),
    str("outputBearingBarYLengthMm=", CENTER_CLUTCH_BEARING_BLOCK_Y),
    str("outputBearingBarY0OffsetMm=",
        CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET),
    str("outputBearingBarZLengthMm=",
        center_clutch_output_bearing_bar_z_length()),
    str("outputBearingBarZMarginMm=",
        CENTER_CLUTCH_BEARING_BLOCK_Z_MARGIN),
    str("outputBearingBarZMinMm=",
        center_clutch_output_bearing_bar_z0()),
    str("outputBearingBarZMaxMm=",
        center_clutch_output_bearing_bar_z1()),
    str("outputBearingBarMotherClearanceMm=",
        CENTER_CLUTCH_BEARING_BLOCK_Y0_OFFSET),
    str("outputBearingBarPlateOverlapMm=",
        CENTER_CLUTCH_BEARING_BLOCK_Z_OVERLAP),
    str("shaftDiameterMm=", GT2_D_AXIS_D),
    str("matingMagnetCount=", 2),
    str("inputSleeveMagnetCount=", 1),
    str("totalModeledMagnetCount=", 3),
    "rotaryBearingArrangement=output-two-3x6x2-in-one-integral-bar-input-free",
    "linearBearingArrangement=single-coaxial-with-integrated-seat",
    str("plateWidthMm=", CENTER_CLUTCH_PLATE_W),
    str("plateThicknessMm=", CENTER_CLUTCH_PLATE_T),
    str("platePartitionGapMm=", CENTER_CLUTCH_PLATE_PARTITION_GAP),
    str("plateFastenerCount=", CENTER_CLUTCH_PLATE_FASTENER_COUNT),
    str("plateM3ClearanceMm=", CENTER_CLUTCH_M3_CLEAR_D),
    str("partitionSelfTapPilotDiameterMm=",
        CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_D),
    str("partitionSelfTapPilotDepthMm=",
        CENTER_CLUTCH_PARTITION_SELF_TAP_PILOT_DEPTH),
    str("partitionSelfTapBottomWallMm=",
        CENTER_CLUTCH_PARTITION_SELF_TAP_BOTTOM_WALL),
    str("partitionBossPerCellCount=",
        CENTER_CLUTCH_PARTITION_BOSS_PER_CELL_COUNT),
    str("partitionBossCount=", CENTER_CLUTCH_PARTITION_BOSS_COUNT),
    str("partitionBossCenterOffsetXMm=",
        CENTER_CLUTCH_PLATE_MOUNT_X_OFFSET),
    str("partitionBossCenterOffsetYMm=",
        CENTER_CLUTCH_PLATE_MOUNT_Y_OFFSET),
    str("partitionBossOuterDiameterMm=",
        CENTER_CLUTCH_PARTITION_BOSS_OD),
    str("partitionBossHeightMm=", CENTER_CLUTCH_PARTITION_BOSS_HEIGHT),
    str("partitionBossHeightDeficitMm=",
        CENTER_CLUTCH_PLATE_T - CENTER_CLUTCH_PARTITION_BOSS_HEIGHT),
    str("plateBeltPassageHalfWidthMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_HALF_X),
    str("plateBeltPassageSlotCount=", 2),
    str("plateBeltPassageSlotCenterOffsetMm=",
        CENTER_CLUTCH_PLATE_BELT_SLOT_CENTER_OFFSET),
    str("plateBeltPassageSlotWidthMm=",
        2 * CENTER_CLUTCH_PLATE_BELT_SLOT_HALF_X),
    str("plateBeltPassageAxialWidthMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_Y),
    str("plateBeltPassageRadialClearanceMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_RADIAL_CLEAR),
    str("plateBeltPassageAxialClearanceMm=",
        CENTER_CLUTCH_PLATE_BELT_PASSAGE_AXIAL_CLEAR),
    "partitionBeltPassageType=per-drawer-cell-2GT-straight-run-windows",
    str("partitionBeltPassageWindowCount=", N_COL * N_ROW),
    str("partitionBeltPassage2GTWindowCount=", N_COL * N_ROW),
    str("partitionBeltPassageCenterXMm=", clutch_col_x(CENTER_GT2_COL)),
    str("partitionBeltPassageCenterYMm=",
        center_gt2_belt_y(CENTER_GT2_ROW)),
    str("partitionBeltPassageRelativeXMm=", 0),
    str("partitionBeltPassageRelativeYMm=",
        center_gt2_belt_y(CENTER_GT2_ROW)
            - world_row_center_y(CENTER_GT2_FRONT_PULLEY_ROW)),
    str("partitionBeltPassagePlateZMm=", WORLD_PARTITION_BACK_Z),
    str("partitionBeltPassagePlateThicknessMm=", WORLD_PARTITION_T),
    str("partitionBeltPassageHalfWidthMm=",
        PARTITION_BELT_PASSAGE_WINDOW_HALF_X),
    str("partitionBeltPassageAxialWidthMm=",
        PARTITION_BELT_PASSAGE_WINDOW_AXIAL_WIDTH),
    str("partitionBeltPassageRadialClearanceMm=",
        PARTITION_BELT_PASSAGE_WINDOW_RADIAL_CLEAR
            + GT2_BELT_RADIAL_CLEARANCE),
    str("partitionBeltPassageAxialClearanceMm=",
        PARTITION_BELT_PASSAGE_WINDOW_AXIAL_CLEAR),
    "plateSupport=partition-boss-locators-plus-four-self-tapping-screws",
    "actuation=permanent-magnet",
    "engageOnlyWhenStopped=true",
    "releaseBeforeReturn=true",
    "inputSideAdditionalMechanism=none",
    str("centerCol=", CENTER_GT2_COL),
    str("centerRow=", CENTER_GT2_ROW),
    "inputPart=cabinet-clutch/center_input_rotor",
    "outputPart=cabinet-clutch/center_output_rotor",
    "outputBearingSupportPart=cabinet-clutch/center_mechanism_plate",
    "mechanismPlatePart=cabinet-clutch/center_mechanism_plate",
    "outputShaftPart=cabinet-clutch/center_output_shaft_reference",
    "outputBearingsPart=cabinet-clutch/center_output_bearings_reference"
);
assert(
    CLUTCH_PART == "assembly"
    || CLUTCH_PART == "cabinet"
    || CLUTCH_PART == "cabinet_frame"
    || CLUTCH_PART == "cabinet_partition"
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
    || CLUTCH_PART == "vertical_spline_bearing_support"
    || CLUTCH_PART == "vertical_spline_bearings"
    || CLUTCH_PART == "vertical_rack"
    || CLUTCH_PART == "column_sync_belt_bottom"
    || CLUTCH_PART == "column_sync_belt_top"
    || CLUTCH_PART == "column_sync_tensioner"
    || CLUTCH_PART == "center_station_template_assembly"
    || CLUTCH_PART == "center_input_rotor"
    || CLUTCH_PART == "center_output_rotor"
    || CLUTCH_PART == "center_input_sleeve"
    || CLUTCH_PART == "center_input_sleeve_magnet"
    || CLUTCH_PART == "center_input_carriage"
    || CLUTCH_PART == "center_output_bearing_bar"
    || CLUTCH_PART == "center_guide_rails"
    || CLUTCH_PART == "center_linear_bearings"
    || CLUTCH_PART == "center_linear_bearing_retainers"
    || CLUTCH_PART == "center_linear_bearing_fit_coupon"
    || CLUTCH_PART == "center_stops"
    || CLUTCH_PART == "center_mechanism_plate"
    || CLUTCH_PART == "center_plate_belt_collision"
    || CLUTCH_PART == "center_partition_belt_collision"
    || CLUTCH_PART == "vertical_spline_support_chain_collision"
    || CLUTCH_PART == "vertical_spline_support_drive_collision"
    || CLUTCH_PART == "vertical_spline_support_partition_window_collision"
    || CLUTCH_PART == "center_clutch_pair_collision"
    || CLUTCH_PART == "center_carriage_rail_collision"
    || CLUTCH_PART == "center_input_rotor_carriage_collision"
    || CLUTCH_PART == "center_stops_carriage_collision"
    || CLUTCH_PART == "center_stops_retainer_collision"
    || CLUTCH_PART == "center_guide_stop_collision"
    || CLUTCH_PART == "center_input_shaft"
    || CLUTCH_PART == "center_output_shaft"
    || CLUTCH_PART == "center_input_bearings"
    || CLUTCH_PART == "center_output_bearings"
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
    || CLUTCH_PART == "drawer_rack_guide_rollers"
    || CLUTCH_PART == "drawer_rack_guide_rails"
    || CLUTCH_PART == "drawer_guide_flange_rail_collision"
    || CLUTCH_PART == "drawer_front_drive_shelf_collision"
    || CLUTCH_PART == "drawer_front_pinion_bearing_support"
    || CLUTCH_PART == "drawer_front_pinion_bearings"
    || CLUTCH_PART == "front_timing_bearing_support"
    || CLUTCH_PART == "front_timing_bearing"
    || CLUTCH_PART == "front_d_axis"
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
assert(abs(CENTER_GT2_FRONT_PULLEY_Z + CENTER_FRONT_DRIVE_AXIS_NATIVE_Y) < 0.001,
    "center front drive depth must match the printable cabinet shelf seat");
assert(N_ROW == 3 && SERVICE_LAYERS == 1,
    "current first article is the three-drawer one-service-layer layout");
assert(DRAWER_RACK_BODY_Y > 0
        && abs(drawer_rack_y(CENTER_GT2_ROW)
            + DRAWER_RACK_BODY_Y / 2
            - drawer_bottom_y(CENTER_GT2_ROW)) < 0.001,
    "drawer rack backing must terminate at the drawer underside");
assert(DRAWER_RACK_BODY_X > 0
        && DRAWER_RACK_TOOTH_H > 0
        && DRAWER_RACK_TOOTH_OVERHANG_X >= 0,
    "drawer rack X envelope and tooth geometry must be positive");
assert(CENTER_FRONT_DRIVE_LIFT_MM > 0,
    "center front drive must lift above the intact shelf");
assert(abs(
    center_gt2_front_gear_y(CENTER_GT2_ROW)
        - (drawer_rack_y(CENTER_GT2_ROW) + CENTER_FRONT_DRIVE_LIFT_MM)
) < 0.001,
    "center front rack lift must be applied to the rack and pinion together");
assert(abs(
    center_gt2_front_gear_y(CENTER_GT2_ROW)
        - DRAWER_RACK_BODY_Y / 2
        - world_row_y(CENTER_GT2_ROW)
        - CENTER_FRONT_RACK_ABOVE_SHELF_GAP
) < 0.001,
    "center rack lower edge must sit above the shelf top");
assert(abs(
    center_gt2_front_timing_bearing_upper_y(CENTER_GT2_ROW)
        - world_row_y(CENTER_GT2_ROW)
) < 0.001,
    "center timing bearing upper edge must be flush with the shelf top");
assert(CENTER_FRONT_BEARING_REINFORCEMENT_DISC_DIAMETER
        > CENTER_FRONT_BEARING_OD
        && CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS > 0,
    "center timing bearing must have a real lower reinforcement disc");
assert(drawer_rack_z1(CENTER_GT2_FRONT_PULLEY_Z)
        > drawer_rack_z0() + DRAWER_RACK_PITCH,
    "drawer rack must leave a positive tooth run");
assert(abs(
    center_gt2_front_gear_y(CENTER_GT2_ROW)
        - (drawer_rack_y(CENTER_GT2_ROW) + CENTER_FRONT_DRIVE_LIFT_MM)
) < 0.001,
    "center front pinion must share the lifted moving drawer rack height");
assert(abs(
    center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))
        + CENTER_GT2_FRONT_TIMING_BEARING_GEAR_GAP
        + DRAWER_FRONT_TIMING_BEARING_W
        + CENTER_GT2_FRONT_TIMING_BEARING_PULLEY_GAP
        + CENTER_FRONT_DRIVE_LIFT_MM
        + FRONT_GEAR_T / 2
        - center_gt2_front_gear_y(CENTER_GT2_ROW)
) < 0.001,
    "center 2GT pulley must sit in the lower bay below the shelf bearing");
assert(CENTER_GT2_FRONT_PULLEY_ROW >= 0
        && CENTER_GT2_FRONT_PULLEY_ROW < N_ROW,
    "center front pulley must have a real lower drawer bay");
assert(center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))
        < center_gt2_front_timing_bearing_lower_y(CENTER_GT2_ROW)
            - CENTER_GT2_FRONT_TIMING_BEARING_PULLEY_GAP + 0.001,
    "center front pulley must clear the shelf-thickness bearing");
assert(center_gt2_front_timing_bearing_upper_y(CENTER_GT2_ROW)
        < center_gt2_front_pinion_lower_y(CENTER_GT2_ROW) + 0.001,
    "center shelf bearing must clear the upper pinion");
assert(abs(DRAWER_FRONT_TIMING_BEARING_W - CENTER_FRONT_BEARING_WIDTH) < 0.001
        && abs(DRAWER_FRONT_TIMING_BEARING_ID - CENTER_FRONT_BEARING_ID) < 0.001
        && abs(DRAWER_FRONT_TIMING_BEARING_OD - CENTER_FRONT_BEARING_OD) < 0.001,
    "center front bearing must be the purchased 3x6x2 part");
assert(DRAWER_FRONT_TIMING_BEARING_W < WORLD_SHELF_T
        && DRAWER_FRONT_TIMING_BEARING_RETAINER_T > 0
        && DRAWER_FRONT_TIMING_BEARING_RETAINER_T
            + DRAWER_FRONT_TIMING_BEARING_W <= WORLD_SHELF_T + 0.001,
    "center front bearing must leave a printed shelf shoulder");
assert(abs(
    center_gt2_front_bearing_boss_bottom_y(CENTER_GT2_ROW)
        + DRAWER_FRONT_TIMING_BEARING_RETAINER_T
        + CENTER_FRONT_BEARING_REINFORCEMENT_DISC_THICKNESS
        - center_gt2_front_timing_bearing_lower_y(CENTER_GT2_ROW)
    ) < 0.001,
    "center front bearing bottom shoulder must be derived from the bearing");
assert(abs(
    center_gt2_front_shelf_lower_y(CENTER_GT2_ROW)
        - (world_row_y(CENTER_GT2_ROW) - WORLD_SHELF_T)
    ) < 0.001,
    "center front bearing boss must terminate on the real shelf underside");
assert(center_gt2_front_d_shaft_length(CENTER_GT2_ROW) > 0
        && center_gt2_front_d_shaft_length(CENTER_GT2_ROW)
            > DRAWER_FRONT_TIMING_BEARING_W,
    "center front D shaft must bridge pinion, shelf bearing and pulley");
assert(center_gt2_pulley_base_y(center_gt2_belt_y(CENTER_GT2_ROW))
        >= world_row_y(CENTER_GT2_FRONT_PULLEY_ROW) + DRAWER_CLEAR
            - 0.001
        && center_gt2_pulley_top_y(center_gt2_belt_y(CENTER_GT2_ROW))
            <= world_row_y(CENTER_GT2_FRONT_PULLEY_ROW) + BAY_H - DRAWER_CLEAR
                + 0.001,
    "center front timing pulley must fit inside the next drawer bay");
assert(center_gt2_belt_y(CENTER_GT2_ROW)
        < center_gt2_front_gear_y(CENTER_GT2_ROW),
    "center drawer belt must stay below the front pinion");
assert(drawer_guide_z1(CENTER_GT2_FRONT_PULLEY_Z)
        > drawer_guide_z0(CENTER_GT2_FRONT_PULLEY_Z)
            + 2 * DRAWER_GUIDE_ROLLER_Z_MARGIN,
    "drawer guide rails must leave two roller stations");
assert(DRAWER_GUIDE_681_OD > DRAWER_GUIDE_681_ID
        && DRAWER_GUIDE_681_SEAT_D > DRAWER_GUIDE_681_OD,
    "681 guide bearing seat must leave a press-fit annulus");
assert(DRAWER_GUIDE_PARTITION_SUPPORT_T >= WORLD_DIV_T - EPS
        && DRAWER_GUIDE_RAIL_ATTACH_OVERLAP > 0
        && DRAWER_GUIDE_RAIL_ATTACH_OVERLAP < DRAWER_GUIDE_PARTITION_SUPPORT_T,
    "C rail must attach to the real divider/side-panel vertical member");
assert(DRAWER_GUIDE_C_DEPTH
        > DRAWER_CLEAR + DRAWER_GUIDE_C_FLANGE_PROJECTION
            + DRAWER_GUIDE_C_FLANGE_CLEARANCE,
    "inward C rail must extend beyond the drawer flange with a running gap");
assert(DRAWER_GUIDE_C_FLANGE_END_CLEARANCE >= DRAWER_GUIDE_C_FLANGE_CLEARANCE,
    "inward C rail flange must stop before its free end with the running gap");
for (guide_col = [0:N_COL - 1]) {
    assert(drawer_left_guide_partition_face_x(guide_col)
            >= world_col_x(guide_col) - EPS
        && drawer_left_guide_rail_end_x(guide_col)
            <= world_col_x(guide_col) + WORLD_BAY_W + EPS,
        "left C rail must stay inside its own drawer cell");
    assert(drawer_right_guide_partition_face_x(guide_col)
            <= world_col_x(guide_col) + WORLD_BAY_W + EPS
        && drawer_right_guide_rail_end_x(guide_col)
            >= world_col_x(guide_col) - EPS,
        "right C rail must stay inside its own drawer cell");
    assert(drawer_left_guide_tail_bearing_x(guide_col)
            >= drawer_left_guide_partition_face_x(guide_col)
        && drawer_left_guide_tail_bearing_x(guide_col)
            <= drawer_left_guide_rail_end_x(guide_col),
        "left 681 tail bearing must remain inside the inward lip");
    assert(drawer_right_guide_tail_bearing_x(guide_col)
            <= drawer_right_guide_partition_face_x(guide_col)
        && drawer_right_guide_tail_bearing_x(guide_col)
            >= drawer_right_guide_rail_end_x(guide_col),
        "right 681 tail bearing must remain inside the inward lip");
}
assert(DRAWER_PINION_MR63_OD > DRAWER_PINION_MR63_ID
        && DRAWER_PINION_MR63_SEAT_D > DRAWER_PINION_MR63_OD,
    "MR63 pinion bearing seat must leave a press-fit annulus");
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
assert(VERTICAL_GEAR_BOTTOM_END_STUB_LENGTH >= 12.0,
    "lower spline D stub must reach the fixed 3x6x2 bearing");
assert(VERTICAL_GEAR_TOP_END_STUB_LENGTH > 0,
    "upper spline D stub must remain positive");
assert(VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNT == 8,
    "removable spline bearing carrier must use eight floor bosses");
assert(VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X0_MM > WALL
        && VERTICAL_SPLINE_BEARING_CARRIER_PLATE_X1_MM < W - WALL,
    "removable spline bearing carrier must stay inside the cabinet width");
assert(VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z0_MM > -D + WALL
        && VERTICAL_SPLINE_BEARING_CARRIER_PLATE_Z1_MM
            < WORLD_PARTITION_BACK_Z - EPS,
    "removable spline bearing carrier must stay in the rear cavity");
assert(VERTICAL_SPLINE_BEARING_CARRIER_PLATE_T_MM >= 3.0,
    "removable spline bearing carrier plate must retain a printable load path");
assert(VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM
        > VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM);
assert(VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM
        >= VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM - EPS
    && VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM
        <= VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM + EPS
    && VERTICAL_SPLINE_BEARING_FLOOR_BOSS_PILOT_BOTTOM_Y_MM >= WALL - EPS,
    "floor boss must pass through the carrier and keep its blind pilot inside the floor");
assert(abs(VERTICAL_SPLINE_BEARING_CARRIER_PLATE_BOTTOM_Y_MM - WALL) < EPS
    && abs(VERTICAL_SPLINE_BEARING_FLOOR_BOSS_TOP_Y_MM
        - VERTICAL_SPLINE_BEARING_CARRIER_PLATE_TOP_Y_MM) < EPS,
    "carrier bottom must meet the cabinet floor top and Boss top must flush with carrier top");
assert(VERTICAL_SPLINE_BEARING_CARRIER_BOSS_CLEAR_D_MM
        > VERTICAL_SPLINE_BEARING_FLOOR_BOSS_OD_MM,
    "carrier Ø5.2 holes must clear the Ø5 floor bosses");
assert(VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_D_MM == 0
    && VERTICAL_SPLINE_BEARING_CARRIER_BOSS_COUNTERBORE_DEPTH_MM == 0,
    "carrier must use top screws over plain circular bosses, not underside pockets");
assert(VERTICAL_SPLINE_BEARING_CAP_BOTTOM_Y_MM
        > VERTICAL_SPLINE_BEARING_CHAIN_TOP_Y_MM + 0.45,
    "bearing caps must clear the snake return guide");
assert(VERTICAL_SPLINE_BEARING_CAP_TOP_Y_MM
        < VERTICAL_SPLINE_BEARING_LOWER_PULLEY_BOTTOM_Y_MM - 0.45,
    "bearing caps must clear the lower 2GT pulley");
assert(VERTICAL_SPLINE_BEARING_SEAT_SHOULDER_T_MM >= 0.20 - EPS,
    "bearing seat must retain a positive lower shoulder");
assert(VERTICAL_SPLINE_BEARING_TOWER_BORE_D_MM
        > VERTICAL_SPLINE_BEARING_ID_MM,
    "tower bore must clear the 3 mm spline shaft");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_CLEARANCE_MM >= 0.45,
    "C5 split tower rails must clear the purchased motor body");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CLEARANCE_MM >= 0.45,
    "C5 split tower roots must clear the purchased motor body");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_BOTTOM_CENTER_OFFSET_X_MM
        > VERTICAL_SPLINE_BEARING_C5_RAIL_CENTER_OFFSET_X_MM,
    "C5 split tower braces must flare outward toward the carrier");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_WIDTH_MM
        > VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM,
    "C5 split tower roots must be wider than the upper braces");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_ROOT_Z_DEPTH_MM
        > VERTICAL_SPLINE_BEARING_C5_RAIL_Z_DEPTH_MM,
    "C5 split tower roots must have a deeper Z load footprint");
assert(VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM > 0.80
        && VERTICAL_SPLINE_BEARING_C5_RAIL_CORNER_RADIUS_MM
            < VERTICAL_SPLINE_BEARING_C5_RAIL_WIDTH_MM / 2,
    "C5 split tower rounded brace radius must be printable");
assert(VERTICAL_SPLINE_BEARING_RETURN_DRIVE_CLEARANCE_MM > 0.45,
    "bearing caps must clear the 12T snake return drive");
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
// The motor is intentionally allowed to rise inside the Ω tensioner stroke;
// the floor boss therefore follows the raised seat stop instead of assuming
// the old motor-at-floor datum.  Keep the stop in the low rear-cavity zone,
// but do not reject the valid +Z tension adjustment at 7 mm.
assert(SNAKE_MOTOR_BOSS_STAGE1_TOP_Y > WALL
    && SNAKE_MOTOR_BOSS_STAGE1_TOP_Y < 12.0,
    "snake motor boss first step must remain a low printable floor stop");
assert(SNAKE_MOTOR_BOSS_GUIDE_OD > SNAKE_MOTOR_BOSS_GUIDE_BORE_D,
    "snake motor boss guide must leave an annular wall");
assert(SNAKE_MOTOR_BOSS_GUIDE_TOP_Y < WORLD_GRID_ORIGIN_Y,
    "snake motor boss guides must remain below the drawer grid");
assert(SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z
        - SNAKE_MOTOR_BOSS_BASE_D / 2 > -D + WALL
    && SNAKE_MOTOR_MOUNT_SEAT_CENTER_Z
        + SNAKE_MOTOR_BOSS_BASE_D / 2 < -WALL,
    "snake motor Boss bases must stay inside the rear depth");
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
