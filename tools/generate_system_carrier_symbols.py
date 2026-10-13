from __future__ import annotations

import argparse
import csv
from pathlib import Path


LIBRARY_NAME = "SystemCarrier_Local"
CORE_TARGET_REFS = {"U2", "U4", "U5", "U6", "U7"}
AUX_TARGET_REFS = {"Y1", "Y2", "D3", "D4"}
TARGET_REFS = CORE_TARGET_REFS | AUX_TARGET_REFS

PIN_TYPE = {
    "DIGITAL_IN": "input",
    "CLOCK_IN": "input",
    "ANALOG_IN": "input",
    "STRAP_IN": "input",
    "RF_IN": "input",
    "DIGITAL_OUT": "output",
    "DIGITAL_OUT_STRAP": "output",
    "ANALOG_OUT": "output",
    "POWER_SWITCH": "passive",
    "POWER_OUT": "power_out",
    "OPEN_DRAIN_OUT": "open_collector",
    "DIGITAL_IO": "bidirectional",
    "BUS_IO": "bidirectional",
    "ANALOG_IO": "bidirectional",
    "USB_IO": "bidirectional",
    "STRAP_IO": "bidirectional",
    "POWER_IN": "power_in",
    "GROUND": "power_in",
    "THERMAL_PAD": "power_in",
    "CLOCK": "output",
    "ANALOG": "passive",
    "RESERVED": "passive",
}

REF_PREFIX = {
    "ICM-42688-P": "U",
    "TCAN3404DRBRQ1": "U",
    "TPS62132RGTR": "U",
    "TPS259470ARPWR": "U",
    "ECS-2520S33-250-FN-TR": "Y",
    "ECS-2520S33-500-FN-TR": "Y",
    "ESD2CANFD24DBZRQ1": "D",
    "TPD4E05U06DQAR": "D",
}


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        return list(reader)


def _footprints(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}

    for row in _read_csv(path):
        if str(row.get("status", "")).strip() != "LOCKED":
            continue

        mpn = str(row.get("mpn", "")).strip()
        footprint = str(
            row.get("footprint_id", "")
        ).strip()

        if mpn and footprint:
            result[mpn] = footprint

    return result


def _pin_rows(
    paths: list[Path],
    target_refs: set[str],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}

    for path in paths:
        for row in _read_csv(path):
            ref = str(row.get("ref", "")).strip()
            if ref not in target_refs:
                continue

            role = str(
                row.get("electrical_role", "")
            ).strip()
            if role not in PIN_TYPE:
                raise ValueError(
                    f"unsupported electrical_role:{ref}:{role}"
                )

            grouped.setdefault(ref, []).append(row)

    missing = sorted(target_refs - set(grouped))
    if missing:
        raise ValueError(
            "missing target refs:" + ",".join(missing)
        )

    return grouped

def _pin_sort_key(pin: str) -> tuple[int, str]:
    try:
        return (0, f"{int(pin):06d}")
    except ValueError:
        return (1, pin)


def _symbol_text(
    *,
    name: str,
    pins: list[dict[str, str]],
    footprint: str,
) -> str:
    pins = sorted(
        pins,
        key=lambda row: _pin_sort_key(
            str(row["pin_number"]).strip()
        ),
    )

    left = pins[::2]
    right = pins[1::2]
    row_count = max(len(left), len(right), 1)

    pitch = 2.54
    half_height = max(10.16, (row_count + 1) * pitch / 2)
    half_width = 10.16

    lines: list[str] = []
    lines.append(
        f'  (symbol "{_escape(name)}" '
        '(pin_names (offset 1.016)) '
        '(exclude_from_sim no) (in_bom yes) (on_board yes)'
    )
    lines.append(
        f'    (property "Reference" "{REF_PREFIX.get(name, "U")}" '
        f'(at {-half_width:.2f} {half_height + 2.54:.2f} 0) '
        '(effects (font (size 1.27 1.27))))'
    )
    lines.append(
        f'    (property "Value" "{_escape(name)}" '
        f'(at {half_width:.2f} {half_height + 2.54:.2f} 0) '
        '(effects (font (size 1.27 1.27)) (justify right)))'
    )
    lines.append(
        f'    (property "Footprint" "{_escape(footprint)}" '
        '(at 0 0 0) (effects (font (size 1.27 1.27)) hide))'
    )
    lines.append(
        '    (property "Datasheet" "" '
        '(at 0 0 0) (effects (font (size 1.27 1.27)) hide))'
    )
    lines.append(
        '    (property "Description" '
        f'"Generated from SYMBOL_PIN_CONTRACT_SYS_001.csv for {_escape(name)}" '
        '(at 0 0 0) (effects (font (size 1.27 1.27)) hide))'
    )
    lines.append(
        f'    (symbol "{_escape(name)}_0_1"'
    )
    lines.append(
        f'      (rectangle (start {-half_width:.2f} {half_height:.2f}) '
        f'(end {half_width:.2f} {-half_height:.2f}) '
        '(stroke (width 0.254) (type default)) '
        '(fill (type background)))'
    )
    lines.append('    )')
    lines.append(
        f'    (symbol "{_escape(name)}_1_1"'
    )

    def append_pin(
        row: dict[str, str],
        index: int,
        *,
        left_side: bool,
    ) -> None:
        pin_num = str(row["pin_number"]).strip()
        pin_name = str(row["pin_name"]).strip()
        role = str(row["electrical_role"]).strip()
        ptype = PIN_TYPE[role]

        # TPS62132 exposes three internally common SW package pins.
        # Model one as the power-output source and the other duplicated
        # package contacts as passive to avoid false output-vs-output ERC.
        if (
            name == "TPS62132RGTR"
            and role == "POWER_SWITCH"
            and pin_num in {"2", "3"}
        ):
            ptype = "passive"

        # TPD4E05U06 DQA package pins 6/7/9/10 are true NC pins.
        # Model them as no_connect in the symbol rather than placing
        # geometry-dependent NC markers after schematic instantiation.
        if (
            name == "TPD4E05U06DQAR"
            and pin_num in {"6", "7", "9", "10"}
        ):
            ptype = "no_connect"

        # ESD-array ground contacts are passive return pins. Modeling
        # them as power_in incorrectly requires an artificial PWR_FLAG.
        if (
            name in {
                "TPD4E05U06DQAR",
                "ESD2CANFD24DBZRQ1",
            }
            and role == "GROUND"
        ):
            ptype = "passive"

        y = half_height - pitch * (index + 1)
        x = -half_width - 2.54 if left_side else half_width + 2.54
        angle = 0 if left_side else 180

        lines.append(
            f'      (pin {ptype} line '
            f'(at {x:.2f} {y:.2f} {angle}) (length 2.54)'
        )
        lines.append(
            f'        (name "{_escape(pin_name)}" '
            '(effects (font (size 1.0 1.0))))'
        )
        lines.append(
            f'        (number "{_escape(pin_num)}" '
            '(effects (font (size 1.0 1.0))))'
        )
        lines.append('      )')

    for index, row in enumerate(left):
        append_pin(row, index, left_side=True)

    for index, row in enumerate(right):
        append_pin(row, index, left_side=False)

    lines.append('    )')
    lines.append('  )')

    return "\n".join(lines)


def generate(
    *,
    pin_contract: str | Path,
    footprint_plan: str | Path,
    output: str | Path,
    aux_pin_contract: str | Path | None = None,
) -> dict:
    pin_contract = Path(pin_contract)
    footprint_plan = Path(footprint_plan)
    output = Path(output)

    pin_contracts = [pin_contract]
    target_refs = set(CORE_TARGET_REFS)

    if aux_pin_contract is not None:
        pin_contracts.append(
            Path(aux_pin_contract)
        )
        target_refs.update(
            AUX_TARGET_REFS
        )

    grouped = _pin_rows(
        pin_contracts,
        target_refs,
    )
    footprints = _footprints(footprint_plan)

    by_mpn: dict[str, dict] = {}

    for ref in sorted(grouped):
        rows = grouped[ref]
        mpns = {
            str(row["mpn"]).strip()
            for row in rows
        }
        if len(mpns) != 1:
            raise ValueError(
                f"mixed MPNs for {ref}"
            )

        mpn = next(iter(mpns))
        existing = by_mpn.get(mpn)

        if existing is None:
            by_mpn[mpn] = {
                "pins": rows,
                "refs": [ref],
                "footprint": footprints.get(mpn, ""),
            }
        else:
            existing["refs"].append(ref)
            existing_numbers = {
                str(row["pin_number"]).strip()
                for row in existing["pins"]
            }
            new_numbers = {
                str(row["pin_number"]).strip()
                for row in rows
            }
            if existing_numbers != new_numbers:
                raise ValueError(
                    f"pin contract differs between refs for {mpn}"
                )

    parts = [
        '(kicad_symbol_lib',
        '  (version 20241209)',
        '  (generator "rls_head_symbol_generator")',
        '  (generator_version "1.0")',
    ]

    manifest_symbols = []

    for mpn in sorted(by_mpn):
        item = by_mpn[mpn]
        parts.append(
            _symbol_text(
                name=mpn,
                pins=item["pins"],
                footprint=item["footprint"],
            )
        )
        manifest_symbols.append(
            {
                "name": mpn,
                "refs": item["refs"],
                "pin_count": len(item["pins"]),
                "footprint": item["footprint"],
            }
        )

    parts.append(')')

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        "\n".join(parts) + "\n",
        encoding="utf-8",
    )

    return {
        "schema": "SYSTEM-CARRIER-LOCAL-SYMBOL-LIBRARY-001",
        "status": "GENERATED",
        "library_name": LIBRARY_NAME,
        "symbol_count": len(manifest_symbols),
        "symbols": manifest_symbols,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin-contract", required=True)
    parser.add_argument("--footprint-plan", required=True)
    parser.add_argument("--aux-pin-contract")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = generate(
        pin_contract=args.pin_contract,
        footprint_plan=args.footprint_plan,
        output=args.output,
        aux_pin_contract=args.aux_pin_contract,
    )

    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
