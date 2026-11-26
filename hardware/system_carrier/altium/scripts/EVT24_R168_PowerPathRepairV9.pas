Function R168V9Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V9Near(A, B : TCoord) : Boolean;
Begin
    Result := Abs(A - B) <= R168V9Coord('0.001mm');
End;

Function R168V9FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V9TrackMatches(TrackObj : IPCB_Track;
                            X1Text, Y1Text, X2Text, Y2Text : String) : Boolean;
Var
    X1, Y1, X2, Y2 : TCoord;
Begin
    X1 := R168V9Coord(X1Text);
    Y1 := R168V9Coord(Y1Text);
    X2 := R168V9Coord(X2Text);
    Y2 := R168V9Coord(Y2Text);
    Result :=
        (R168V9Near(TrackObj.X1, X1) And R168V9Near(TrackObj.Y1, Y1) And
         R168V9Near(TrackObj.X2, X2) And R168V9Near(TrackObj.Y2, Y2)) Or
        (R168V9Near(TrackObj.X1, X2) And R168V9Near(TrackObj.Y1, Y2) And
         R168V9Near(TrackObj.X2, X1) And R168V9Near(TrackObj.Y2, Y1));
End;

Function R168V9ViaMatches(ViaObj : IPCB_Via;
                          XText, YText : String) : Boolean;
Begin
    Result := R168V9Near(ViaObj.X, R168V9Coord(XText)) And
              R168V9Near(ViaObj.Y, R168V9Coord(YText));
End;

Procedure R168V9AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V9Coord(X1Text);
    TrackObj.Y1 := R168V9Coord(Y1Text);
    TrackObj.X2 := R168V9Coord(X2Text);
    TrackObj.Y2 := R168V9Coord(Y2Text);
    TrackObj.Width := R168V9Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V9RemoveTracks(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    NetName   : String;
    RemoveIt  : Boolean;
Begin
    Count := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        RemoveIt := False;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) Then
        Begin
            NetName := UpperCase(TrackObj.Net.Name);
            If NetName = 'VIN_PROTECTED_24V' Then
            Begin
                If (TrackObj.Layer = eTopLayer) And
                   (R168V9TrackMatches(TrackObj,
                                       '29mm', '12.8mm', '29.8mm', '12.8mm') Or
                    R168V9TrackMatches(TrackObj,
                                       '29.8mm', '12.8mm', '30.3mm', '13.3mm') Or
                    R168V9TrackMatches(TrackObj,
                                       '30.3mm', '13.3mm', '30.3mm', '13.5mm') Or
                    R168V9TrackMatches(TrackObj,
                                       '30.3mm', '13.5mm', '32.625mm', '13.5mm')) Then
                    RemoveIt := True;
                If (TrackObj.Layer = eBottomLayer) And
                   R168V9TrackMatches(TrackObj,
                                      '29mm', '12.8mm', '29mm', '15.5mm') Then
                    RemoveIt := True;
            End;

            If (NetName = 'GND') And
               (((TrackObj.Layer = eTopLayer) And
                 R168V9TrackMatches(TrackObj,
                                    '75.775mm', '13.125mm',
                                    '76.7mm', '13.125mm')) Or
                ((TrackObj.Layer = eMidLayer1) And
                 R168V9TrackMatches(TrackObj,
                                    '72mm', '13.8mm',
                                    '76.7mm', '13.125mm'))) Then
                RemoveIt := True;
        End;
        If RemoveIt Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V9RemoveVias(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
    NetName  : String;
    RemoveIt : Boolean;
Begin
    Count := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        RemoveIt := False;
        If ViaObj.Net <> Nil Then
        Begin
            NetName := UpperCase(ViaObj.Net.Name);
            If (NetName = 'GND') And
               R168V9ViaMatches(ViaObj, '76.7mm', '13.125mm') Then
                RemoveIt := True;
        End;
        If RemoveIt Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyR168PowerPathRepairV9;
Var
    Board         : IPCB_Board;
    VinProtected  : IPCB_Net;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
    AddedTracks   : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 power V9 stopped: EVT24_REWORK_R168.PcbDoc is unavailable.');
        Exit;
    End;

    VinProtected := R168V9FindNet(Board, 'VIN_PROTECTED_24V');
    If VinProtected = Nil Then
    Begin
        ShowMessage('R168 power V9 stopped: VIN_PROTECTED_24V is missing.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    AddedTracks := 0;

    PCBServer.PreProcess;
    Try
        R168V9RemoveTracks(Board, RemovedTracks);
        R168V9RemoveVias(Board, RemovedVias);

        R168V9AddTrack(Board, VinProtected,
                       '29mm', '12.8mm', '29.6mm', '13.4mm',
                       '1.00mm', eBottomLayer, AddedTracks);
        R168V9AddTrack(Board, VinProtected,
                       '29.6mm', '13.4mm', '29.6mm', '14.9mm',
                       '1.00mm', eBottomLayer, AddedTracks);
        R168V9AddTrack(Board, VinProtected,
                       '29.6mm', '14.9mm', '29mm', '15.5mm',
                       '1.00mm', eBottomLayer, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 power V9 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', vias=' + IntToStr(RemovedVias) +
                ', added tracks=' + IntToStr(AddedTracks) + '.');
End;
