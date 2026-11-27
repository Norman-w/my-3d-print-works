# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from parts.standard_parts import CatalogPart, PartKind, PartsCatalog


# ===== 分区：常量/配置 =====
GEAR_STAGE_EFFICIENCY = 0.85
SCREW_FRICTION_FACTOR = 0.2
SCREW_SHEAR_FACTOR = 0.58
CORE_TO_MAJOR = 0.8
MOTOR_MOUNT_RADIUS_MM = 4.5


# ===== 分区：模型/类型 =====
@dataclass
class PartReport:
    id: str
    kind: str
    title: str
    ok: bool
    metrics: dict[str, float]
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "ok": self.ok,
            "metrics": self.metrics,
            "notes": self.notes,
        }


class PartSimulator(ABC):
    kind: PartKind

    @abstractmethod
    def simulate(self, part: CatalogPart, catalog: PartsCatalog) -> PartReport:
        raise NotImplementedError


# ===== 分区：业务逻辑 =====
class DcMotorSimulator(PartSimulator):
    kind = PartKind.DcMotor

    def simulate(self, part: CatalogPart, catalog: PartsCatalog) -> PartReport:
        stall = part.number("stall_torque_nm")
        rpm = part.number("no_load_rpm")
        resistance = part.number("resistance_ohm")
        voltage = part.number("voltage_v")
        kt = stall * resistance / voltage
        return PartReport(
            id=part.id,
            kind=part.kind.name,
            title=part.title,
            ok=stall > 0 and rpm > 0,
            metrics={
                "voltage_v": voltage,
                "stall_torque_nm": stall,
                "no_load_rpm": rpm,
                "kt_nm_per_a": kt,
                "stall_current_a": voltage / resistance,
            },
            notes=["电气参数按堵转力矩反推，未拆减速箱内部损耗。"],
        )


class SpurGearSimulator(PartSimulator):
    kind = PartKind.SpurGear

    def simulate(self, part: CatalogPart, catalog: PartsCatalog) -> PartReport:
        module = part.number("module_mm")
        teeth = part.number("teeth")
        mate = catalog.require(str(part.fields["meshes_with"]))
        center = module * (teeth + mate.number("teeth")) / 2
        actual = math.dist(part.numbers("origin_mm"), mate.numbers("origin_mm"))
        ok = abs(module - mate.number("module_mm")) < 1e-9 and abs(actual - center) < 0.05
        notes = [f"与 {mate.title} 中心距要求 {center:.3f} mm，目录放置 {actual:.3f} mm。"]
        if abs(module - mate.number("module_mm")) >= 1e-9:
            notes.append("配对齿轮模数不一致。")
        return PartReport(
            id=part.id,
            kind=part.kind.name,
            title=part.title,
            ok=ok,
            metrics={
                "module_mm": module,
                "teeth": teeth,
                "pitch_diameter_mm": module * teeth,
                "required_center_distance_mm": center,
                "placed_center_distance_mm": actual,
                "ratio_from_mate": mate.number("teeth") / teeth,
            },
            notes=notes,
        )


class MetricScrewSimulator(PartSimulator):
    kind = PartKind.MetricScrew

    def simulate(self, part: CatalogPart, catalog: PartsCatalog) -> PartReport:
        steel = catalog.material(part.material)
        diameter = part.number("thread_major_mm")
        core_area = math.pi * (CORE_TO_MAJOR * diameter / 2) ** 2
        tensile_n = 0.8 * steel.yield_mpa * core_area
        shear_n = SCREW_SHEAR_FACTOR * steel.yield_mpa * core_area
        clamp_n = 0.5 * tensile_n
        torque_nmm = SCREW_FRICTION_FACTOR * clamp_n * diameter
        ok = shear_n > 20 and tensile_n > 40
        return PartReport(
            id=part.id,
            kind=part.kind.name,
            title=part.title,
            ok=ok,
            metrics={
                "tensile_allow_n": tensile_n,
                "shear_allow_n": shear_n,
                "design_clamp_n": clamp_n,
                "install_torque_nmm": torque_nmm,
            },
            notes=["钢对钢紧固件估算；本阶段不含塑料壳体螺孔。"],
        )


SIMULATORS: dict[PartKind, PartSimulator] = {
    PartKind.DcMotor: DcMotorSimulator(),
    PartKind.SpurGear: SpurGearSimulator(),
    PartKind.MetricScrew: MetricScrewSimulator(),
}


def simulate_drive_chain(catalog: PartsCatalog, part_reports: list[PartReport]) -> dict[str, Any]:
    motor = catalog.require("motor_n20")
    pinion = catalog.require("pinion_m05_z8")
    wheel = catalog.require("spur_m05_z40")
    ratio = wheel.number("teeth") / pinion.number("teeth")
    stall = motor.number("stall_torque_nm")
    output_nm = stall * ratio * GEAR_STAGE_EFFICIENCY
    output_rpm = motor.number("no_load_rpm") / ratio
    screws = [report for report in part_reports if report.kind == PartKind.MetricScrew.name]
    mount_m = MOTOR_MOUNT_RADIUS_MM / 1000
    shear_each = stall / (max(len(screws), 1) * mount_m)
    min_allow = min(report.metrics["shear_allow_n"] for report in screws)
    screws_hold = shear_each < min_allow
    notes = [
        "无壳体：只仿真电机 → 齿轮副 → 安装螺钉。",
        "输出轴力矩 = 电机堵转 × 齿比 × 0.85 啮合效率。",
    ]
    if not screws_hold:
        notes.append("螺钉抗剪不足以承受电机堵转反力。")
    return {
        "gear_ratio": ratio,
        "motor_stall_nm": stall,
        "output_shaft_nm": output_nm,
        "output_no_load_rpm": output_rpm,
        "screw_shear_each_n": shear_each,
        "screw_shear_allow_n": min_allow,
        "screws_hold_stall": screws_hold,
        "notes": notes,
    }


# ===== 分区：公开 API =====
def simulate_catalog(catalog: PartsCatalog) -> dict[str, Any]:
    reports: list[PartReport] = []
    for part in catalog.parts:
        simulator = SIMULATORS.get(part.kind)
        if simulator is None:
            reports.append(
                PartReport(
                    id=part.id,
                    kind=part.kind.name,
                    title=part.title,
                    ok=False,
                    metrics={},
                    notes=["此阶段只仿真标准件，跳过非目录零件。"],
                )
            )
            continue
        reports.append(simulator.simulate(part, catalog))
    drive = simulate_drive_chain(catalog, reports)
    return {
        "revision": catalog.revision,
        "ok": all(report.ok for report in reports) and bool(drive["screws_hold_stall"]),
        "parts": [report.to_json() for report in reports],
        "drive": drive,
        "cad": {"engine": "FreeCAD", "version_requested": "1.1.3", "format": "step"},
    }
