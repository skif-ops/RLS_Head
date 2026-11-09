from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate common vertical offsets for the D79 antenna aperture")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--shifts", required=True, nargs="+", type=float)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    tools_dir = Path(__file__).resolve().parent
    results: list[dict[str, object]] = []

    for shift in args.shifts:
        label = f"{shift:g}".replace(".", "p")
        candidate = args.work_dir / f"candidate_shift_{label}.PcbDoc"
        manifest = args.work_dir / f"candidate_shift_{label}.json"
        pattern = args.work_dir / f"candidate_shift_{label}.csv"
        report = args.work_dir / f"candidate_shift_{label}_preflight.json"
        subprocess.run(
            [
                sys.executable,
                str(tools_dir / "radar_wide_elevation_antenna.py"),
                "--source",
                str(args.source),
                "--output",
                str(candidate),
                "--manifest",
                str(manifest),
                "--pattern-csv",
                str(pattern),
                "--array-shift-y-mm",
                str(shift),
                "--preserve-rf-conflicting-vias",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(tools_dir / "verify_radar_wide_elevation_antenna.py"),
                "--pcb",
                str(candidate),
                "--manifest",
                str(manifest),
                "--output",
                str(report),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        data = json.loads(report.read_text(encoding="utf-8"))
        results.append(
            {
                "shift_y_mm": shift,
                "status": data["status"],
                "top_copper_intrusions": len(data["non_antenna_top_copper_in_rf_zone"]),
                "via_clearance_intrusions": len(data["non_antenna_vias_inside_rf_copper_clearance"]),
                "errors": data["errors"],
                "candidate": str(candidate),
            }
        )

    output = args.work_dir / "shift_evaluation.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
