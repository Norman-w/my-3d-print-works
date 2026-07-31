// SmartPaddle M5 — 完整拍柄入口（当前阶段：尾段 coupon + 电池装配）
// 不覆盖 M4 paddle_shell.scad。预览请用 assembly_m5.scad 或 ./scripts/preview-m5.sh

include <../generated/profiles.scad>
include <parameters_m5.scad>
use <assembly_m5.scad>

// ===== 分区：常量/配置 =====
// "tail_coupon" | 透传到 assembly 的状态名
HALF = "tail_coupon";
ASSEMBLY_STATE = "cartridge_locked";

// ===== 分区：公开 API =====
if (HALF == "tail_coupon") {
    m5_assembly(ASSEMBLY_STATE);
} else {
    m5_assembly(HALF);
}

echo("=== SmartPaddle M5 shell entry ===");
echo(str("HALF=", HALF, " ASSEMBLY_STATE=", ASSEMBLY_STATE));
