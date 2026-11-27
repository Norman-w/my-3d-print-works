#!/usr/bin/env python3
"""Add Bambu Studio object metadata without touching the source 3MF."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def build_model_settings(model_name: str, source_name: str, extruder: int) -> bytes:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="1">
    <metadata key="name" value="{model_name}"/>
    <metadata key="extruder" value="{extruder}"/>
    <part id="1" subtype="normal_part" uuid="00000000-0000-0000-0000-000000000001">
      <metadata key="name" value="{model_name}"/>
      <metadata key="source_file" value="{source_name}"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="M7-LB1 主拍面正面 · PA6-CF A3"/>
    <metadata key="locked" value="false"/>
    <model_instance>
      <metadata key="object_id" value="1"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="1"/>
    </model_instance>
  </plate>
  <assemble>
  </assemble>
</config>
'''.encode("utf-8")


def build_project_settings(printer_settings_id: str) -> bytes:
    """Pin the project to the local X1C hardened-steel 0.4 mm preset."""
    settings = {
        "printer_settings_id": printer_settings_id,
        "printer_model": "Bambu Lab X1 Carbon",
        "printer_variant": "0.4",
        "printer_technology": "FFF",
        "printer_structure": "corexy",
        "nozzle_type": ["hardened_steel"],
        "nozzle_diameter": ["0.4"],
        "nozzle_volume": ["107"],
        "nozzle_volume_type": ["Standard"],
        "printer_extruder_id": ["1"],
        "printer_extruder_variant": ["Direct Drive Standard"],
        "required_nozzle_HRC": ["3"],
        "print_compatible_printers": [
            printer_settings_id,
            "Bambu Lab X1 0.4 nozzle",
            "Bambu Lab P1S 0.4 nozzle",
            "Bambu Lab X1E 0.4 nozzle",
        ],
    }
    return json.dumps(settings, ensure_ascii=False, indent=4).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--extruder", type=int, default=3)
    parser.add_argument(
        "--printer-settings-id",
        default="Bambu Lab X1 Carbon 0.4 nozzle",
        help="Bambu Studio printer preset ID to embed in the project.",
    )
    args = parser.parse_args()

    source_name = args.source.stem + ".stl"
    model_name = args.source.stem
    with zipfile.ZipFile(args.source, "r") as source_zip, zipfile.ZipFile(
        args.destination, "w", compression=zipfile.ZIP_DEFLATED
    ) as destination_zip:
        for info in source_zip.infolist():
            if info.filename in {
                "Metadata/model_settings.config",
                "Metadata/project_settings.config",
            }:
                continue
            destination_zip.writestr(info, source_zip.read(info.filename))
        destination_zip.writestr(
            "Metadata/model_settings.config",
            build_model_settings(model_name, source_name, args.extruder),
        )
        destination_zip.writestr(
            "Metadata/project_settings.config",
            build_project_settings(args.printer_settings_id),
        )


if __name__ == "__main__":
    main()
