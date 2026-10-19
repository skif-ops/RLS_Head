from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "hardware/system_carrier/altium/scripts/"
    "EVT_SYS_CARRIER_Audit.pas"
)


def test_native_audit_script_exports_rich_read_only_evidence():
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "eComponentObject",
        "eNetObject",
        "eRuleObject",
        "ePadObject",
        "Pad.Component",
        "Pad.Net",
        "Board.LayerStack",
        "Layer2String(LayerObj.LayerID)",
        "Rule.Scope1Expression",
        "Rule.Scope2Expression",
        "Rule.DRCEnabled",
        "component_inventory.csv",
        "net_inventory.csv",
        "rule_inventory.csv",
        "pad_net_inventory.csv",
        "layer_stack_inventory.csv",
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
