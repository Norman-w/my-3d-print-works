"""Explicit version selection shared by smooth-shell build/audit/render tools."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SmoothRelease:
    revision: int
    body_height: int
    previous_package: str
    previous_stem: str

    @property
    def stem(self):
        return f"fan76-smooth-v{self.revision}"

    @property
    def source(self):
        return self.stem + ".scad"

    @property
    def out(self):
        return ROOT / "output" / f"{self.stem}-20261008"

    @property
    def sources(self):
        return [self.source, "fan-tee-v5-parameters.scad", "fan-tee-v5-thread.scad", "fan-tee-narrow-v5.scad"]


def smooth_release(revision):
    return {
        2: SmoothRelease(2, 184, "fan76-direct-longtravel-v1-20261007", "fan76-direct-v1"),
        3: SmoothRelease(3, 234, "fan76-smooth-v2-20261008", "fan76-smooth-v2"),
        4: SmoothRelease(4, 244, "fan76-smooth-v3-20261008", "fan76-smooth-v3"),
        5: SmoothRelease(5, 248, "fan76-smooth-v4-20261008", "fan76-smooth-v4"),
    }[revision]
