from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "hardware" / "system_carrier" / "altium" / "native"
STALE = "EVT_SYS_CARRIER_OPEN_DIRTY_BACKUP_BEFORE_DRC_ZERO_PROMOTION_2026-11-02.PcbDoc"
CANONICAL = "EVT_SYS_CARRIER.PcbDoc"


def rebind(path: Path) -> int:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    count = text.count(STALE)
    if count:
        path.write_bytes(text.replace(STALE, CANONICAL).encode("utf-8"))
    updated = path.read_text(encoding="utf-8-sig")
    if STALE in updated:
        raise RuntimeError(f"Stale board binding remains in {path}")
    return count


def main() -> None:
    total = 0
    for name in ("Fabrication.OutJob", "Assembly.OutJob"):
        path = NATIVE / name
        replacements = rebind(path)
        total += replacements
        print(f"{name}: {replacements} binding(s) updated")
    if total == 0:
        print("OutJob bindings already canonical")


if __name__ == "__main__":
    main()
