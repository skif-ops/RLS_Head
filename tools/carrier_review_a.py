from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCHEMA = "CARRIER-REVIEW-A-MANIFEST-001"
RESULT_SCHEMA = "CARRIER-REVIEW-A-RESULT-001"

REQUIRED_ARTIFACTS = {
    "schematic",
    "erc_json",
    "pinmap",
    "bom",
}

REQUIRED_AUDITS = {
    "power",
    "clock",
    "reset_boot",
    "timing_capture",
    "imu",
    "ethernet",
    "can_fd",
}

EXPECTED_TIMING = {
    "GNSS_PPS": ("PA0", "TIM2_CH1"),
    "RADAR_REF": ("PB10", "TIM2_CH3"),
    "IMU_DRDY": ("PB11", "TIM2_CH4"),
}

REQUIRED_MPNS = {
    "STM32H753IIT6",
    "ICM-42688-P",
    "LAN8742Ai-CZ-TR",
    "TCAN3404DRBRQ1",
    "TPS62130ARGTR",
    "TPS259470ARPWR",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_repo_path(root: Path, relative: str) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe artifact path: {relative}")

    root_resolved = root.resolve()
    path = (root / rel).resolve()

    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"artifact escapes repository root: {relative}") from exc

    return path


def parse_erc_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    sheets = data.get("sheets")
    if not isinstance(sheets, list):
        raise ValueError("KiCad ERC JSON must contain sheets[]")

    violations: list[dict] = []

    for sheet in sheets:
        if not isinstance(sheet, dict):
            raise ValueError("invalid ERC sheet entry")

        sheet_path = str(sheet.get("path", ""))
        entries = sheet.get("violations", [])

        if not isinstance(entries, list):
            raise ValueError("ERC sheet violations must be a list")

        for violation in entries:
            if not isinstance(violation, dict):
                raise ValueError("invalid ERC violation entry")

            severity = str(violation.get("severity", "")).lower()

            if severity not in {"error", "warning"}:
                raise ValueError(
                    f"unsupported ERC severity {severity!r}"
                )

            violations.append(
                {
                    "sheet": sheet_path,
                    "severity": severity,
                    "type": str(violation.get("type", "")),
                    "description": str(
                        violation.get("description", "")
                    ),
                }
            )

    errors = sum(
        1 for item in violations
        if item["severity"] == "error"
    )

    warnings = sum(
        1 for item in violations
        if item["severity"] == "warning"
    )

    return {
        "kicad_version": str(data.get("kicad_version", "")),
        "source": str(data.get("source", "")),
        "errors": errors,
        "warnings": warnings,
        "violations": violations,
    }


def validate_pinmap(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        required_columns = {
            "signal",
            "mcu_pin",
            "peripheral",
            "direction",
            "criticality",
        }

        if (
            reader.fieldnames is None
            or not required_columns.issubset(reader.fieldnames)
        ):
            raise ValueError(
                "pinmap missing required columns"
            )

        rows = {
            str(row["signal"]).strip(): row
            for row in reader
            if str(row.get("signal", "")).strip()
        }

    findings: list[str] = []

    for signal, (expected_pin, expected_peripheral) in (
        EXPECTED_TIMING.items()
    ):
        row = rows.get(signal)

        if row is None:
            findings.append(f"missing:{signal}")
            continue

        pin = str(row["mcu_pin"]).strip()
        peripheral = str(row["peripheral"]).strip()
        criticality = str(row["criticality"]).strip()

        if pin != expected_pin:
            findings.append(
                f"{signal}:pin:{pin}!={expected_pin}"
            )

        if peripheral != expected_peripheral:
            findings.append(
                f"{signal}:peripheral:"
                f"{peripheral}!={expected_peripheral}"
            )

        if criticality != "P0":
            findings.append(
                f"{signal}:criticality:{criticality}!=P0"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "timing_signal_count": len(EXPECTED_TIMING),
    }


def validate_bom(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        required_columns = {
            "ref",
            "qty",
            "manufacturer",
            "mpn",
            "description",
        }

        if (
            reader.fieldnames is None
            or not required_columns.issubset(reader.fieldnames)
        ):
            raise ValueError("BOM missing required columns")

        mpns = {
            str(row.get("mpn", "")).strip()
            for row in reader
            if str(row.get("mpn", "")).strip()
        }

    missing = sorted(REQUIRED_MPNS - mpns)

    return {
        "status": "PASS" if not missing else "FAIL",
        "missing_required_mpns": missing,
        "required_mpn_count": len(REQUIRED_MPNS),
    }


def validate_manifest(
    manifest_path: str | Path,
    repository_root: str | Path = ".",
) -> dict:
    manifest_path = Path(manifest_path)
    root = Path(repository_root)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    errors: list[str] = []
    reasons: list[str] = []

    if manifest.get("schema") != SCHEMA:
        errors.append("schema")

    if manifest.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")

    if manifest.get("hardware_revision") != "A":
        errors.append("hardware_revision")

    if manifest.get("cad_tool") != "KiCad":
        errors.append("cad_tool")

    artifacts_raw = manifest.get("artifacts")

    if not isinstance(artifacts_raw, list):
        raise ValueError("artifacts must be a list")

    artifacts = {}

    for item in artifacts_raw:
        if not isinstance(item, dict):
            errors.append("artifact_entry")
            continue

        artifact_id = str(item.get("id", "")).strip()

        if not artifact_id:
            errors.append("artifact_without_id")
            continue

        if artifact_id in artifacts:
            errors.append(
                f"duplicate_artifact:{artifact_id}"
            )
            continue

        artifacts[artifact_id] = item

    missing_artifacts = sorted(
        REQUIRED_ARTIFACTS - set(artifacts)
    )

    if missing_artifacts:
        errors.extend(
            f"missing_artifact:{item}"
            for item in missing_artifacts
        )

    integrity = {}
    resolved = {}

    for artifact_id in REQUIRED_ARTIFACTS:
        item = artifacts.get(artifact_id)

        if item is None:
            continue

        relative = str(item.get("path", ""))
        expected_hash = str(item.get("sha256", "")).lower()

        try:
            path = safe_repo_path(root, relative)
        except ValueError as exc:
            errors.append(
                f"artifact_path:{artifact_id}:{exc}"
            )
            continue

        if not path.is_file():
            errors.append(
                f"artifact_missing:{artifact_id}"
            )
            continue

        actual_hash = sha256_file(path)
        hash_ok = (
            len(expected_hash) == 64
            and actual_hash == expected_hash
        )

        integrity[artifact_id] = {
            "path": relative,
            "sha256_expected": expected_hash,
            "sha256_actual": actual_hash,
            "hash_ok": hash_ok,
        }

        resolved[artifact_id] = path

        if not hash_ok:
            errors.append(
                f"hash_mismatch:{artifact_id}"
            )

    erc = None
    pinmap = None
    bom = None

    if "erc_json" in resolved:
        try:
            erc = parse_erc_json(
                resolved["erc_json"]
            )
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"erc_parse:{exc}")

    if "pinmap" in resolved:
        try:
            pinmap = validate_pinmap(
                resolved["pinmap"]
            )
        except ValueError as exc:
            errors.append(f"pinmap_parse:{exc}")

    if "bom" in resolved:
        try:
            bom = validate_bom(
                resolved["bom"]
            )
        except ValueError as exc:
            errors.append(f"bom_parse:{exc}")

    schematic_item = artifacts.get("schematic")
    if schematic_item is not None:
        if not str(
            schematic_item.get("path", "")
        ).endswith(".kicad_sch"):
            errors.append("schematic_extension")

    erc_policy = manifest.get("erc_policy", {})

    if not isinstance(erc_policy, dict):
        errors.append("erc_policy")
        erc_policy = {}

    errors_allowed = int(
        erc_policy.get("errors_allowed", 0)
    )

    warnings_allowed = int(
        erc_policy.get("warnings_allowed", 0)
    )

    if erc is not None:
        if erc["errors"] > errors_allowed:
            reasons.append("ERC_ERRORS")

        if erc["warnings"] > warnings_allowed:
            reasons.append("ERC_WARNINGS")

    if pinmap is not None and pinmap["status"] != "PASS":
        reasons.append("TIMING_PINMAP")

    if bom is not None and bom["status"] != "PASS":
        reasons.append("BOM")

    audits = manifest.get("audits")

    audit_status = {}

    if not isinstance(audits, dict):
        errors.append("audits")
    else:
        for audit in sorted(REQUIRED_AUDITS):
            value = str(audits.get(audit, "MISSING"))
            audit_status[audit] = value

            if value != "PASS":
                reasons.append(
                    f"AUDIT_{audit.upper()}"
                )

    synthetic = bool(
        manifest.get("synthetic_fixture", False)
    )

    evidence_level = str(
        manifest.get("evidence_level", "")
    )

    if errors:
        status = "INVALID"
    elif reasons:
        status = "FAIL"
    elif synthetic:
        status = "TEST_READY"
    elif evidence_level != "CAD_REVIEW":
        status = "HOLD"
        reasons.append("EVIDENCE_LEVEL")
    else:
        status = "PASS"

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "board_id": manifest.get("board_id"),
        "hardware_revision": manifest.get(
            "hardware_revision"
        ),
        "cad_tool": manifest.get("cad_tool"),
        "cad_version": manifest.get("cad_version"),
        "synthetic_fixture": synthetic,
        "evidence_level": evidence_level,
        "errors": errors,
        "reason_codes": sorted(set(reasons)),
        "integrity": integrity,
        "erc": erc,
        "pinmap": pinmap,
        "bom": bom,
        "audits": audit_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate EVT System Carrier Review A evidence"
        )
    )

    parser.add_argument("manifest")
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate_manifest(
        args.manifest,
        args.repository_root,
    )

    Path(args.output).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(result["status"])

    return (
        0
        if result["status"]
        in {"PASS", "TEST_READY", "HOLD"}
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
