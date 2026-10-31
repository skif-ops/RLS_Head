from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "build-cad/power_plane_fanout_plan.json"
OUTPUT = (
    ROOT
    / "hardware/system_carrier/altium/native/EVT_SYS_CARRIER_PowerPlaneClosure.pas"
)


def fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def layer_name(layer: int) -> str:
    return {
        1: "eTopLayer",
        2: "eMidLayer1",
        3: "eMidLayer2",
        32: "eBottomLayer",
    }[layer]


def qmm(value: float) -> str:
    return f"'{fmt(value)}mm'"


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    lines = [
        "{ Apply the audited 3V3/GND plane fanout closure to the physical candidate. }\n\n",
        "Function PPCCoord(ValueText : String) : TCoord;\n",
        "Var\n    UnitKind : TUnit;\n",
        "Begin\n    UnitKind := eMetric;\n",
        "    StringToCoordUnit(ValueText, Result, UnitKind);\nEnd;\n\n",
        "Function PPCIsCandidate(Board : IPCB_Board) : Boolean;\n",
        "Var\n    P : String;\n",
        "Begin\n    Result := False;\n    If Board = Nil Then Exit;\n",
        "    P := LowerCase(Board.FileName);\n",
        "    Result := (Pos('\\hardware\\system_carrier\\altium\\native\\', P) > 0) And\n",
        "        (UpperCase(ExtractFileName(Board.FileName)) =\n",
        "         'EVT_SYS_CARRIER_PHYSICAL_CLOSURE_CANDIDATE.PCBDOC');\n",
        "End;\n\n",
        "Function PPCFindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;\n",
        "Var\n    Iterator : IPCB_BoardIterator;\n    NetObj : IPCB_Net;\n",
        "Begin\n    Result := Nil;\n",
        "    Iterator := Board.BoardIterator_Create;\n",
        "    Iterator.AddFilter_ObjectSet(MkSet(eNetObject));\n",
        "    Iterator.AddFilter_LayerSet(AllLayers);\n",
        "    Iterator.AddFilter_Method(eProcessAll);\n",
        "    NetObj := Iterator.FirstPCBObject;\n",
        "    While NetObj <> Nil Do\n    Begin\n",
        "        If UpperCase(NetObj.Name) = UpperCase(NetName) Then\n",
        "        Begin\n            Result := NetObj;\n            Break;\n        End;\n",
        "        NetObj := Iterator.NextPCBObject;\n    End;\n",
        "    Board.BoardIterator_Destroy(Iterator);\nEnd;\n\n",
        "Function PPCFind3V3Plane(Board : IPCB_Board) : IPCB_Polygon;\n",
        "Var\n    Iterator : IPCB_BoardIterator;\n    PolyObj : IPCB_Polygon;\n",
        "Begin\n    Result := Nil;\n",
        "    Iterator := Board.BoardIterator_Create;\n",
        "    Iterator.AddFilter_ObjectSet(MkSet(ePolyObject));\n",
        "    Iterator.AddFilter_LayerSet(MkSet(eMidLayer2));\n",
        "    Iterator.AddFilter_Method(eProcessAll);\n",
        "    PolyObj := Iterator.FirstPCBObject;\n",
        "    While PolyObj <> Nil Do\n    Begin\n",
        "        If UpperCase(PolyObj.Name) = 'EVT_3V3_L3_PLANE' Then\n",
        "        Begin\n            Result := PolyObj;\n            Break;\n        End;\n",
        "        PolyObj := Iterator.NextPCBObject;\n    End;\n",
        "    Board.BoardIterator_Destroy(Iterator);\nEnd;\n\n",
        "Procedure PPCConfigure3V3Plane(Board : IPCB_Board; Rail : IPCB_Net;\n",
        "                                Var PolygonObj : IPCB_Polygon;\n",
        "                                Var Created : Boolean);\n",
        "Var\n    I : Integer;\n",
        "Begin\n",
        "    Board.BoardOutline.Invalidate;\n    Board.BoardOutline.Rebuild;\n",
        "    Board.BoardOutline.Validate;\n",
        "    PolygonObj := PPCFind3V3Plane(Board);\n",
        "    Created := PolygonObj = Nil;\n",
        "    If Created Then\n",
        "        PolygonObj := PCBServer.PCBObjectFactory(ePolyObject, eNoDimension, eCreate_Default)\n",
        "    Else\n        PolygonObj.BeginModify;\n",
        "    PolygonObj.Name := 'EVT_3V3_L3_PLANE';\n",
        "    PolygonObj.Layer := eMidLayer2;\n    PolygonObj.Net := Rail;\n",
        "    PolygonObj.PolygonType := eSignalLayerPolygon;\n",
        "    PolygonObj.PolyHatchStyle := ePolySolid;\n",
        "    PolygonObj.PourOver := ePolygonPourOver_None;\n",
        "    PolygonObj.Grid := MMsToCoord(0.25);\n",
        "    PolygonObj.TrackSize := MMsToCoord(0.25);\n",
        "    PolygonObj.MinTrack := MMsToCoord(0.20);\n",
        "    PolygonObj.BorderWidth := MMsToCoord(0.25);\n",
        "    PolygonObj.ArcApproximation := MMsToCoord(0.05);\n",
        "    PolygonObj.RemoveDead := False;\n",
        "    PolygonObj.RemoveIslandsByArea := False;\n",
        "    PolygonObj.RemoveNarrowNecks := False;\n",
        "    PolygonObj.PointCount := Board.BoardOutline.PointCount;\n",
        "    For I := 0 To Board.BoardOutline.PointCount - 1 Do\n",
        "        PolygonObj.Segments[I] := Board.BoardOutline.Segments[I];\n",
        "End;\n\n",
        "Procedure PPCAddTrack(Board : IPCB_Board; NetName, X1Text, Y1Text,\n",
        "                      X2Text, Y2Text, WidthText : String;\n",
        "                      Var Count : Integer);\n",
        "Var\n    TrackObj : IPCB_Track;\n    NetObj : IPCB_Net;\n",
        "Begin\n    NetObj := PPCFindNet(Board, NetName);\n    If NetObj = Nil Then Exit;\n",
        "    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);\n",
        "    TrackObj.X1 := PPCCoord(X1Text);\n    TrackObj.Y1 := PPCCoord(Y1Text);\n",
        "    TrackObj.X2 := PPCCoord(X2Text);\n    TrackObj.Y2 := PPCCoord(Y2Text);\n",
        "    TrackObj.Width := PPCCoord(WidthText);\n    TrackObj.Layer := eTopLayer;\n",
        "    TrackObj.Net := NetObj;\n    Board.AddPCBObject(TrackObj);\n    Inc(Count);\nEnd;\n\n",
        "Procedure PPCAddVia(Board : IPCB_Board; NetName, XText, YText,\n",
        "                    SizeText, HoleText : String; HighLayer : TLayer;\n",
        "                    Var Count : Integer);\n",
        "Var\n    ViaObj : IPCB_Via;\n    NetObj : IPCB_Net;\n",
        "Begin\n    NetObj := PPCFindNet(Board, NetName);\n    If NetObj = Nil Then Exit;\n",
        "    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);\n",
        "    ViaObj.X := PPCCoord(XText);\n    ViaObj.Y := PPCCoord(YText);\n",
        "    ViaObj.Size := PPCCoord(SizeText);\n    ViaObj.HoleSize := PPCCoord(HoleText);\n",
        "    ViaObj.LowLayer := eTopLayer;\n    ViaObj.HighLayer := HighLayer;\n",
        "    ViaObj.Net := NetObj;\n    Board.AddPCBObject(ViaObj);\n    Inc(Count);\nEnd;\n\n",
        "Function PPCSameSegment(TrackObj : IPCB_Track; X1Text, Y1Text,\n",
        "                        X2Text, Y2Text : String) : Boolean;\n",
        "Begin\n",
        "    Result := (((TrackObj.X1 = PPCCoord(X1Text)) And (TrackObj.Y1 = PPCCoord(Y1Text)) And\n",
        "                (TrackObj.X2 = PPCCoord(X2Text)) And (TrackObj.Y2 = PPCCoord(Y2Text))) Or\n",
        "               ((TrackObj.X1 = PPCCoord(X2Text)) And (TrackObj.Y1 = PPCCoord(Y2Text)) And\n",
        "                (TrackObj.X2 = PPCCoord(X1Text)) And (TrackObj.Y2 = PPCCoord(Y1Text))));\n",
        "End;\n\n",
        "Procedure PPCRemoveTrack(Board : IPCB_Board; NetName, X1Text, Y1Text,\n",
        "                         X2Text, Y2Text : String; Var Count : Integer);\n",
        "Var\n    Iterator : IPCB_BoardIterator;\n    TrackObj, NextTrack : IPCB_Track;\n",
        "Begin\n    Iterator := Board.BoardIterator_Create;\n",
        "    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));\n",
        "    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));\n",
        "    Iterator.AddFilter_Method(eProcessAll);\n",
        "    TrackObj := Iterator.FirstPCBObject;\n",
        "    While TrackObj <> Nil Do\n    Begin\n",
        "        NextTrack := Iterator.NextPCBObject;\n",
        "        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) And\n",
        "           (UpperCase(TrackObj.Net.Name) = UpperCase(NetName)) And\n",
        "           PPCSameSegment(TrackObj, X1Text, Y1Text, X2Text, Y2Text) Then\n",
        "        Begin\n            Board.RemovePCBObject(TrackObj);\n            Inc(Count);\n        End;\n",
        "        TrackObj := NextTrack;\n    End;\n",
        "    Board.BoardIterator_Destroy(Iterator);\nEnd;\n\n",
        "Procedure PPCRemoveVia(Board : IPCB_Board; NetName, XText, YText : String;\n",
        "                       Var Count : Integer);\n",
        "Var\n    Iterator : IPCB_BoardIterator;\n    ViaObj, NextVia : IPCB_Via;\n",
        "Begin\n    Iterator := Board.BoardIterator_Create;\n",
        "    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));\n",
        "    Iterator.AddFilter_LayerSet(AllLayers);\n",
        "    Iterator.AddFilter_Method(eProcessAll);\n",
        "    ViaObj := Iterator.FirstPCBObject;\n",
        "    While ViaObj <> Nil Do\n    Begin\n",
        "        NextVia := Iterator.NextPCBObject;\n",
        "        If (ViaObj.Net <> Nil) And\n",
        "           (UpperCase(ViaObj.Net.Name) = UpperCase(NetName)) And\n",
        "           (ViaObj.X = PPCCoord(XText)) And (ViaObj.Y = PPCCoord(YText)) Then\n",
        "        Begin\n            Board.RemovePCBObject(ViaObj);\n            Inc(Count);\n        End;\n",
        "        ViaObj := NextVia;\n    End;\n",
        "    Board.BoardIterator_Destroy(Iterator);\nEnd;\n\n",
        "Procedure ApplyPowerPlaneClosure;\n",
        "Var\n    Board : IPCB_Board;\n    Rail3V3 : IPCB_Net;\n",
        "    PolygonObj : IPCB_Polygon;\n    Created : Boolean;\n",
        "    AddedTracks, AddedVias, RemovedTracks, RemovedVias : Integer;\n",
        "Begin\n    Board := PCBServer.GetCurrentPCBBoard;\n",
        "    If Not PPCIsCandidate(Board) Then\n",
        "    Begin\n",
        "        ShowMessage('Power-plane closure stopped: select EVT_SYS_CARRIER_physical_closure_candidate.PcbDoc.');\n",
        "        Exit;\n    End;\n",
        "    If Board.BoardOutline.PointCount < 3 Then\n",
        "    Begin\n        ShowMessage('Power-plane closure stopped: invalid board outline.');\n        Exit;\n    End;\n",
        "    Rail3V3 := PPCFindNet(Board, '3V3');\n",
        "    If (Rail3V3 = Nil) Or (PPCFindNet(Board, 'GND') = Nil) Then\n",
        "    Begin\n        ShowMessage('Power-plane closure stopped: 3V3 or GND net missing.');\n        Exit;\n    End;\n",
        "    AddedTracks := 0; AddedVias := 0; RemovedTracks := 0; RemovedVias := 0;\n",
        "    PPCConfigure3V3Plane(Board, Rail3V3, PolygonObj, Created);\n",
        "    PCBServer.PreProcess;\n    Try\n",
    ]

    for item in plan.get("cleanup_fanouts", []) + plan["fanouts"]:
        path = item["track"]
        for first, second in zip(path, path[1:]):
            lines.append(
                f"        PPCRemoveTrack(Board, '{item['net']}', {qmm(first[0])}, {qmm(first[1])}, "
                f"{qmm(second[0])}, {qmm(second[1])}, RemovedTracks);\n"
            )
        if item["via"] is not None:
            lines.append(
                f"        PPCRemoveVia(Board, '{item['net']}', {qmm(item['via'][0])}, "
                f"{qmm(item['via'][1])}, RemovedVias);\n"
            )

    lines.extend([
        "        If Created Then\n        Begin\n",
        "            Board.AddPCBObject(PolygonObj);\n",
        "            PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,\n",
        "                                          PCBM_BoardRegisteration, PolygonObj.I_ObjectAddress);\n",
        "        End\n        Else\n            PolygonObj.EndModify;\n",
    ])

    for item in plan["fanouts"]:
        lines.append(
            f"\n        {{ {item['net']} {item['designator']}-{item['pad_name']} }}\n"
        )
        path = item["track"]
        for first, second in zip(path, path[1:]):
            lines.append(
                f"        PPCAddTrack(Board, '{item['net']}', {qmm(first[0])}, {qmm(first[1])}, "
                f"{qmm(second[0])}, {qmm(second[1])}, {qmm(item['track_width_mm'])}, AddedTracks);\n"
            )
        if item["via"] is not None:
            high_layer = layer_name(item["via_layers"][1])
            lines.append(
                f"        PPCAddVia(Board, '{item['net']}', {qmm(item['via'][0])}, "
                f"{qmm(item['via'][1])}, {qmm(item['via_size_mm'])}, "
                f"{qmm(item['via_hole_mm'])}, {high_layer}, AddedVias);\n"
            )

    lines.extend([
        "        PolygonObj.Rebuild;\n",
        "    Finally\n        PCBServer.PostProcess;\n    End;\n",
        "    Board.ViewManager_FullUpdate;\n",
        "    ShowMessage('Power-plane closure applied: ' + IntToStr(AddedTracks) +\n",
        "                ' tracks, ' + IntToStr(AddedVias) + ' vias; removed ' +\n",
        "                IntToStr(RemovedTracks) + ' tracks and ' +\n",
        "                IntToStr(RemovedVias) + ' vias. Repour, save and run full DRC.');\n",
        "End;\n",
    ])

    OUTPUT.write_text("".join(lines), encoding="utf-8")
    print(f"generated {OUTPUT} from {len(plan['fanouts'])} fanouts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
