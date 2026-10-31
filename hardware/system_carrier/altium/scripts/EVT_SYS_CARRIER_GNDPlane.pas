Function IsCanonicalGNDPlaneBoard(Board : IPCB_Board) : Boolean;
Var
    P : String;
Begin
    If Board = Nil Then
    Begin
        Result := False;
        Exit;
    End;
    P := LowerCase(Board.FileName);
    Result := (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (UpperCase(ExtractFileName(Board.FileName)) = 'EVT_SYS_CARRIER.PCBDOC');
End;

Function FindGNDPlaneNet(Board : IPCB_Board) : IPCB_Net;
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
        If UpperCase(NetObj.Name) = 'GND' Then
        Begin
            Result := NetObj;
            Break;
        End;
        NetObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function FindExistingGNDPlane(Board : IPCB_Board) : IPCB_Polygon;
Var
    Iterator : IPCB_BoardIterator;
    PolyObj  : IPCB_Polygon;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePolyObject));
    Iterator.AddFilter_LayerSet(MkSet(eMidLayer1));
    Iterator.AddFilter_Method(eProcessAll);
    PolyObj := Iterator.FirstPCBObject;
    While PolyObj <> Nil Do
    Begin
        If UpperCase(PolyObj.Name) = 'EVT_GND_L2_PLANE' Then
        Begin
            Result := PolyObj;
            Break;
        End;
        PolyObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyEVTGNDPlane;
Var
    Board      : IPCB_Board;
    Ground     : IPCB_Net;
    PolygonObj : IPCB_Polygon;
    I          : Integer;
    Created    : Boolean;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Not IsCanonicalGNDPlaneBoard(Board) Then
    Begin
        ShowMessage('GND plane stopped: activate the canonical native EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    Ground := FindGNDPlaneNet(Board);
    If Ground = Nil Then
    Begin
        ShowMessage('GND plane stopped: GND net not found.');
        Exit;
    End;

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    If Board.BoardOutline.PointCount < 3 Then
    Begin
        ShowMessage('GND plane stopped: board outline is invalid.');
        Exit;
    End;

    PolygonObj := FindExistingGNDPlane(Board);
    Created := PolygonObj = Nil;
    If Created Then
        PolygonObj := PCBServer.PCBObjectFactory(ePolyObject, eNoDimension, eCreate_Default)
    Else
        PolygonObj.BeginModify;
    PolygonObj.Name := 'EVT_GND_L2_PLANE';
    PolygonObj.Layer := eMidLayer1;
    PolygonObj.Net := Ground;
    PolygonObj.PolygonType := eSignalLayerPolygon;
    PolygonObj.PolyHatchStyle := ePolySolid;
    PolygonObj.PourOver := ePolygonPourOver_None;
    PolygonObj.Grid := MMsToCoord(0.25);
    PolygonObj.TrackSize := MMsToCoord(0.25);
    PolygonObj.MinTrack := MMsToCoord(0.20);
    PolygonObj.BorderWidth := MMsToCoord(0.25);
    PolygonObj.ArcApproximation := MMsToCoord(0.05);
    PolygonObj.RemoveDead := False;
    PolygonObj.RemoveIslandsByArea := False;
    PolygonObj.RemoveNarrowNecks := False;
    PolygonObj.PointCount := Board.BoardOutline.PointCount;
    For I := 0 To Board.BoardOutline.PointCount - 1 Do
        PolygonObj.Segments[I] := Board.BoardOutline.Segments[I];

    PCBServer.PreProcess;
    If Created Then
    Begin
        Board.AddPCBObject(PolygonObj);
        PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                      PCBM_BoardRegisteration, PolygonObj.I_ObjectAddress);
    End
    Else
        PolygonObj.EndModify;
    PolygonObj.Rebuild;
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;

    ShowMessage('EVT_GND_L2_PLANE synchronized to the current board outline. Repour all polygons, inspect L2, then save and run DRC.');
End;
