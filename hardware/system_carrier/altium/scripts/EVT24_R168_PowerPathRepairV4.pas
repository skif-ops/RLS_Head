Function R168V4Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V4FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V4FindComponent(Board : IPCB_Board; DesignatorText : String) : IPCB_Component;
Var
    Iterator : IPCB_BoardIterator;
    CompObj  : IPCB_Component;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    CompObj := Iterator.FirstPCBObject;
    While CompObj <> Nil Do
    Begin
        If UpperCase(CompObj.SourceDesignator) = UpperCase(DesignatorText) Then
        Begin
            Result := CompObj;
            Break;
        End;
        CompObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function R168V4TargetNet(NetObj : IPCB_Net) : Boolean;
Var
    NetName : String;
Begin
    Result := False;
    If NetObj = Nil Then Exit;
    NetName := UpperCase(NetObj.Name);
    Result := (NetName = 'RADAR_12V') Or
              (NetName = 'U7_DVDT') Or
              (NetName = 'U6_IN_BLOCKED');
End;

Procedure R168V4Count(Board : IPCB_Board;
                      Var RadarTracks, RadarVias, DvdtTracks, DvdtVias,
                          BlockedTracks, BlockedVias, BlockedFills : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
    ViaObj   : IPCB_Via;
    FillObj  : IPCB_Fill;
    NetName  : String;
Begin
    RadarTracks := 0;
    RadarVias := 0;
    DvdtTracks := 0;
    DvdtVias := 0;
    BlockedTracks := 0;
    BlockedVias := 0;
    BlockedFills := 0;

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
            If NetName = 'RADAR_12V' Then Inc(RadarTracks);
            If NetName = 'U7_DVDT' Then Inc(DvdtTracks);
            If NetName = 'U6_IN_BLOCKED' Then Inc(BlockedTracks);
        End;
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        If ViaObj.Net <> Nil Then
        Begin
            NetName := UpperCase(ViaObj.Net.Name);
            If NetName = 'RADAR_12V' Then Inc(RadarVias);
            If NetName = 'U7_DVDT' Then Inc(DvdtVias);
            If NetName = 'U6_IN_BLOCKED' Then Inc(BlockedVias);
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eFillObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    FillObj := Iterator.FirstPCBObject;
    While FillObj <> Nil Do
    Begin
        If (FillObj.Component = Nil) And (FillObj.Net <> Nil) And
           (UpperCase(FillObj.Net.Name) = 'U6_IN_BLOCKED') Then
            Inc(BlockedFills);
        FillObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V4RemoveTracksAndVias(Board : IPCB_Board;
                                    Var RemovedTracks, RemovedVias : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    ViaObj    : IPCB_Via;
    NextVia   : IPCB_Via;
Begin
    RemovedTracks := 0;
    RemovedVias := 0;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And R168V4TargetNet(TrackObj.Net) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(RemovedTracks);
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
        If R168V4TargetNet(ViaObj.Net) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(RemovedVias);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V4AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V4Coord(X1Text);
    TrackObj.Y1 := R168V4Coord(Y1Text);
    TrackObj.X2 := R168V4Coord(X2Text);
    TrackObj.Y2 := R168V4Coord(Y2Text);
    TrackObj.Width := R168V4Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V4AddFill(Board : IPCB_Board; NetObj : IPCB_Net;
                        LeftText, BottomText, RightText, TopText : String;
                        LayerId : TLayer; Var Count : Integer);
Var
    FillObj : IPCB_Fill;
Begin
    FillObj := PCBServer.PCBObjectFactory(eFillObject, eNoDimension,
                                          eCreate_Default);
    FillObj.X1Location := R168V4Coord(LeftText);
    FillObj.Y1Location := R168V4Coord(BottomText);
    FillObj.X2Location := R168V4Coord(RightText);
    FillObj.Y2Location := R168V4Coord(TopText);
    FillObj.Rotation := 0;
    FillObj.Layer := LayerId;
    FillObj.Net := NetObj;
    Board.AddPCBObject(FillObj);
    Inc(Count);
End;

Procedure R168V4AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                       XText, YText, SizeText, HoleText : String;
                       Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V4Coord(XText);
    ViaObj.Y := R168V4Coord(YText);
    ViaObj.Size := R168V4Coord(SizeText);
    ViaObj.HoleSize := R168V4Coord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure ApplyR168PowerPathRepairV4;
Var
    Board          : IPCB_Board;
    Radar12V       : IPCB_Net;
    U7Dvdt         : IPCB_Net;
    U6Blocked      : IPCB_Net;
    GndNet         : IPCB_Net;
    C7D            : IPCB_Component;
    RadarTracks    : Integer;
    RadarVias      : Integer;
    DvdtTracks     : Integer;
    DvdtVias       : Integer;
    BlockedTracks  : Integer;
    BlockedVias    : Integer;
    BlockedFills   : Integer;
    RemovedTracks  : Integer;
    RemovedVias    : Integer;
    AddedTracks    : Integer;
    AddedVias      : Integer;
    AddedFills     : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 power V4 stopped: activate EVT24_REWORK_R168.PcbDoc.');
        Exit;
    End;

    Radar12V := R168V4FindNet(Board, 'RADAR_12V');
    U7Dvdt := R168V4FindNet(Board, 'U7_DVDT');
    U6Blocked := R168V4FindNet(Board, 'U6_IN_BLOCKED');
    GndNet := R168V4FindNet(Board, 'GND');
    C7D := R168V4FindComponent(Board, 'C7D');
    If (Radar12V = Nil) Or (U7Dvdt = Nil) Or (U6Blocked = Nil) Or
       (GndNet = Nil) Or (C7D = Nil) Then
    Begin
        ShowMessage('R168 power V4 stopped: a required net or C7D is missing.');
        Exit;
    End;

    R168V4Count(Board, RadarTracks, RadarVias, DvdtTracks, DvdtVias,
                BlockedTracks, BlockedVias, BlockedFills);
    If (RadarTracks <> 8) Or (RadarVias <> 2) Or
       (DvdtTracks <> 4) Or (DvdtVias <> 0) Or
       (BlockedTracks <> 4) Or (BlockedVias <> 0) Or
       (BlockedFills <> 0) Then
    Begin
        ShowMessage('R168 power V4 stopped: audited geometry differs. RADAR=' +
                    IntToStr(RadarTracks) + '/' + IntToStr(RadarVias) +
                    ', DVDT=' + IntToStr(DvdtTracks) + '/' + IntToStr(DvdtVias) +
                    ', U6_IN=' + IntToStr(BlockedTracks) + '/' +
                    IntToStr(BlockedVias) + '/' + IntToStr(BlockedFills) + '.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    AddedTracks := 0;
    AddedVias := 0;
    AddedFills := 0;

    PCBServer.PreProcess;
    Try
        R168V4RemoveTracksAndVias(Board, RemovedTracks, RemovedVias);

        R168V4AddFill(Board, U6Blocked,
                      '18.25mm', '12.65mm', '21.8mm', '15.65mm',
                      eTopLayer, AddedFills);
        R168V4AddFill(Board, U6Blocked,
                      '21.6mm', '14.625mm', '22.625mm', '15.375mm',
                      eTopLayer, AddedFills);

        C7D.X := R168V4Coord('72.5mm');
        C7D.Y := R168V4Coord('13.125mm');
        C7D.Rotation := 0;
        C7D.Name.Rotation := 0;
        C7D.NameAutoPosition := eAutoPos_TopCenter;
        C7D.AutoPosition_NameComment;
        C7D.Selected := False;

        R168V4AddTrack(Board, U7Dvdt,
                       '70.725mm', '13.125mm', '71.725mm', '13.125mm',
                       '0.20mm', eTopLayer, AddedTracks);
        R168V4AddTrack(Board, GndNet,
                       '73.275mm', '13.125mm', '74mm', '13.125mm',
                       '0.30mm', eTopLayer, AddedTracks);
        R168V4AddVia(Board, GndNet, '74mm', '13.125mm',
                     '0.60mm', '0.30mm', AddedVias);

        R168V4AddTrack(Board, Radar12V,
                       '70.25mm', '14mm', '70.25mm', '15.6mm',
                       '0.30mm', eTopLayer, AddedTracks);
        R168V4AddTrack(Board, Radar12V,
                       '70.25mm', '15.6mm', '71mm', '16.35mm',
                       '0.75mm', eTopLayer, AddedTracks);
        R168V4AddTrack(Board, Radar12V,
                       '71mm', '16.35mm', '83.5mm', '16.35mm',
                       '1.50mm', eTopLayer, AddedTracks);
        R168V4AddTrack(Board, Radar12V,
                       '83.5mm', '16.35mm', '85mm', '14.85mm',
                       '1.50mm', eTopLayer, AddedTracks);
        R168V4AddTrack(Board, Radar12V,
                       '85mm', '14.85mm', '85mm', '14mm',
                       '1.50mm', eTopLayer, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 power V4 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', removed vias=' +
                IntToStr(RemovedVias) + ', added tracks=' +
                IntToStr(AddedTracks) + ', added vias=' +
                IntToStr(AddedVias) + ', added fills=' +
                IntToStr(AddedFills) + '.');
End;
