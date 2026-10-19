from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "hardware/system_carrier/altium/scripts/"
    "EVT_SYS_CARRIER_Hierarchy_Audit.pas"
)


def test_hierarchy_exporter_is_read_only_and_uses_compiled_project_ports():
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "GetWorkspace",
        "DM_FocusedProject",
        "DM_LogicalDocumentCount",
        "DM_LogicalDocuments",
        "DM_Compile",
        "SchServer.GetSchDocumentByPath",
        "SchIterator_Create",
        "MkSet(ePort)",
        "Port.Name",
        "Port.IOType",
        "hierarchy_export.csv",
    ):
        assert required in text

    for forbidden in (
        "AddSchObject(",
        "RemoveSchObject(",
        "SetState_",
        "RobotManager.SendMessage",
        "ProcessControl.PreProcess",
        "ProcessControl.PostProcess",
    ):
        assert forbidden not in text
