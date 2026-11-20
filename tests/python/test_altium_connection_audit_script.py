from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "hardware/system_carrier/altium/scripts/"
    "EVT_SYS_CARRIER_ConnectionAudit.pas"
)


def test_connection_audit_is_read_only_and_exports_complete_geometry():
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "EVT_SYS_CARRIER.PcbDoc",
        "eComponentObject",
        "ePadObject",
        "eTrackObject",
        "eFillObject",
        "eViaObject",
        "BoundingRectangle",
        "Pad.Component",
        "Pad.Net",
        "component_bounds.csv",
        "pad_geometry.csv",
        "track_inventory.csv",
        "fill_inventory.csv",
        "via_inventory.csv",
    ):
        assert required in text

    for forbidden in (
        "PCBServer.PreProcess",
        "PCBServer.PostProcess",
        "AddPCBObject(",
        "RemovePCBObject(",
        "SetState_",
    ):
        assert forbidden not in text
