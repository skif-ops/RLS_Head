from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.altium_compile_evidence import validate as validate_compile_evidence
from tools.altium_native_file_preflight import validate as validate_native_files
from tools.altium_script_runtime_receipt import (
    validate as validate_script_runtime_receipt,
)


MANIFEST_SCHEMA = "ALTIUM-EQUIVALENCE-MANIFEST-001"
RESULT_SCHEMA = "ALTIUM-EQUIVALENCE-RESULT-001"

REQUIRED_ARTIFACTS = {
    "project",
    "schematic",
    "pcb",
    "native_file_preflight",
    "import_native_file_preflight",
    "import_package_manifest",
    "import_receipt",
    "import_log",
    "compile_report_raw",
    "compile_report",
    "bom_export",
    "bom_validation_result",
    "connector_validation_result",
    "kicad_netlist_baseline",
    "netlist_validation_result",
    "netlist_export",
    "footprint_report",
    "component_inventory",
    "net_inventory",
    "rule_inventory",
    "pad_net_inventory",
    "layer_stack_inventory",
    "hierarchy_export",
    "hierarchy_validation_result",
    "script_runtime_receipt",
    "script_runtime_result",
    "no_mmwave_review",
    "no_mmwave_review_result",
    "native_audit_result",
}

REQUIRED_CHECKS = {
    "bom_designator_mpn_equivalence",
    "pinmap_equivalence",
    "connector_pinout_equivalence",
    "netlist_equivalence",
    "footprint_equivalence",
    "hierarchy_equivalence",
    "rules_equivalence",
    "stackup_equivalence",
    "no_76_81GHz_rf_on_system_carrier",
    "native_pcb_audit",
}

EXPECTED_EXTENSIONS = {
    "project": ".PrjPcb",
    "schematic": ".SchDoc",
    "pcb": ".PcbDoc",
}

CANONICAL_ARTIFACT_PATHS = {
    "project": "hardware/system_carrier/altium/EVT_SYS_CARRIER.PrjPcb",
    "schematic": (
        "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc"
    ),
    "pcb": "hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc",
    "script_runtime_receipt": (
        "hardware/system_carrier/altium/equivalence/"
        "script_runtime_receipt.json"
    ),
    "script_runtime_result": (
        "hardware/system_carrier/altium/equivalence/"
        "script_runtime_result.json"
    ),
}

IMPORT_SNAPSHOT_PATHS = {
    "schematic": CANONICAL_ARTIFACT_PATHS["schematic"],
    "pcb": CANONICAL_ARTIFACT_PATHS["pcb"],
    "import_log": (
        "hardware/system_carrier/altium/equivalence/import_log.txt"
    ),
}


def valid_sha256(value: object) -> bool:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return False
    try:
        int(text, 16)
    except ValueError:
        return False
    return True


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
        raise ValueError(
            f"artifact escapes repository root: {relative}"
        ) from exc
    return path


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

    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("schema")
    if manifest.get("board_id") != "EVT-SYS-CARRIER":
        errors.append("board_id")
    if manifest.get("hardware_revision") != "A":
        errors.append("hardware_revision")
    if manifest.get("primary_cad") != "Altium Designer":
        errors.append("primary_cad")

    artifacts_raw = manifest.get("artifacts")
    if not isinstance(artifacts_raw, list):
        raise ValueError("artifacts must be a list")

    artifacts: dict[str, dict] = {}
    for item in artifacts_raw:
        if not isinstance(item, dict):
            errors.append("artifact_entry")
            continue
        artifact_id = str(item.get("id", "")).strip()
        if not artifact_id:
            errors.append("artifact_without_id")
            continue
        if artifact_id in artifacts:
            errors.append(f"duplicate_artifact:{artifact_id}")
            continue
        artifacts[artifact_id] = item

    for missing in sorted(REQUIRED_ARTIFACTS - set(artifacts)):
        errors.append(f"missing_artifact:{missing}")

    integrity: dict[str, dict] = {}
    resolved: dict[str, Path] = {}

    for artifact_id in REQUIRED_ARTIFACTS:
        item = artifacts.get(artifact_id)
        if item is None:
            continue

        relative = str(item.get("path", "")).strip()

        canonical = CANONICAL_ARTIFACT_PATHS.get(artifact_id)
        if canonical is not None and relative != canonical:
            errors.append(
                f"canonical_path:{artifact_id}"
            )
            continue

        expected_hash = str(
            item.get("sha256", "")
        ).strip().lower()

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

    for artifact_id, extension in EXPECTED_EXTENSIONS.items():
        item = artifacts.get(artifact_id)
        if item is None:
            continue
        if not str(item.get("path", "")).endswith(extension):
            errors.append(
                f"extension:{artifact_id}:{extension}"
            )

    import_package = None
    package_path = resolved.get("import_package_manifest")
    if package_path is not None:
        try:
            import_package = json.loads(
                package_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_package_parse:{exc}")
        else:
            if (
                import_package.get("schema")
                != "ALTIUM-IMPORT-PACKAGE-001"
            ):
                errors.append("import_package_schema")
            if import_package.get("status") != "READY_FOR_ALTIUM_IMPORT":
                errors.append("import_package_status")

    import_native_preflight = None
    import_preflight_path = resolved.get("import_native_file_preflight")
    if import_preflight_path is not None:
        try:
            import_native_preflight = json.loads(
                import_preflight_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_native_preflight_parse:{exc}")
        else:
            if (
                import_native_preflight.get("schema")
                != "ALTIUM-NATIVE-FILE-PREFLIGHT-001"
            ):
                errors.append("import_native_preflight_schema")
            if import_native_preflight.get("status") != "PASS":
                reasons.append("IMPORT_NATIVE_PREFLIGHT")

            import_artifacts = import_native_preflight.get("artifacts")
            if not isinstance(import_artifacts, dict):
                errors.append("import_native_preflight_artifacts")
            else:
                for artifact_id in ("schematic", "pcb"):
                    record = import_artifacts.get(artifact_id)
                    if not isinstance(record, dict):
                        errors.append(
                            f"import_native_preflight_record:{artifact_id}"
                        )
                        continue
                    expected_path = CANONICAL_ARTIFACT_PATHS[
                        artifact_id
                    ]
                    if (
                        str(record.get("path", "")).strip()
                        != expected_path
                    ):
                        errors.append(
                            f"import_native_preflight_path:{artifact_id}"
                        )
                    if not valid_sha256(record.get("sha256")):
                        errors.append(
                            f"import_native_preflight_hash:{artifact_id}"
                        )

    import_receipt = None
    receipt_path = resolved.get("import_receipt")
    if receipt_path is not None:
        try:
            import_receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"import_receipt_parse:{exc}")
        else:
            if (
                import_receipt.get("schema")
                != "ALTIUM-NATIVE-IMPORT-RECEIPT-001"
            ):
                errors.append("import_receipt_schema")
            if import_receipt.get("status") != "PASS":
                reasons.append("IMPORT_RECEIPT")
            if (
                import_receipt.get("snapshot_role")
                != "POST_IMPORT_NATIVE_SNAPSHOT"
            ):
                errors.append("import_receipt_snapshot_role")
            if not str(import_receipt.get("altium_version", "")).strip():
                errors.append("import_receipt_altium_version")
            if not str(import_receipt.get("importer_version", "")).strip():
                errors.append("import_receipt_importer_version")

            preflight_record = import_receipt.get(
                "import_native_file_preflight"
            )
            if not isinstance(preflight_record, dict):
                errors.append("import_receipt_preflight_record")
            else:
                claimed = str(
                    preflight_record.get("sha256", "")
                ).lower()
                actual = str(
                    integrity.get(
                        "import_native_file_preflight", {}
                    ).get("sha256_actual", "")
                ).lower()
                if not actual or claimed != actual:
                    errors.append(
                        "import_receipt_hash:import_native_file_preflight"
                    )

            package_record = import_receipt.get(
                "import_package_manifest"
            )
            if not isinstance(package_record, dict):
                errors.append("import_receipt_package_record")
            else:
                claimed = str(
                    package_record.get("sha256", "")
                ).lower()
                actual = str(
                    integrity.get(
                        "import_package_manifest", {}
                    ).get("sha256_actual", "")
                ).lower()
                if not actual or claimed != actual:
                    errors.append(
                        "import_receipt_hash:import_package_manifest"
                    )

            native_records = import_receipt.get("native_artifacts")
            if not isinstance(native_records, dict):
                errors.append("import_receipt_native_artifacts")
            else:
                for artifact_id in (
                    "schematic",
                    "pcb",
                    "import_log",
                ):
                    record = native_records.get(artifact_id)
                    if not isinstance(record, dict):
                        errors.append(
                            f"import_receipt_snapshot_record:{artifact_id}"
                        )
                        continue

                    expected_snapshot_path = IMPORT_SNAPSHOT_PATHS[
                        artifact_id
                    ]
                    if (
                        str(record.get("path", "")).strip()
                        != expected_snapshot_path
                    ):
                        errors.append(
                            f"import_receipt_snapshot_path:{artifact_id}"
                        )

                    claimed = str(
                        record.get("sha256", "")
                    ).strip().lower()
                    if not valid_sha256(claimed):
                        errors.append(
                            f"import_receipt_snapshot_hash:{artifact_id}"
                        )

                    # Import-time SchDoc/PcbDoc hashes are provenance of the
                    # immediate Import Wizard output. They are intentionally
                    # allowed to differ from the later prepared pre-routing
                    # snapshot, which is bound by native_file_preflight and
                    # the equivalence manifest. The import log itself must
                    # remain immutable and is therefore checked exactly.
                    if artifact_id == "import_log":
                        actual = str(
                            integrity.get("import_log", {}).get(
                                "sha256_actual",
                                "",
                            )
                        ).lower()
                        if not actual or claimed != actual:
                            errors.append("import_receipt_hash:import_log")

                if isinstance(import_native_preflight, dict):
                    preflight_artifacts = import_native_preflight.get(
                        "artifacts"
                    )
                    if isinstance(preflight_artifacts, dict):
                        for artifact_id in ("schematic", "pcb"):
                            receipt_record = native_records.get(
                                artifact_id
                            )
                            preflight_record = preflight_artifacts.get(
                                artifact_id
                            )
                            receipt_hash = (
                                str(
                                    receipt_record.get("sha256", "")
                                ).lower()
                                if isinstance(receipt_record, dict)
                                else ""
                            )
                            preflight_hash = (
                                str(
                                    preflight_record.get("sha256", "")
                                ).lower()
                                if isinstance(preflight_record, dict)
                                else ""
                            )
                            if (
                                not receipt_hash
                                or receipt_hash != preflight_hash
                            ):
                                errors.append(
                                    "import_snapshot_chain_hash:"
                                    + artifact_id
                                )

            if import_package is not None:
                receipt_source = str(
                    import_receipt.get("source_commit", "")
                ).strip().lower()
                package_source = str(
                    import_package.get("source_commit", "")
                ).strip().lower()
                if not receipt_source or receipt_source != package_source:
                    errors.append("import_receipt_source_commit")

    native_file_preflight = None
    preflight_path = resolved.get("native_file_preflight")
    if preflight_path is not None:
        try:
            native_file_preflight = json.loads(
                preflight_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"native_file_preflight_parse:{exc}")
        else:
            if (
                native_file_preflight.get("schema")
                != "ALTIUM-NATIVE-FILE-PREFLIGHT-001"
            ):
                errors.append("native_file_preflight_schema")
            if native_file_preflight.get("status") != "PASS":
                reasons.append("NATIVE_FILE_PREFLIGHT")

            artifacts_result = native_file_preflight.get("artifacts")
            if not isinstance(artifacts_result, dict):
                errors.append("native_file_preflight_artifacts")
            else:
                for artifact_id in ("schematic", "pcb"):
                    record = artifacts_result.get(artifact_id)
                    claimed = (
                        str(record.get("sha256", "")).lower()
                        if isinstance(record, dict)
                        else ""
                    )
                    actual = str(
                        integrity.get(artifact_id, {}).get(
                            "sha256_actual",
                            "",
                        )
                    ).lower()
                    if not actual or claimed != actual:
                        errors.append(
                            f"native_file_preflight_hash:{artifact_id}"
                        )

    native_file_preflight_rerun = None
    schematic_path = resolved.get("schematic")
    pcb_path = resolved.get("pcb")
    if schematic_path is not None and pcb_path is not None:
        native_file_preflight_rerun = validate_native_files(
            schematic=schematic_path,
            pcb=pcb_path,
        )
        if native_file_preflight_rerun.get("status") != "PASS":
            for item in native_file_preflight_rerun.get("errors", []):
                errors.append(f"native_file_rerun:{item}")

    compile_result = None
    compile_validation = None
    compile_path = resolved.get("compile_report")
    if compile_path is not None:
        compile_validation = validate_compile_evidence(
            compile_report=compile_path,
            repository_root=root,
        )
        compile_result = compile_validation.get("compile")
        validation_status = compile_validation.get("status")
        if validation_status == "INVALID":
            for item in compile_validation.get("errors", []):
                errors.append(f"compile_evidence:{item}")
        elif validation_status != "PASS":
            for item in compile_validation.get("reason_codes", []):
                reasons.append(item)

        if isinstance(compile_result, dict):
            for artifact_id, path_key in (
                ("compile_report_raw", "source_report"),
                ("project", "source_project"),
                ("schematic", "source_schematic"),
            ):
                expected_path = str(
                    integrity.get(artifact_id, {}).get(
                        "path",
                        "",
                    )
                )
                if (
                    str(compile_result.get(path_key, "")).strip()
                    != expected_path
                ):
                    errors.append(
                        f"compile_evidence:{path_key}_manifest_path"
                    )


    bom_validation = None
    bom_validation_path = resolved.get("bom_validation_result")
    if bom_validation_path is not None:
        try:
            bom_validation = json.loads(
                bom_validation_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"bom_validation_parse:{exc}")
        else:
            if (
                bom_validation.get("schema")
                != "ALTIUM-NATIVE-BOM-RESULT-001"
            ):
                errors.append("bom_validation_schema")
            if bom_validation.get("status") != "PASS":
                reasons.append("BOM_VALIDATION")
            hashes = bom_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("bom_validation_input_sha256")
            else:
                actual_export = str(
                    integrity.get("bom_export", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if str(hashes.get("bom_export", "")).lower() != actual_export:
                    errors.append("bom_validation_hash:bom_export")
                contract_path = (
                    root
                    / "hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv"
                )
                if not contract_path.is_file():
                    errors.append("bom_contract_missing")
                elif (
                    str(hashes.get("bom_contract", "")).lower()
                    != sha256_file(contract_path)
                ):
                    errors.append("bom_validation_hash:bom_contract")

    connector_validation = None
    connector_validation_path = resolved.get(
        "connector_validation_result"
    )
    if connector_validation_path is not None:
        try:
            connector_validation = json.loads(
                connector_validation_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"connector_validation_parse:{exc}")
        else:
            if (
                connector_validation.get("schema")
                != "ALTIUM-NATIVE-CONNECTOR-RESULT-001"
            ):
                errors.append("connector_validation_schema")
            if connector_validation.get("status") != "PASS":
                reasons.append("CONNECTOR_VALIDATION")
            hashes = connector_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("connector_validation_input_sha256")
            else:
                actual_inventory = str(
                    integrity.get("pad_net_inventory", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if (
                    str(hashes.get("pad_net_inventory", "")).lower()
                    != actual_inventory
                ):
                    errors.append(
                        "connector_validation_hash:pad_net_inventory"
                    )

                for key, relative in (
                    (
                        "connector_pinout_contract",
                        "hardware/system_carrier/CONNECTOR_PINOUT_SYS_001.csv",
                    ),
                    (
                        "connector_native_map",
                        "hardware/system_carrier/CONNECTOR_NATIVE_PINMAP_SYS_001.csv",
                    ),
                ):
                    contract_path = root / relative
                    if not contract_path.is_file():
                        errors.append(f"{key}_missing")
                    elif (
                        str(hashes.get(key, "")).lower()
                        != sha256_file(contract_path)
                    ):
                        errors.append(
                            f"connector_validation_hash:{key}"
                        )

    netlist_validation = None
    netlist_validation_path = resolved.get("netlist_validation_result")
    if netlist_validation_path is not None:
        try:
            netlist_validation = json.loads(
                netlist_validation_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"netlist_validation_parse:{exc}")
        else:
            if (
                netlist_validation.get("schema")
                != "ALTIUM-NATIVE-NETLIST-RESULT-001"
            ):
                errors.append("netlist_validation_schema")
            if netlist_validation.get("status") != "PASS":
                reasons.append("NETLIST_VALIDATION")
            hashes = netlist_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("netlist_validation_input_sha256")
            else:
                actual_baseline = str(
                    integrity.get("kicad_netlist_baseline", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                actual_inventory = str(
                    integrity.get("pad_net_inventory", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if (
                    str(hashes.get("kicad_netlist_baseline", "")).lower()
                    != actual_baseline
                ):
                    errors.append(
                        "netlist_validation_hash:kicad_netlist_baseline"
                    )
                if (
                    str(hashes.get("pad_net_inventory", "")).lower()
                    != actual_inventory
                ):
                    errors.append(
                        "netlist_validation_hash:pad_net_inventory"
                    )

                package_files = (
                    import_package.get("files", [])
                    if isinstance(import_package, dict)
                    else []
                )
                package_hashes = {
                    str(item.get("sha256", "")).lower()
                    for item in package_files
                    if isinstance(item, dict)
                    and str(item.get("path", "")).replace("\\", "/").endswith(
                        "/evidence/kicad_netlist_baseline.csv"
                    )
                }
                if (
                    not actual_baseline
                    or actual_baseline not in package_hashes
                ):
                    errors.append(
                        "netlist_baseline_not_bound_to_import_package"
                    )

    footprint_validation = None
    footprint_path = resolved.get("footprint_report")
    if footprint_path is not None:
        try:
            footprint_validation = json.loads(
                footprint_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"footprint_report_parse:{exc}")
        else:
            if (
                footprint_validation.get("schema")
                != "ALTIUM-NATIVE-FOOTPRINT-RESULT-001"
            ):
                errors.append("footprint_report_schema")
            if footprint_validation.get("status") != "PASS":
                reasons.append("FOOTPRINT_VALIDATION")
            hashes = footprint_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("footprint_report_input_sha256")
            else:
                actual_inventory = str(
                    integrity.get("component_inventory", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if (
                    str(hashes.get("component_inventory", "")).lower()
                    != actual_inventory
                ):
                    errors.append(
                        "footprint_report_hash:component_inventory"
                    )
                contract_path = (
                    root
                    / "hardware/system_carrier/FOOTPRINT_ASSIGNMENT_SYS_002.csv"
                )
                if not contract_path.is_file():
                    errors.append("footprint_contract_missing")
                elif (
                    str(hashes.get("footprint_contract", "")).lower()
                    != sha256_file(contract_path)
                ):
                    errors.append(
                        "footprint_report_hash:footprint_contract"
                    )

    hierarchy_validation = None
    hierarchy_path = resolved.get("hierarchy_validation_result")
    if hierarchy_path is not None:
        try:
            hierarchy_validation = json.loads(
                hierarchy_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"hierarchy_validation_parse:{exc}")
        else:
            if (
                hierarchy_validation.get("schema")
                != "ALTIUM-NATIVE-HIERARCHY-RESULT-001"
            ):
                errors.append("hierarchy_validation_schema")
            if hierarchy_validation.get("status") != "PASS":
                reasons.append("HIERARCHY_VALIDATION")
            hashes = hierarchy_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("hierarchy_validation_input_sha256")
            else:
                actual_export = str(
                    integrity.get("hierarchy_export", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if (
                    str(hashes.get("hierarchy_export", "")).lower()
                    != actual_export
                ):
                    errors.append(
                        "hierarchy_validation_hash:hierarchy_export"
                    )
                actual_pad_inventory = str(
                    integrity.get("pad_net_inventory", {}).get(
                        "sha256_actual", ""
                    )
                ).lower()
                if (
                    str(hashes.get("pad_net_inventory", "")).lower()
                    != actual_pad_inventory
                ):
                    errors.append(
                        "hierarchy_validation_hash:pad_net_inventory"
                    )
                contract_path = (
                    root
                    / "hardware/system_carrier/HIERARCHY_INTERFACE_SYS_001.csv"
                )
                if not contract_path.is_file():
                    errors.append("hierarchy_contract_missing")
                elif (
                    str(hashes.get("hierarchy_contract", "")).lower()
                    != sha256_file(contract_path)
                ):
                    errors.append(
                        "hierarchy_validation_hash:hierarchy_contract"
                    )

    no_mmwave_validation = None
    no_mmwave_path = resolved.get("no_mmwave_review_result")
    if no_mmwave_path is not None:
        try:
            no_mmwave_validation = json.loads(
                no_mmwave_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"no_mmwave_review_parse:{exc}")
        else:
            if (
                no_mmwave_validation.get("schema")
                != "ALTIUM-NO-MMWAVE-REVIEW-RESULT-001"
            ):
                errors.append("no_mmwave_review_schema")
            if no_mmwave_validation.get("status") != "PASS":
                reasons.append("NO_MMWAVE_REVIEW")
            hashes = no_mmwave_validation.get("input_sha256", {})
            if not isinstance(hashes, dict):
                errors.append("no_mmwave_review_input_sha256")
            else:
                for artifact_id, hash_key in (
                    ("no_mmwave_review", "review"),
                    ("pcb", "pcb"),
                    ("component_inventory", "component_inventory"),
                    ("net_inventory", "net_inventory"),
                ):
                    actual = str(
                        integrity.get(artifact_id, {}).get(
                            "sha256_actual", ""
                        )
                    ).lower()
                    if str(hashes.get(hash_key, "")).lower() != actual:
                        errors.append(
                            f"no_mmwave_review_hash:{artifact_id}"
                        )

    script_runtime = None
    script_runtime_rerun = None
    script_runtime_path = resolved.get("script_runtime_result")
    script_runtime_receipt_path = resolved.get("script_runtime_receipt")
    if script_runtime_path is not None:
        try:
            script_runtime = json.loads(
                script_runtime_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"script_runtime_parse:{exc}")
        else:
            if script_runtime_receipt_path is None:
                errors.append("script_runtime_receipt_missing")
            else:
                try:
                    script_runtime_rerun = (
                        validate_script_runtime_receipt(
                            receipt_json=script_runtime_receipt_path,
                            repository_root=root,
                        )
                    )
                except (
                    OSError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    ValueError,
                ) as exc:
                    errors.append(
                        f"script_runtime_rerun:{exc}"
                    )
                else:
                    if script_runtime_rerun != script_runtime:
                        errors.append(
                            "script_runtime_result_not_reproducible"
                        )
                    if (
                        script_runtime_rerun.get("status") != "PASS"
                        or script_runtime_rerun.get(
                            "runtime_validated"
                        )
                        is not True
                    ):
                        reasons.append("SCRIPT_RUNTIME_RERUN")

            if (
                script_runtime.get("schema")
                != "ALTIUM-SCRIPT-RUNTIME-RESULT-001"
            ):
                errors.append("script_runtime_schema")
            if (
                script_runtime.get("status") != "PASS"
                or script_runtime.get("runtime_validated") is not True
            ):
                reasons.append("SCRIPT_RUNTIME")

            actual_receipt = str(
                integrity.get("script_runtime_receipt", {}).get(
                    "sha256_actual",
                    "",
                )
            ).lower()
            if (
                str(
                    script_runtime.get("receipt_sha256", "")
                ).lower()
                != actual_receipt
            ):
                errors.append("script_runtime_hash:receipt")

            runtime_inputs = script_runtime.get("input_sha256")
            if not isinstance(runtime_inputs, dict):
                errors.append("script_runtime_input_sha256")
                runtime_inputs = {}

            for artifact_id in ("project", "schematic", "pcb"):
                actual = str(
                    integrity.get(artifact_id, {}).get(
                        "sha256_actual",
                        "",
                    )
                ).lower()
                if (
                    str(
                        runtime_inputs.get(artifact_id, "")
                    ).lower()
                    != actual
                ):
                    errors.append(
                        f"script_runtime_hash:{artifact_id}"
                    )

            runtime_source_paths = {
                "pcb_audit_script": (
                    "hardware/system_carrier/altium/scripts/"
                    "EVT_SYS_CARRIER_Audit.pas"
                ),
                "hierarchy_audit_script": (
                    "hardware/system_carrier/altium/scripts/"
                    "EVT_SYS_CARRIER_Hierarchy_Audit.pas"
                ),
                "api_contract": (
                    "hardware/system_carrier/altium/"
                    "ALTIUM_SCRIPT_API_COMPAT_SYS_001.json"
                ),
                "script_project": (
                    "hardware/system_carrier/altium/scripts/"
                    "EVT_SYS_CARRIER_Audit.PrjScr"
                ),
            }
            for artifact_id, relative in runtime_source_paths.items():
                path = root / relative
                if not path.is_file():
                    errors.append(
                        f"script_runtime_source_missing:{artifact_id}"
                    )
                    continue
                actual = sha256_file(path)
                if (
                    str(
                        runtime_inputs.get(artifact_id, "")
                    ).lower()
                    != actual
                ):
                    errors.append(
                        f"script_runtime_hash:{artifact_id}"
                    )

            runtime_outputs = script_runtime.get("output_sha256")
            if not isinstance(runtime_outputs, dict):
                errors.append("script_runtime_output_sha256")
                runtime_outputs = {}

            for artifact_id in (
                "component_inventory",
                "net_inventory",
                "rule_inventory",
                "pad_net_inventory",
                "layer_stack_inventory",
                "hierarchy_export",
            ):
                actual = str(
                    integrity.get(artifact_id, {}).get(
                        "sha256_actual",
                        "",
                    )
                ).lower()
                if (
                    str(
                        runtime_outputs.get(artifact_id, "")
                    ).lower()
                    != actual
                ):
                    errors.append(
                        f"script_runtime_hash:{artifact_id}"
                    )

    native_audit = None
    native_audit_path = resolved.get("native_audit_result")
    if native_audit_path is not None:
        try:
            native_audit = json.loads(
                native_audit_path.read_text(encoding="utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"native_audit_parse:{exc}")
        else:
            if (
                native_audit.get("schema")
                != "ALTIUM-NATIVE-AUDIT-RESULT-001"
            ):
                errors.append("native_audit_schema")
            if native_audit.get("status") != "PASS":
                reasons.append("NATIVE_AUDIT")

            input_sha256 = native_audit.get("input_sha256")
            if not isinstance(input_sha256, dict):
                errors.append("native_audit_input_sha256")
            else:
                for artifact_id in (
                    "component_inventory",
                    "net_inventory",
                    "rule_inventory",
                    "pad_net_inventory",
                    "layer_stack_inventory",
                ):
                    actual = str(
                        integrity.get(artifact_id, {}).get(
                            "sha256_actual",
                            "",
                        )
                    ).lower()
                    claimed = str(
                        input_sha256.get(artifact_id, "")
                    ).lower()
                    if not actual or claimed != actual:
                        errors.append(
                            f"native_audit_input_hash:{artifact_id}"
                        )

    checks_raw = manifest.get("checks")
    checks: dict[str, str] = {}
    if not isinstance(checks_raw, dict):
        errors.append("checks")
    else:
        for name in sorted(REQUIRED_CHECKS):
            value = str(
                checks_raw.get(name, "MISSING")
            ).strip()
            checks[name] = value
            if value != "PASS":
                reasons.append(
                    f"CHECK_{name.upper()}"
                )

    preserved_kicad = bool(
        manifest.get("preserve_kicad", False)
    )
    if not preserved_kicad:
        reasons.append("KICAD_NOT_PRESERVED")

    review_a = str(
        manifest.get("review_a_status", "")
    ).strip()
    if review_a != "PASS":
        reasons.append("REVIEW_A_NOT_PASS")

    synthetic = bool(
        manifest.get("synthetic_fixture", False)
    )
    evidence_level = str(
        manifest.get("evidence_level", "")
    ).strip()

    if errors:
        status = "INVALID"
    elif reasons:
        status = "FAIL"
    elif synthetic:
        status = "TEST_READY"
    elif evidence_level != "NATIVE_ALTIUM":
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
        "primary_cad": manifest.get("primary_cad"),
        "synthetic_fixture": synthetic,
        "evidence_level": evidence_level,
        "errors": sorted(set(errors)),
        "reason_codes": sorted(set(reasons)),
        "integrity": integrity,
        "native_file_preflight": native_file_preflight,
        "native_file_preflight_rerun": native_file_preflight_rerun,
        "import_package": import_package,
        "import_native_preflight": import_native_preflight,
        "import_receipt": import_receipt,
        "bom_validation": bom_validation,
        "connector_validation": connector_validation,
        "netlist_validation": netlist_validation,
        "footprint_validation": footprint_validation,
        "hierarchy_validation": hierarchy_validation,
        "no_mmwave_validation": no_mmwave_validation,
        "script_runtime": script_runtime,
        "script_runtime_rerun": script_runtime_rerun,
        "compile": compile_result,
        "compile_validation": compile_validation,
        "native_audit": native_audit,
        "checks": checks,
        "preserve_kicad": preserved_kicad,
        "review_a_status": review_a,
        "layout_authority": (
            "AUTHORIZED"
            if status == "PASS"
            else "NOT_AUTHORIZED"
        ),
        "production_authority": "NOT_AUTHORIZED",
        "notes": [
            (
                "PASS authorizes native Altium PCB implementation "
                "as the layout authority for System Carrier Rev.A."
            ),
            (
                "PASS does not authorize production; DRC, SI/return-path, "
                "DFM and manufacturing release gates remain separate."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
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
    return 0 if result["status"] in {"PASS", "TEST_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
