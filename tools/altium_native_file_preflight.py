from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "ALTIUM-NATIVE-FILE-PREFLIGHT-001"
CFB_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_cfb(
    path: str | Path,
    *,
    expected_suffix: str,
) -> dict:
    file_path = Path(path)
    errors: list[str] = []

    if file_path.suffix != expected_suffix:
        errors.append(
            f"extension:{file_path.suffix}!={expected_suffix}"
        )

    if not file_path.is_file():
        return {
            "path": file_path.as_posix(),
            "status": "FAIL",
            "errors": ["missing_file"],
        }

    size = file_path.stat().st_size
    if size < 512:
        errors.append("file_too_small")

    header = file_path.read_bytes()[:512]
    if len(header) < 34:
        errors.append("short_header")
        major_version = None
        sector_shift = None
        sector_size = None
    else:
        if header[:8] != CFB_MAGIC:
            errors.append("cfb_magic")

        major_version = int.from_bytes(
            header[26:28],
            "little",
        )
        byte_order = int.from_bytes(
            header[28:30],
            "little",
        )
        sector_shift = int.from_bytes(
            header[30:32],
            "little",
        )
        mini_sector_shift = int.from_bytes(
            header[32:34],
            "little",
        )

        if major_version not in {3, 4}:
            errors.append(f"cfb_major_version:{major_version}")
        if byte_order != 0xFFFE:
            errors.append(f"cfb_byte_order:{byte_order:#06x}")
        expected_shift = 9 if major_version == 3 else 12
        if major_version in {3, 4} and sector_shift != expected_shift:
            errors.append(
                f"cfb_sector_shift:{sector_shift}!={expected_shift}"
            )
        if mini_sector_shift != 6:
            errors.append(
                f"cfb_mini_sector_shift:{mini_sector_shift}!=6"
            )

        sector_size = (
            1 << sector_shift
            if 0 <= sector_shift <= 31
            else None
        )
        if (
            sector_size is not None
            and size >= sector_size
            and size % sector_size != 0
        ):
            errors.append(
                f"cfb_file_alignment:{size}%{sector_size}"
            )

    return {
        "path": file_path.as_posix(),
        "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "size": size,
        "sha256": sha256_file(file_path),
        "cfb_major_version": major_version,
        "sector_shift": sector_shift,
        "sector_size": sector_size,
    }


def validate(
    *,
    schematic: str | Path,
    pcb: str | Path,
) -> dict:
    schematic_result = inspect_cfb(
        schematic,
        expected_suffix=".SchDoc",
    )
    pcb_result = inspect_cfb(
        pcb,
        expected_suffix=".PcbDoc",
    )

    errors: list[str] = []
    for artifact_id, result in (
        ("schematic", schematic_result),
        ("pcb", pcb_result),
    ):
        for error in result.get("errors", []):
            errors.append(f"{artifact_id}:{error}")

    status = "PASS" if not errors else "FAIL"
    return {
        "schema": SCHEMA,
        "status": status,
        "errors": sorted(set(errors)),
        "artifacts": {
            "schematic": schematic_result,
            "pcb": pcb_result,
        },
        "layout_authority": "NOT_AUTHORIZED",
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "PASS proves that the native Altium documents are non-trivial "
                "Microsoft Compound File Binary containers with valid CFB header "
                "geometry; it does not prove electrical equivalence."
            ),
            (
                "Electrical/layout authority remains controlled by "
                "ALTIUM_EQUIVALENCE_GATE."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schematic", required=True)
    parser.add_argument("--pcb", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        schematic=args.schematic,
        pcb=args.pcb,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
