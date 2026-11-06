import csv
import json
from pathlib import Path

import pcb_a10_planner as design


ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / "build-cad/pcb_a10_plan.json").read_text(encoding="utf-8"))
POWER_PLAN = json.loads((ROOT / "build-cad/pcb_a10_power_plan.json").read_text(encoding="utf-8"))
OUT = ROOT / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER_SignalRoutingCandidate.pas"


def fmt(value):
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if "." in text else text + ".0"


def narrow_segments():
    result = set()
    for row in design.rows("pad_geometry.csv"):
        manual = design.MANUAL_LEADS.get((row["designator"], row["pad_name"]))
        if manual is None:
            continue
        lead = [design.row_point(row), *manual]
        for first, second in zip(lead, lead[1:]):
            result.add(tuple(sorted(((round(first[0], 6), round(first[1], 6)), (round(second[0], 6), round(second[1], 6))))))
    return result


def component_centers():
    with (design.AUDIT / "component_bounds.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {row["designator"]: (design.mm(row["x_mil"]), design.mm(row["y_mil"])) for row in rows}


def layer_name(index):
    return {0: "eTopLayer", 1: "eMidLayer2", 2: "eBottomLayer"}[index]


def generate():
    targets = list(PLAN)
    target_expr = " Or\n              ".join(f"(N = '{net}')" for net in targets)
    header = f"""{{ Apply PCB-A10 signal routing to the isolated candidate board. }}

Function A10Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function ExpectedA10BoardPath : String;
Var
    Workspace : IWorkspace;
    Project   : IProject;
    I         : Integer;
Begin
    Result := '';
    Workspace := GetWorkspace;
    If Workspace = Nil Then Exit;
    For I := 0 To Workspace.DM_ProjectCount - 1 Do
    Begin
        Project := Workspace.DM_Projects(I);
        If Project = Nil Then Continue;
        If ExtractFileName(Project.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER_SignalRoutingCandidate.PrjScr' Then Continue;
        Result := ExtractFilePath(Project.DM_ProjectFullPath) + 'EVT_SYS_CARRIER_signal_candidate.PcbDoc';
        Exit;
    End;
End;

Function IsExpectedA10Board(APath : String; ExpectedPath : String) : Boolean;
Begin
    Result := (ExpectedPath <> '') And (UpperCase(APath) = UpperCase(ExpectedPath));
End;

Function ResolveA10Board : IPCB_Board;
Var
    Board        : IPCB_Board;
    ExpectedPath : String;
Begin
    ExpectedPath := ExpectedA10BoardPath;
    If ExpectedPath = '' Then
    Begin
        Result := Nil;
        Exit;
    End;
    Result := PCBServer.GetPCBBoardByPath(ExpectedPath);
    If Result <> Nil Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If Not IsExpectedA10Board(Board.FileName, ExpectedPath) Then
    Begin
        Result := Nil;
        Exit;
    End;
    Result := Board;
End;

Function FindA10Net(Board : IPCB_Board; NetName : String) : IPCB_Net;
Var
    Iterator : IPCB_BoardIterator;
    NetObj   : IPCB_Net;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eNetObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    NetObj := Iterator.FirstPCBObject;
    While NetObj <> Nil Do
    Begin
        If UpperCase(NetObj.Name) = UpperCase(NetName) Then
        Begin
            Result := NetObj;
            Break;
        End;
        NetObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function IsA10TargetNet(NetName : String) : Boolean;
Var
    N : String;
Begin
    N := UpperCase(NetName);
    Result := {target_expr};
End;

Function ExistingA10TrackCount(Board : IPCB_Board) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Track    : IPCB_Track;
Begin
    Result := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        If (Track.Net <> Nil) And IsA10TargetNet(Track.Net.Name) Then
            Result := Result + 1;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function FindA10Component(Board : IPCB_Board; DesignatorText : String) : IPCB_Component;
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        If UpperCase(Component.SourceDesignator) = UpperCase(DesignatorText) Then
        Begin
            Result := Component;
            Break;
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure MoveA10Component(Board : IPCB_Board; DesignatorText, XText, YText : String);
Var
    Component : IPCB_Component;
Begin
    Component := FindA10Component(Board, DesignatorText);
    If Component = Nil Then Exit;
    Component.X := A10Coord(XText);
    Component.Y := A10Coord(YText);
End;

Function FindA10Pad(Board : IPCB_Board; DesignatorText, PadNameText : String) : IPCB_Pad;
Var
    Iterator : IPCB_BoardIterator;
    PadObj   : IPCB_Pad;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    PadObj := Iterator.FirstPCBObject;
    While PadObj <> Nil Do
    Begin
        If PadObj.Component <> Nil Then
        Begin
            If (UpperCase(PadObj.Component.SourceDesignator) = UpperCase(DesignatorText)) And
               (UpperCase(PadObj.Name) = UpperCase(PadNameText)) Then
            Begin
                Result := PadObj;
                Break;
            End;
        End;
        PadObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure SnapA10PadConnections(Board : IPCB_Board; DesignatorText, PadNameText : String);
Var
    PadObj    : IPCB_Pad;
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    ViaObj    : IPCB_Via;
    Tolerance : TCoord;
Begin
    PadObj := FindA10Pad(Board, DesignatorText, PadNameText);
    If (PadObj = Nil) Or (PadObj.Net = Nil) Then Exit;
    Tolerance := A10Coord('0.02mm');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(PadObj.Net.Name)) Then
        Begin
            If (Abs(Track.X1 - PadObj.X) <= Tolerance) And
               (Abs(Track.Y1 - PadObj.Y) <= Tolerance) Then
            Begin
                Track.X1 := PadObj.X;
                Track.Y1 := PadObj.Y;
            End;
            If (Abs(Track.X2 - PadObj.X) <= Tolerance) And
               (Abs(Track.Y2 - PadObj.Y) <= Tolerance) Then
            Begin
                Track.X2 := PadObj.X;
                Track.Y2 := PadObj.Y;
            End;
        End;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        If (ViaObj.Net <> Nil) And (UpperCase(ViaObj.Net.Name) = UpperCase(PadObj.Net.Name)) And
           (Abs(ViaObj.X - PadObj.X) <= Tolerance) And
           (Abs(ViaObj.Y - PadObj.Y) <= Tolerance) Then
        Begin
            ViaObj.X := PadObj.X;
            ViaObj.Y := PadObj.Y;
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure AddA10Track(Board : IPCB_Board; NetName, X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                      LayerValue : TLayer; Var TrackCount : Integer);
Var
    Track  : IPCB_Track;
    NetObj : IPCB_Net;
Begin
    NetObj := FindA10Net(Board, NetName);
    If NetObj = Nil Then Exit;
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := A10Coord(X1Text);
    Track.Y1 := A10Coord(Y1Text);
    Track.X2 := A10Coord(X2Text);
    Track.Y2 := A10Coord(Y2Text);
    Track.Width := A10Coord(WidthText);
    Track.Layer := LayerValue;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure AddA10Via(Board : IPCB_Board; NetName, XText, YText : String; Var ViaCount : Integer);
Var
    ViaObj : IPCB_Via;
    NetObj : IPCB_Net;
Begin
    NetObj := FindA10Net(Board, NetName);
    If NetObj = Nil Then Exit;
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := A10Coord(XText);
    ViaObj.Y := A10Coord(YText);
    ViaObj.Size := A10Coord('0.60mm');
    ViaObj.HoleSize := A10Coord('0.30mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    ViaCount := ViaCount + 1;
End;

Procedure RemoveAllTracksForNet(Board : IPCB_Board; NetName : String; Var RemovedCount : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(NetName)) Then
        Begin
            Board.RemovePCBObject(Track);
            RemovedCount := RemovedCount + 1;
        End;
        Track := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function SameA10Segment(Track : IPCB_Track; X1, Y1, X2, Y2 : TCoord) : Boolean;
Var
    Tolerance : TCoord;
Begin
    Tolerance := A10Coord('0.02mm');
    Result :=
        ((Abs(Track.X1 - X1) <= Tolerance) And (Abs(Track.Y1 - Y1) <= Tolerance) And
         (Abs(Track.X2 - X2) <= Tolerance) And (Abs(Track.Y2 - Y2) <= Tolerance)) Or
        ((Abs(Track.X1 - X2) <= Tolerance) And (Abs(Track.Y1 - Y2) <= Tolerance) And
         (Abs(Track.X2 - X1) <= Tolerance) And (Abs(Track.Y2 - Y1) <= Tolerance));
End;

Procedure RemoveA10Segment(Board : IPCB_Board; NetName, X1Text, Y1Text, X2Text, Y2Text : String;
                           Var RemovedCount : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(NetName)) And
           SameA10Segment(Track, A10Coord(X1Text), A10Coord(Y1Text), A10Coord(X2Text), A10Coord(Y2Text)) Then
        Begin
            Board.RemovePCBObject(Track);
            RemovedCount := RemovedCount + 1;
        End;
        Track := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure RemoveA10Via(Board : IPCB_Board; NetName, XText, YText : String; Var RemovedCount : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
    Tolerance: TCoord;
Begin
    Tolerance := A10Coord('0.02mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And (UpperCase(ViaObj.Net.Name) = UpperCase(NetName)) And
           (Abs(ViaObj.X - A10Coord(XText)) <= Tolerance) And
           (Abs(ViaObj.Y - A10Coord(YText)) <= Tolerance) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            RemovedCount := RemovedCount + 1;
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyEVTSignalRoutingCandidate;
Var
    Board         : IPCB_Board;
    TrackCount    : Integer;
    ViaCount      : Integer;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
Begin
    Board := ResolveA10Board;
    If Board = Nil Then
    Begin
        ShowMessage('PCB-A10 stopped: open the isolated signal candidate PcbDoc.');
        Exit;
    End;
    If ExistingA10TrackCount(Board) <> 0 Then
    Begin
        ShowMessage('PCB-A10 stopped: one or more target nets already contain tracks.');
        Exit;
    End;
"""
    lines = [header]
    for net in targets:
        lines.append(f"    If FindA10Net(Board, '{net}') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net {net}.'); Exit; End;\n")
    for net in sorted(design.POWER_STITCH_NETS):
        lines.append(f"    If FindA10Net(Board, '{net}') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net {net}.'); Exit; End;\n")
    lines.append("\n    TrackCount := 0; ViaCount := 0; RemovedTracks := 0; RemovedVias := 0;\n    PCBServer.PreProcess;\n")

    centers = component_centers()
    for designator, shift in design.PLACEMENT_SHIFT.items():
        x, y = centers[designator]
        lines.append(f"    MoveA10Component(Board, '{designator}', '{fmt(x + shift[0])}mm', '{fmt(y + shift[1])}mm');\n")

    lines.append("\n    { Restore 3V3 and GND connections for moved components. }\n")
    via_seen = set()
    for item in POWER_PLAN:
        net = item["net"]
        route = item["route"]
        source_key = item["designator"], item["pad_name"]
        lines.append(
            f"    {{ {item['designator']}-{item['pad_name']} to "
            f"{item['target_designator']}-{item['target_pad_name']} }}\n"
        )
        for index, (first, second) in enumerate(zip(route, route[1:])):
            if first[0] == second[0]:
                width = design.power_segment_width(route, index, source_key)
                lines.append(
                    f"    AddA10Track(Board, '{net}', '{fmt(first[1])}mm', '{fmt(first[2])}mm', "
                    f"'{fmt(second[1])}mm', '{fmt(second[2])}mm', '{fmt(width)}mm', "
                    f"{layer_name(first[0])}, TrackCount);\n"
                )
            else:
                key = (net, round(first[1], 6), round(first[2], 6))
                if key not in via_seen:
                    via_seen.add(key)
                    lines.append(f"    AddA10Via(Board, '{net}', '{fmt(first[1])}mm', '{fmt(first[2])}mm', ViaCount);\n")

    lines.append("\n    RemoveAllTracksForNet(Board, 'GNSS_PPS', RemovedTracks);\n")
    for net, segments in design.MDI_REPLACED_SEGMENTS.items():
        for segment in sorted(segments):
            first, second = segment
            lines.append(f"    RemoveA10Segment(Board, '{net}', '{fmt(first[0])}mm', '{fmt(first[1])}mm', '{fmt(second[0])}mm', '{fmt(second[1])}mm', RemovedTracks);\n")
    lines.append("    RemoveA10Via(Board, 'ETH_TXP', '75.0mm', '55.49mm', RemovedVias);\n\n")

    for first, second in design.GNSS_PPS_REROUTE:
        lines.append(f"    AddA10Track(Board, 'GNSS_PPS', '{fmt(first[0])}mm', '{fmt(first[1])}mm', '{fmt(second[0])}mm', '{fmt(second[1])}mm', '0.20mm', eTopLayer, TrackCount);\n")
    for net, layer, first, second in design.MDI_REPLACEMENT_TRACKS:
        lines.append(f"    AddA10Track(Board, '{net}', '{fmt(first[0])}mm', '{fmt(first[1])}mm', '{fmt(second[0])}mm', '{fmt(second[1])}mm', '0.26mm', {layer_name(layer)}, TrackCount);\n")
    lines.append("    AddA10Via(Board, 'ETH_TXP', '79.0mm', '55.49mm', ViaCount);\n\n")

    narrow = narrow_segments()
    for net, routes in PLAN.items():
        lines.append(f"    {{ {net} }}\n")
        for route in routes:
            for first, second in zip(route, route[1:]):
                if first[0] == second[0]:
                    key = tuple(sorted(((round(first[1], 6), round(first[2], 6)), (round(second[1], 6), round(second[2], 6)))))
                    width = "0.15mm" if key in narrow else "0.20mm"
                    lines.append(
                        f"    AddA10Track(Board, '{net}', '{fmt(first[1])}mm', '{fmt(first[2])}mm', "
                        f"'{fmt(second[1])}mm', '{fmt(second[2])}mm', '{width}', {layer_name(first[0])}, TrackCount);\n"
                    )
                else:
                    key = (net, round(first[1], 6), round(first[2], 6))
                    if key not in via_seen:
                        via_seen.add(key)
                        lines.append(f"    AddA10Via(Board, '{net}', '{fmt(first[1])}mm', '{fmt(first[2])}mm', ViaCount);\n")
        lines.append("\n")

    lines.append("    { Snap generated primitives to the native pad coordinates after component moves. }\n")
    moved_pads = sorted(
        {
            (row["designator"], row["pad_name"])
            for row in design.rows("pad_geometry.csv")
            if row["designator"] in design.PLACEMENT_SHIFT
        }
    )
    for designator, pad_name in moved_pads:
        lines.append(f"    SnapA10PadConnections(Board, '{designator}', '{pad_name}');\n")
    lines.append("\n")

    lines.append("""    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    ShowMessage('PCB-A10 candidate applied: added ' + IntToStr(TrackCount) +
                ' tracks and ' + IntToStr(ViaCount) + ' vias; removed ' +
                IntToStr(RemovedTracks) + ' tracks and ' + IntToStr(RemovedVias) +
                ' vias. Save and run DRC plus connection audit.');
End;
""")
    OUT.write_text("".join(lines), encoding="utf-8")
    prj = OUT.with_suffix(".PrjScr")
    prj.write_text(
        "[Design]\nVersion=1.0\nHierarchyMode=0\n\n"
        "[Document1]\nDocumentPath=" + OUT.name + "\nAnnotationEnabled=1\n\n"
        "[Generic_ScriptingSystem]\nStartProcName=" + OUT.name + ">ApplyEVTSignalRoutingCandidate\n",
        encoding="utf-8",
    )
    print(OUT)
    print(
        f"tracks={sum(1 for line in lines if '    AddA10Track(Board' in line)} "
        f"vias={sum(1 for line in lines if '    AddA10Via(Board' in line)}"
    )


if __name__ == "__main__":
    generate()
