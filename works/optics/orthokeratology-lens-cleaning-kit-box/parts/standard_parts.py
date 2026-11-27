# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


# ===== 分区：常量/配置 =====
CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"


# ===== 分区：模型/类型 =====
class PartKind(Enum):
    Unknown = 0
    PrintedShell = 1
    LatchBeam = 2
    ReleaseMembrane = 3
    HingeJoint = 4
    DcMotor = 5
    SpurGear = 6
    MetricScrew = 7


KIND_BY_TOKEN = {
    "printed_shell": PartKind.PrintedShell,
    "latch_beam": PartKind.LatchBeam,
    "release_membrane": PartKind.ReleaseMembrane,
    "hinge_joint": PartKind.HingeJoint,
    "dc_motor": PartKind.DcMotor,
    "spur_gear": PartKind.SpurGear,
    "metric_screw": PartKind.MetricScrew,
}


@dataclass(frozen=True)
class Material:
    name: str
    young_modulus_mpa: float
    yield_mpa: float
    density_kg_m3: float

    @classmethod
    def from_json(cls, name: str, payload: dict[str, Any]) -> Material:
        return cls(
            name=name,
            young_modulus_mpa=float(payload["young_modulus_mpa"]),
            yield_mpa=float(payload["yield_mpa"]),
            density_kg_m3=float(payload["density_kg_m3"]),
        )


@dataclass(frozen=True)
class CatalogPart:
    id: str
    kind: PartKind
    title: str
    material: str
    fields: dict[str, Any]

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> CatalogPart:
        token = str(payload.get("kind", ""))
        kind = KIND_BY_TOKEN.get(token, PartKind.Unknown)
        fields = {key: value for key, value in payload.items() if key not in {"id", "kind", "title", "material"}}
        return cls(
            id=str(payload["id"]),
            kind=kind,
            title=str(payload["title"]),
            material=str(payload["material"]),
            fields=fields,
        )

    def number(self, name: str) -> float:
        return float(self.fields[name])

    def numbers(self, name: str) -> list[float]:
        return [float(value) for value in self.fields[name]]


# ===== 分区：公开 API =====
class PartsCatalog:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.revision = str(payload["revision"])
        self.units = str(payload["units"])
        self.notes = str(payload.get("notes", ""))
        self.materials = {
            name: Material.from_json(name, spec)
            for name, spec in payload["materials"].items()
        }
        self.parts = [CatalogPart.from_json(item) for item in payload["parts"]]

    @classmethod
    def from_json_path(cls, path: Path | None = None) -> PartsCatalog:
        catalog_path = path or CATALOG_PATH
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("零件目录 JSON 必须是对象。")
        return cls(payload)

    def material(self, name: str) -> Material:
        try:
            return self.materials[name]
        except KeyError as exc:
            raise KeyError(f"未知材料: {name}") from exc

    def parts_of(self, kind: PartKind) -> list[CatalogPart]:
        return [part for part in self.parts if part.kind == kind]

    def require(self, part_id: str) -> CatalogPart:
        for part in self.parts:
            if part.id == part_id:
                return part
        raise KeyError(f"零件目录缺少: {part_id}")
