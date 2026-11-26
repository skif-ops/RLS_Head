Function R167Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R167FindPad(Board : IPCB_Board;
    DesignatorText, PadNameText : String) : IPCB_Pad;
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
        If (PadObj.Component <> Nil) And
           (UpperCase(PadObj.Component.SourceDesignator) =
            UpperCase(DesignatorText)) And
           (UpperCase(PadObj.Name) = UpperCase(PadNameText)) Then
        Begin
            Result := PadObj;
            Break;
        End;
        PadObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function R167ResolveTarget : IPCB_Board;
Var
    WS        : IWorkspace;
    Project   : IProject;
    PcbDoc    : IServerDocument;
    BoardPath : String;
    I         : Integer;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If Result <> Nil Then
        If UpperCase(ExtractFileName(Result.FileName)) =
            'EVT24_REWORK_R167.PCBDOC' Then Exit;
    Result := Nil;

    WS := GetWorkspace;
    If WS = Nil Then Exit;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Project := WS.DM_Projects(I);
        If Project = Nil Then Continue;
        If UpperCase(ExtractFileName(Project.DM_ProjectFullPath)) <>
            'EVT24_R167_REROUTECAN.PRJSCR' Then Continue;

        BoardPath := ExtractFilePath(Project.DM_ProjectFullPath) +
            'EVT24_REWORK_R167.PcbDoc';
        Result := PCBServer.GetPCBBoardByPath(BoardPath);
        If Result <> Nil Then Exit;

        PcbDoc := Client.OpenDocument('PCB', BoardPath);
        If PcbDoc = Nil Then Exit;
        Client.ShowDocument(PcbDoc);
        Result := PCBServer.GetPCBBoardByPath(BoardPath);
        Exit;
    End;
End;

Procedure R167DeleteNetTracks(Board : IPCB_Board; NetObj : IPCB_Net;
    Var DeletedTracks : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
    NextObj  : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextObj := Iterator.NextPCBObject;
        If TrackObj.Net = NetObj Then
        Begin
            Board.RemovePCBObject(TrackObj);
            DeletedTracks := DeletedTracks + 1;
        End;
        TrackObj := NextObj;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R167DeleteNetVias(Board : IPCB_Board; NetObj : IPCB_Net;
    Var DeletedVias : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextObj  : IPCB_Via;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextObj := Iterator.NextPCBObject;
        If ViaObj.Net = NetObj Then
        Begin
            Board.RemovePCBObject(ViaObj);
            DeletedVias := DeletedVias + 1;
        End;
        ViaObj := NextObj;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R167AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
    LayerKind : TLayer; X1, Y1, X2, Y2 : Double;
    Var AddedTracks : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject,
        eNoDimension, eCreate_Default);
    TrackObj.X1 := MMsToCoord(X1);
    TrackObj.Y1 := MMsToCoord(Y1);
    TrackObj.X2 := MMsToCoord(X2);
    TrackObj.Y2 := MMsToCoord(Y2);
    TrackObj.Width := R167Coord('0.200mm');
    TrackObj.Layer := LayerKind;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    AddedTracks := AddedTracks + 1;
End;

Procedure R167AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
    X, Y : Double; Var AddedVias : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject,
        eNoDimension, eCreate_Default);
    ViaObj.X := MMsToCoord(X);
    ViaObj.Y := MMsToCoord(Y);
    ViaObj.Size := R167Coord('0.500mm');
    ViaObj.HoleSize := R167Coord('0.250mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    AddedVias := AddedVias + 1;
End;

Procedure ApplyR167RerouteCAN;
Var
    Board         : IPCB_Board;
    PadH          : IPCB_Pad;
    PadL          : IPCB_Pad;
    NetH          : IPCB_Net;
    NetL          : IPCB_Net;
    AddedTracks   : Integer;
    AddedVias     : Integer;
    DeletedTracks : Integer;
    DeletedVias   : Integer;
Begin
    Board := R167ResolveTarget;
    If Board = Nil Then
    Begin
        ShowMessage('R167 CAN reroute stopped: activate EVT24_REWORK_R167.PcbDoc.');
        Exit;
    End;

    PadH := R167FindPad(Board, 'U4', '7');
    PadL := R167FindPad(Board, 'U4', '6');
    If (PadH = Nil) Or (PadL = Nil) Or
       (PadH.Net = Nil) Or (PadL.Net = Nil) Or
       (UpperCase(PadH.Net.Name) <> 'RADAR_CANH') Or
       (UpperCase(PadL.Net.Name) <> 'RADAR_CANL') Then
    Begin
        ShowMessage('R167 CAN reroute stopped: U4 CAN nets were not verified.');
        Exit;
    End;

    NetH := PadH.Net;
    NetL := PadL.Net;
    AddedTracks := 0;
    AddedVias := 0;
    DeletedTracks := 0;
    DeletedVias := 0;

    PCBServer.PreProcess;
    Try
        R167DeleteNetTracks(Board, NetH, DeletedTracks);
        R167DeleteNetTracks(Board, NetL, DeletedTracks);
        R167DeleteNetVias(Board, NetH, DeletedVias);
        R167DeleteNetVias(Board, NetL, DeletedVias);

        R167AddVia(Board, NetH, 73.5, 29.5, AddedVias);
        R167AddVia(Board, NetL, 73.5, 28.5, AddedVias);
        R167AddVia(Board, NetH, 76.0, 28.05, AddedVias);
        R167AddVia(Board, NetL, 76.0, 30.75, AddedVias);
        R167AddVia(Board, NetL, 79.0, 30.75, AddedVias);
        R167AddVia(Board, NetH, 88.0, 26.3, AddedVias);
        R167AddVia(Board, NetL, 88.0, 27.0, AddedVias);

        R167AddTrack(Board, NetH, eTopLayer,
            72.4, 29.325, 73.5, 29.5, AddedTracks);
        R167AddTrack(Board, NetL, eTopLayer,
            72.4, 28.675, 73.5, 28.5, AddedTracks);
        R167AddTrack(Board, NetH, eTopLayer,
            75.0625, 28.05, 76.0, 28.05, AddedTracks);
        R167AddTrack(Board, NetL, eTopLayer,
            75.0625, 29.95, 75.5, 29.95, AddedTracks);
        R167AddTrack(Board, NetL, eTopLayer,
            75.5, 29.95, 76.0, 30.75, AddedTracks);
        R167AddTrack(Board, NetH, eTopLayer,
            87.0, 25.675, 88.0, 26.3, AddedTracks);
        R167AddTrack(Board, NetL, eTopLayer,
            87.0, 27.325, 88.0, 27.0, AddedTracks);

        R167AddTrack(Board, NetH, eBottomLayer,
            73.5, 29.5, 73.75, 29.75, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            73.75, 29.75, 74.25, 30.05, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            73.5, 28.5, 72.8, 29.2, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            72.8, 29.2, 72.8, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            72.8, 30.45, 74.25, 30.45, AddedTracks);

        R167AddTrack(Board, NetH, eBottomLayer,
            74.25, 30.05, 76.0, 30.05, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            76.0, 30.05, 79.0, 30.05, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            79.0, 30.05, 85.0, 30.05, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            85.0, 30.05, 86.0, 30.05, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            74.25, 30.45, 76.0, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            76.0, 30.45, 79.0, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            79.0, 30.45, 85.0, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            85.0, 30.45, 86.0, 30.45, AddedTracks);

        R167AddTrack(Board, NetH, eBottomLayer,
            76.0, 28.05, 75.6, 28.45, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            75.6, 28.45, 75.6, 29.65, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            75.6, 29.65, 76.0, 30.05, AddedTracks);
        R167AddTrack(Board, NetL, eMidLayer2,
            79.0, 29.0, 79.0, 30.75, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            76.0, 30.75, 76.0, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            79.0, 30.75, 79.0, 30.45, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            85.0, 29.0, 85.0, 30.05, AddedTracks);

        R167AddTrack(Board, NetH, eBottomLayer,
            86.0, 30.05, 86.4, 30.05, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            86.4, 30.05, 86.4, 26.3, AddedTracks);
        R167AddTrack(Board, NetH, eBottomLayer,
            86.4, 26.3, 88.0, 26.3, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            86.0, 30.45, 86.8, 30.45, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            86.8, 30.45, 86.8, 27.0, AddedTracks);
        R167AddTrack(Board, NetL, eBottomLayer,
            86.8, 27.0, 88.0, 27.0, AddedTracks);

        Board.NewUndo;
        Board.SetState_DocumentHasChanged;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    Client.SendMessage('PCB:Zoom', 'Action=Redraw', 255,
        Client.CurrentView);
    ShowMessage('R167 CAN pair rebuilt. Tracks added: ' +
        IntToStr(AddedTracks) + ', vias added: ' +
        IntToStr(AddedVias) + ', old tracks removed: ' +
        IntToStr(DeletedTracks) + ', old vias removed: ' +
        IntToStr(DeletedVias) + '. Save and run DRC.');
End;
