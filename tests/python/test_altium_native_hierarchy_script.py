from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "hardware/system_carrier/altium/scripts/"
    "EVT_SYS_CARRIER_HierarchyAudit.pas"
)


def test_native_hierarchy_audit_script_is_read_only_and_complete():
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "DM_FocusedProject",
        "DM_LogicalDocumentCount",
        "DM_LogicalDocuments",
        "SchServer.GetSchDocumentByPath",
        "ePort",
        "eSheetEntry",
        "GetState_SchOwnerSheetSymbol",
        "SheetFileName.Text",
        "PortObj.IOType",
        "EntryObj.IOType",
        "hierarchy_port_inventory.csv",
        "hierarchy_sheet_entry_inventory.csv",
    ):
        assert required in text

    for forbidden in (
        "SchServer.RobotManager.SendMessage",
        "RegisterSchObjectInContainer",
        "RemoveSchObject",
        "SetState_",
        "GraphicallyInvalidate",
    ):
        assert forbidden not in text
