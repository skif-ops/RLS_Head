from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


SCHEMA = "ALTIUM-IMPORT-PACKAGE-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, target: Path) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": target.as_posix(),
        "sha256": sha256_file(target),
        "size": target.stat().st_size,
    }


def build(
    *,
    generated_dir: str | Path,
    system_root: str | Path,
    output_dir: str | Path,
    source_commit: str,
) -> dict:
    generated = Path(generated_dir)
    system = Path(system_root)
    output = Path(output_dir)

    profile_path = (
        system
        / "altium"
        / "ALTIUM_IMPORT_PROFILE_SYS_001.json"
    )
    authority_path = (
        system
        / "CAD_AUTHORITY_SYS_001.json"
    )

    profile = json.loads(
        profile_path.read_text(encoding="utf-8")
    )
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )

    source = profile["source"]
    required_generated = [
        source["project"],
        source["root_schematic"],
        *source["child_sheets"],
        source["symbol_library"],
    ]

    missing = [
        name
        for name in required_generated
        if not (generated / name).is_file()
    ]
    footprint_dir = (
        generated
        / source["footprint_library"]
    )
    if not footprint_dir.is_dir():
        missing.append(source["footprint_library"])

    if missing:
        raise FileNotFoundError(
            "missing generated Altium import inputs: "
            + ", ".join(sorted(missing))
        )

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    records: list[dict] = []

    for name in required_generated:
        records.append(
            copy_file(
                generated / name,
                output / "kicad_source" / name,
            )
        )

    for path in sorted(
        footprint_dir.rglob("*")
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(generated)
        records.append(
            copy_file(
                path,
                output / "kicad_source" / rel,
            )
        )

    contract_names = [
        "BOM_SYS_CARRIER_003.csv",
        "BOM_SYS_CARRIER_LAYOUT_004.csv",
        "FOOTPRINT_ASSIGNMENT_SYS_002.csv",
        "PINMAP_SYS_001.csv",
        "CONNECTOR_PINOUT_SYS_001.csv",
        "NETLIST_SYS_001.csv",
        "HIERARCHY_INTERFACE_SYS_001.csv",
        "FOOTPRINT_PLAN_SYS_001.csv",
        "PCB_LAYOUT_CONSTRAINTS_SYS_001.csv",
        "CAD_AUTHORITY_SYS_001.json",
    ]

    for name in contract_names:
        records.append(
            copy_file(
                system / name,
                output / "contracts" / name,
            )
        )

    for name in [
        "EVT_SYS_CARRIER.PrjPcb",
        "ALTIUM_IMPORT_PROFILE_SYS_001.json",
        "ALTIUM_LAYER_STACK_SYS_001.csv",
        "ALTIUM_RULES_SYS_001.csv",
        "ALTIUM_NET_CLASSES_SYS_001.csv",
        "ALTIUM_PLACEMENT_PLAN_SYS_001.csv",
        "ALTIUM_BOARD_MECHANICAL_SYS_001.csv",
        "ALTIUM_PLACEMENT_COORD_SYS_002.csv",
        "ALTIUM_ROUTING_SEQUENCE_SYS_001.csv",
        "ALTIUM_PRELAYOUT_RULE_VALUES_SYS_001.csv",
        "ALTIUM_EQUIVALENCE_CHECKS_SYS_001.csv",
        "ALTIUM_NATIVE_STATUS_SYS_001.json",
        "README.md",
    ]:
        records.append(
            copy_file(
                system / "altium" / name,
                output / "altium_target" / name,
            )
        )

    prelayout_result = (
        generated
        / "prelayout_validation.json"
    )
    if prelayout_result.is_file():
        records.append(
            copy_file(
                prelayout_result,
                output
                / "evidence"
                / "prelayout_validation.json",
            )
        )

    records = sorted(
        records,
        key=lambda item: item["path"],
    )

    manifest = {
        "schema": SCHEMA,
        "status": "READY_FOR_ALTIUM_IMPORT",
        "board_id": authority["board_id"],
        "hardware_revision": authority[
            "hardware_revision"
        ],
        "source_commit": source_commit,
        "source_cad": authority[
            "verification_cad"
        ],
        "target_cad": authority[
            "primary_cad"
        ],
        "preserve_kicad": authority[
            "preserve_kicad"
        ],
        "file_count": len(records),
        "files": records,
        "post_import_checks": profile[
            "post_import_checks"
        ],
        "notes": [
            (
                "Import kicad_source through Altium Designer "
                "KiCad Importer / Import Wizard."
            ),
            (
                "Do not delete the retained KiCad source after "
                "native Altium conversion."
            ),
            (
                "Native SchDoc/PcbDoc become PCB implementation "
                "authority only after the equivalence gate."
            ),
        ],
    }

    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    result = build(
        generated_dir=args.generated_dir,
        system_root=args.system_root,
        output_dir=args.output_dir,
        source_commit=args.source_commit,
    )
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
