Function R168Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168IsPowerNet(NetObj : IPCB_Net) : Boolean;
Var
    NetName : String;
Begin
    Result := False;
    If NetObj = Nil Then Exit;
    NetName := UpperCase(NetObj.Name);
    Result :=
        (NetName = 'VIN_RAW') Or
        (NetName = 'VIN_PROTECTED_24V') Or
        (NetName = 'V12_SYS') Or
        (NetName = 'RADAR_12V') Or
        (NetName = '5V_GNSS');
End;

Procedure R168CountTargets(Board : IPCB_Board;
                           Var SmallVias, SubFabTracks, RadarTracks, RadarVias : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    TrackObj : IPCB_Track;
    NetName  : String;
Begin
    SmallVias := 0;
    SubFabTracks := 0;
    RadarTracks := 0;
    RadarVias := 0;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        If R168IsPowerNet(ViaObj.Net) Then
        Begin
            NetName := UpperCase(ViaObj.Net.Name);
            If ViaObj.HoleSize < R168Coord('0.3mm') Then Inc(SmallVias);
            If NetName = 'RADAR_12V' Then Inc(RadarVias);
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) Then
        Begin
            NetName := UpperCase(TrackObj.Net.Name);
            If R168IsPowerNet(TrackObj.Net) And
               (TrackObj.Width < R168Coord('0.15mm')) Then
                Inc(SubFabTracks);
            If NetName = 'RADAR_12V' Then Inc(RadarTracks);
        End;
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168RepairPowerViasAndMinimumWidth(Board : IPCB_Board;
                                             Var ViaCount, TrackCount : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    TrackObj : IPCB_Track;
Begin
    ViaCount := 0;
    TrackCount := 0;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        If R168IsPowerNet(ViaObj.Net) And
           (ViaObj.HoleSize < R168Coord('0.3mm')) Then
        Begin
            ViaObj.HoleSize := R168Coord('0.3mm');
            If ViaObj.Size < R168Coord('0.6mm') Then
                ViaObj.Size := R168Coord('0.6mm');
            Inc(ViaCount);
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        If (TrackObj.Component = Nil) And
           R168IsPowerNet(TrackObj.Net) And
           (TrackObj.Width < R168Coord('0.15mm')) Then
        Begin
            TrackObj.Width := R168Coord('0.15mm');
            Inc(TrackCount);
        End;
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168RemoveRadarCopper(Board : IPCB_Board;
                                Var TrackCount, ViaCount : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    ViaObj    : IPCB_Via;
    NextVia   : IPCB_Via;
Begin
    TrackCount := 0;
    ViaCount := 0;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And
           (TrackObj.Net <> Nil) And
           (UpperCase(TrackObj.Net.Name) = 'RADAR_12V') Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(TrackCount);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And
           (UpperCase(ViaObj.Net.Name) = 'RADAR_12V') Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(ViaCount);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                       X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                       LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168Coord(X1Text);
    TrackObj.Y1 := R168Coord(Y1Text);
    TrackObj.X2 := R168Coord(X2Text);
    TrackObj.Y2 := R168Coord(Y2Text);
    TrackObj.Width := R168Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure ApplyR168EngineeringRepair;
Var
    Board             : IPCB_Board;
    Radar12V          : IPCB_Net;
    ExpectedSmallVias : Integer;
    ExpectedSubFab    : Integer;
    ExpectedRadarTrk  : Integer;
    ExpectedRadarVia  : Integer;
    RepairedVias      : Integer;
    RepairedTracks    : Integer;
    RemovedRadarTrk   : Integer;
    RemovedRadarVia   : Integer;
    AddedRadarTrk     : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 repair stopped: activate EVT24_REWORK_R168.PcbDoc.');
        Exit;
    End;

    Radar12V := R168FindNet(Board, 'RADAR_12V');
    If Radar12V = Nil Then
    Begin
        ShowMessage('R168 repair stopped: RADAR_12V is missing.');
        Exit;
    End;

    R168CountTargets(Board, ExpectedSmallVias, ExpectedSubFab,
                     ExpectedRadarTrk, ExpectedRadarVia);
    If (ExpectedSmallVias <> 16) Or
       (ExpectedSubFab <> 3) Or
       (ExpectedRadarTrk <> 7) Or
       (ExpectedRadarVia <> 2) Then
    Begin
        ShowMessage('R168 repair stopped: audited counts differ. Small vias=' +
                    IntToStr(ExpectedSmallVias) + ', sub-fab tracks=' +
                    IntToStr(ExpectedSubFab) + ', RADAR tracks=' +
                    IntToStr(ExpectedRadarTrk) + ', RADAR vias=' +
                    IntToStr(ExpectedRadarVia) + '.');
        Exit;
    End;

    RepairedVias := 0;
    RepairedTracks := 0;
    RemovedRadarTrk := 0;
    RemovedRadarVia := 0;
    AddedRadarTrk := 0;

    PCBServer.PreProcess;
    Try
        R168RepairPowerViasAndMinimumWidth(Board, RepairedVias, RepairedTracks);
        R168RemoveRadarCopper(Board, RemovedRadarTrk, RemovedRadarVia);

        R168AddTrack(Board, Radar12V,
                     '70.25mm', '14mm', '70.25mm', '15.6mm',
                     '0.3mm', eTopLayer, AddedRadarTrk);
        R168AddTrack(Board, Radar12V,
                     '70.25mm', '15.6mm', '72mm', '17.35mm',
                     '0.3mm', eTopLayer, AddedRadarTrk);
        R168AddTrack(Board, Radar12V,
                     '72mm', '17.35mm', '83.5mm', '17.35mm',
                     '1.5mm', eTopLayer, AddedRadarTrk);
        R168AddTrack(Board, Radar12V,
                     '83.5mm', '17.35mm', '85mm', '15.85mm',
                     '1.5mm', eTopLayer, AddedRadarTrk);
        R168AddTrack(Board, Radar12V,
                     '85mm', '15.85mm', '85mm', '14mm',
                     '1.5mm', eTopLayer, AddedRadarTrk);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('R168 repair applied. Repaired vias=' + IntToStr(RepairedVias) +
                ', repaired tracks=' + IntToStr(RepairedTracks) +
                ', removed RADAR tracks=' + IntToStr(RemovedRadarTrk) +
                ', removed RADAR vias=' + IntToStr(RemovedRadarVia) +
                ', added RADAR tracks=' + IntToStr(AddedRadarTrk) + '.');
End;
