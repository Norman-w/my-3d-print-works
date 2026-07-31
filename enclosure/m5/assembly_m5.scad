// SmartPaddle M5 — 装配预览入口（不生成 STL，直接 OpenSCAD / 脚本打开）
//
// 用法:
//   openscad enclosure/m5/assembly_m5.scad
//   ASSEMBLY_STATE="latch_pressed" openscad ... -D 'ASSEMBLY_STATE="latch_pressed"'
//
// ASSEMBLY_STATE:
//   shell_only | board_only | cartridge_removed | cartridge_inserting
//   cartridge_locked | cartridge_ejected_3mm | latch_pressed
//   usb_plug_inserted | exploded | section_x | section_z | clearance_debug

include <../generated/profiles.scad>
include <parameters_m5.scad>
use <battery_cartridge_m5.scad>
use <latch_m5.scad>
use <interface_envelopes_m5.scad>
use <tail_housing_m5.scad>

// ===== 分区：常量/配置 =====
ASSEMBLY_STATE = "cartridge_locked";
SHOW_ENVELOPES = true;
SHELL_ALPHA = 0.35;
$fn = 48;

m5_echo_feasibility();

// ===== 分区：业务逻辑 =====
function _m5_cartridge_dy(state) =
    state == "cartridge_removed" ? -45 :
    state == "cartridge_inserting" ? -18 :
    state == "cartridge_ejected_3mm" ? -m5_eject_travel_y :
    state == "latch_pressed" ? -m5_eject_travel_y :
    state == "exploded" ? -28 :
    0;

function _m5_latch_travel(state) =
    state == "latch_pressed" ? m5_latch_travel_x :
    state == "cartridge_ejected_3mm" ? m5_latch_travel_x :
    state == "cartridge_inserting" ? m5_latch_travel_x * 0.35 :
    state == "exploded" ? m5_latch_travel_x + 4 :
    0;

function _m5_eject_state(state) =
    state == "cartridge_locked" ? "locked" :
    state == "cartridge_ejected_3mm" || state == "latch_pressed" ? "ejected" :
    state == "cartridge_removed" || state == "exploded" ? "free" :
    "locked";

// ===== 分区：公开 API =====
module m5_assembly(state = ASSEMBLY_STATE) {
    show_shell = state != "board_only";
    show_cart =
        state != "shell_only" &&
        state != "board_only" &&
        state != "cartridge_removed";
    show_latch = state != "shell_only" && state != "board_only";
    show_board = state != "shell_only";

    if (show_shell) {
        if (state == "section_x") {
            intersection() {
                m5_tail_housing(SHELL_ALPHA);
                translate([-500, 0, 0])
                    cube([1000, 2000, 2000], center = true);
            }
        } else if (state == "section_z") {
            intersection() {
                m5_tail_housing(SHELL_ALPHA);
                translate([0, 0, -500])
                    cube([2000, 2000, 1000], center = true);
            }
        } else {
            m5_tail_housing(SHELL_ALPHA);
        }
    }

    if (show_cart)
        m5_battery_cartridge_placed(
            _m5_cartridge_dy(state),
            show_internals = true
        );

    if (show_latch) {
        m5_latch_placed(_m5_latch_travel(state));
        m5_eject_spring_placed(_m5_eject_state(state));
    }

    if (show_board && SHOW_ENVELOPES)
        m5_interface_envelopes_placed(
            show_usb_plug = (state == "usb_plug_inserted")
        );

    if (state == "clearance_debug") {
        color([1, 0, 0, 0.25])
            translate([0, m5_datum_a_y + 10, 0])
                cube([
                    m5_required_x(),
                    20,
                    max(m5_cartridge_outer_z, m5_tail_board_z)
                ], center = true);
    }

    if (state == "exploded") {
        translate([m5_sx() * -22, 0, 0])
            m5_interface_envelopes_placed();
        translate([m5_sx() * 28, -10, 0])
            m5_latch_placed(m5_latch_travel_x + 2);
    }
}

m5_assembly(ASSEMBLY_STATE);

echo(str("ASSEMBLY_STATE=", ASSEMBLY_STATE));
echo("提示: 在 OpenSCAD 中切换 -D 'ASSEMBLY_STATE=\"latch_pressed\"' 等状态查看开扣/顶出。");
