Function R168V7Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V7Near(A, B : TCoord) : Boolean;
Begin
    Result := Abs(A - B) <= R168V7Coord('0.001mm');
End;

Function R168V7FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V7TrackMatches(TrackObj : IPCB_Track;
                            X1Text, Y1Text, X2Text, Y2Text : String) : Boolean;
Var
    X1, Y1, X2, Y2 : TCoord;
Begin
    X1 := R168V7Coord(X1Text);
    Y1 := R168V7Coord(Y1Text);
    X2 := R168V7Coord(X2Text);
    Y2 := R168V7Coord(Y2Text);
    Result :=
        (R168V7Near(TrackObj.X1, X1) And R168V7Near(TrackObj.Y1, Y1) And
         R168V7Near(TrackObj.X2, X2) And R168V7Near(TrackObj.Y2, Y2)) Or
        (R168V7Near(TrackObj.X1, X2) And R168V7Near(TrackObj.Y1, Y2) And
         R168V7Near(TrackObj.X2, X1) And R168V7Near(TrackObj.Y2, Y1));
End;

Function R168V7ViaMatches(ViaObj : IPCB_Via;
                          XText, YText : String) : Boolean;
Begin
    Result := R168V7Near(ViaObj.X, R168V7Coord(XText)) And
              R168V7Near(ViaObj.Y, R168V7Coord(YText));
End;

Procedure R168V7AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V7Coord(X1Text);
    TrackObj.Y1 := R168V7Coord(Y1Text);
    TrackObj.X2 := R168V7Coord(X2Text);
    TrackObj.Y2 := R168V7Coord(Y2Text);
    TrackObj.Width := R168V7Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V7AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                       XText, YText, SizeText, HoleText : String;
                       Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V7Coord(XText);
    ViaObj.Y := R168V7Coord(YText);
    ViaObj.Size := R168V7Coord(SizeText);
    ViaObj.HoleSize := R168V7Coord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure R168V7RemoveTracks(Board : IPCB_Board; Var Count : Integer);
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
            If (NetName = 'VIN_RAW') And (TrackObj.Layer = eTopLayer) And
               (R168V7TrackMatches(TrackObj,
                                   '21.4mm', '12.1mm', '22.6mm', '12.1mm') Or
                R168V7TrackMatches(TrackObj,
                                   '22.6mm', '12.1mm', '23.0625mm', '13.25mm')) Then
                RemoveIt := True;

            If NetName = 'VIN_PROTECTED_24V' Then
            Begin
                If (TrackObj.Layer = eTopLayer) And
                   (R168V7TrackMatches(TrackObj,
                                       '26.9mm', '17mm', '27.2mm', '17.3mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '28.4mm', '11.8mm', '29mm', '12.8mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '29.1mm', '12.8mm', '30.9mm', '12.8mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '30.9mm', '12.8mm', '31mm', '12.7mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '31mm', '12.7mm', '31.8mm', '13.5mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '31.8mm', '13.5mm', '33.1375mm', '13.5mm')) Then
                    RemoveIt := True;
                If (TrackObj.Layer = eBottomLayer) And
                   (R168V7TrackMatches(TrackObj,
                                       '27.2mm', '17.3mm', '29mm', '15.5mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '27.2mm', '18mm', '29mm', '15.5mm') Or
                    R168V7TrackMatches(TrackObj,
                                       '28.4mm', '11.8mm', '29mm', '12.8mm')) Then
                    RemoveIt := True;
            End;
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

Procedure R168V7RemoveVias(Board : IPCB_Board; Var Count : Integer);
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
            If (NetName = 'VIN_PROTECTED_24V') And
               (R168V7ViaMatches(ViaObj, '27.2mm', '17.3mm') Or
                R168V7ViaMatches(ViaObj, '27.2mm', '18mm') Or
                R168V7ViaMatches(ViaObj, '28.4mm', '11.8mm')) Then
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

Procedure ApplyR168PowerPathRepairV7;
Var
    Board         : IPCB_Board;
    VinRaw        : IPCB_Net;
    VinProtected  : IPCB_Net;
    GndNet        : IPCB_Net;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
    AddedTracks   : Integer;
    AddedVias     : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 power V7 stopped: EVT24_REWORK_R168.PcbDoc is unavailable.');
        Exit;
    End;

    VinRaw := R168V7FindNet(Board, 'VIN_RAW');
    VinProtected := R168V7FindNet(Board, 'VIN_PROTECTED_24V');
    GndNet := R168V7FindNet(Board, 'GND');
    If (VinRaw = Nil) Or (VinProtected = Nil) Or (GndNet = Nil) Then
    Begin
        ShowMessage('R168 power V7 stopped: a required net is missing.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    AddedTracks := 0;
    AddedVias := 0;

    PCBServer.PreProcess;
    Try
        R168V7RemoveTracks(Board, RemovedTracks);
        R168V7RemoveVias(Board, RemovedVias);

        R168V7AddTrack(Board, VinRaw,
                       '21.4mm', '12.1mm', '21.85mm', '12.1mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinRaw,
                       '21.85mm', '12.1mm', '21.85mm', '13.25mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinRaw,
                       '21.85mm', '13.25mm', '23.0625mm', '13.25mm',
                       '0.15mm', eTopLayer, AddedTracks);

        R168V7AddVia(Board, VinProtected,
                     '27.6mm', '17.3mm', '0.60mm', '0.30mm', AddedVias);
        R168V7AddTrack(Board, VinProtected,
                       '26.9mm', '17mm', '27.6mm', '17.3mm',
                       '0.20mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinProtected,
                       '27.6mm', '17.3mm', '29mm', '15.5mm',
                       '1.30mm', eBottomLayer, AddedTracks);

        R168V7AddTrack(Board, VinProtected,
                       '29mm', '12.8mm', '29.8mm', '12.8mm',
                       '0.40mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinProtected,
                       '29.8mm', '12.8mm', '30.3mm', '13.3mm',
                       '0.40mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinProtected,
                       '30.3mm', '13.3mm', '30.3mm', '13.5mm',
                       '0.40mm', eTopLayer, AddedTracks);
        R168V7AddTrack(Board, VinProtected,
                       '30.3mm', '13.5mm', '32.625mm', '13.5mm',
                       '0.80mm', eTopLayer, AddedTracks);

        R168V7AddTrack(Board, GndNet,
                       '72mm', '13.8mm', '72.8mm', '11.8mm',
                       '0.30mm', eMidLayer1, AddedTracks);
        R168V7AddTrack(Board, GndNet,
                       '72mm', '13.8mm', '76.7mm', '13.125mm',
                       '0.30mm', eMidLayer1, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 power V7 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', vias=' + IntToStr(RemovedVias) +
                ', added tracks=' + IntToStr(AddedTracks) + ', vias=' +
                IntToStr(AddedVias) + '.');
End;
