Function R168V11Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V11FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V11SamePoint(X1, Y1, X2, Y2 : TCoord) : Boolean;
Begin
    Result := (X1 = X2) And (Y1 = Y2);
End;

Procedure R168V11RemoveDiagonal(Board : IPCB_Board; GndNet : IPCB_Net;
                                Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    Ax, Ay    : TCoord;
    Bx, By    : TCoord;
Begin
    Ax := R168V11Coord('75.775mm');
    Ay := R168V11Coord('13.125mm');
    Bx := R168V11Coord('72.8mm');
    By := R168V11Coord('11.325mm');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Net = GndNet) And
           ((R168V11SamePoint(TrackObj.X1, TrackObj.Y1, Ax, Ay) And
             R168V11SamePoint(TrackObj.X2, TrackObj.Y2, Bx, By)) Or
            (R168V11SamePoint(TrackObj.X1, TrackObj.Y1, Bx, By) And
             R168V11SamePoint(TrackObj.X2, TrackObj.Y2, Ax, Ay))) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V11AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                          X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                          Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V11Coord(X1Text);
    TrackObj.Y1 := R168V11Coord(Y1Text);
    TrackObj.X2 := R168V11Coord(X2Text);
    TrackObj.Y2 := R168V11Coord(Y2Text);
    TrackObj.Width := R168V11Coord(WidthText);
    TrackObj.Layer := eTopLayer;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure ApplyR168ClearanceRepairV11;
Var
    Board         : IPCB_Board;
    GndNet        : IPCB_Net;
    RemovedTracks : Integer;
    AddedTracks   : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 clearance V11 stopped: EVT24_REWORK_R168.PcbDoc is unavailable.');
        Exit;
    End;

    GndNet := R168V11FindNet(Board, 'GND');
    If GndNet = Nil Then
    Begin
        ShowMessage('R168 clearance V11 stopped: GND net is missing.');
        Exit;
    End;

    RemovedTracks := 0;
    AddedTracks := 0;

    PCBServer.PreProcess;
    Try
        R168V11RemoveDiagonal(Board, GndNet, RemovedTracks);
        R168V11AddTrack(Board, GndNet,
                        '72.8mm', '11.325mm', '75.775mm', '11.325mm',
                        '0.30mm', AddedTracks);
        R168V11AddTrack(Board, GndNet,
                        '75.775mm', '11.325mm', '75.775mm', '13.125mm',
                        '0.30mm', AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 clearance V11 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', added tracks=' +
                IntToStr(AddedTracks) + '.');
End;
