Function R168V3Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;
Function R168V3FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V3TargetNet(NetObj : IPCB_Net) : Boolean;
Var
    NetName : String;
Begin
    Result := False;
    If NetObj = Nil Then Exit;
    NetName := UpperCase(NetObj.Name);
    Result := (NetName = 'RADAR_12V') Or (NetName = 'U7_DVDT');
End;

Procedure R168V3Count(Board : IPCB_Board;
                      Var RadarTracks, RadarVias, DvdtTracks, DvdtVias : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
    ViaObj   : IPCB_Via;
    NetName  : String;
Begin
    RadarTracks := 0;
    RadarVias := 0;
    DvdtTracks := 0;
    DvdtVias := 0;

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
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V3Remove(Board : IPCB_Board;
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
        If (TrackObj.Component = Nil) And R168V3TargetNet(TrackObj.Net) Then
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
        If R168V3TargetNet(ViaObj.Net) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(RemovedVias);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V3AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V3Coord(X1Text);
    TrackObj.Y1 := R168V3Coord(Y1Text);
    TrackObj.X2 := R168V3Coord(X2Text);
    TrackObj.Y2 := R168V3Coord(Y2Text);
    TrackObj.Width := R168V3Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V3AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                       XText, YText : String; Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V3Coord(XText);
    ViaObj.Y := R168V3Coord(YText);
    ViaObj.Size := R168V3Coord('0.6mm');
    ViaObj.HoleSize := R168V3Coord('0.3mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure ApplyR168RadarRepairV3;
Var
    Board          : IPCB_Board;
    Radar12V       : IPCB_Net;
    U7Dvdt         : IPCB_Net;
    RadarTracks    : Integer;
    RadarVias      : Integer;
    DvdtTracks     : Integer;
    DvdtVias       : Integer;
    RemovedTracks  : Integer;
    RemovedVias    : Integer;
    AddedTracks    : Integer;
    AddedVias      : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 RADAR V3 stopped: activate EVT24_REWORK_R168.PcbDoc.');
        Exit;
    End;

    Radar12V := R168V3FindNet(Board, 'RADAR_12V');
    U7Dvdt := R168V3FindNet(Board, 'U7_DVDT');
    If (Radar12V = Nil) Or (U7Dvdt = Nil) Then
    Begin
        ShowMessage('R168 RADAR V3 stopped: a required net is missing.');
        Exit;
    End;

    R168V3Count(Board, RadarTracks, RadarVias, DvdtTracks, DvdtVias);
    If (RadarTracks <> 8) Or (RadarVias <> 2) Or
       (DvdtTracks <> 4) Or (DvdtVias <> 0) Then
    Begin
        ShowMessage('R168 RADAR V3 stopped: audited counts differ. RADAR tracks=' +
                    IntToStr(RadarTracks) + ', RADAR vias=' + IntToStr(RadarVias) +
                    ', DVDT tracks=' + IntToStr(DvdtTracks) + ', DVDT vias=' +
                    IntToStr(DvdtVias) + '.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    AddedTracks := 0;
    AddedVias := 0;

    PCBServer.PreProcess;
    Try
        R168V3Remove(Board, RemovedTracks, RemovedVias);

        R168V3AddTrack(Board, U7Dvdt,
                       '70.725mm', '13.125mm', '70.725mm', '12.5mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, U7Dvdt,
                       '70.725mm', '12.5mm', '72mm', '12.5mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, U7Dvdt,
                       '72mm', '12.5mm', '72mm', '16.725mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, U7Dvdt,
                       '72mm', '16.725mm', '70mm', '16.725mm',
                       '0.15mm', eTopLayer, AddedTracks);

        R168V3AddTrack(Board, Radar12V,
                       '70.25mm', '14mm', '70.25mm', '15.6mm',
                       '0.3mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, Radar12V,
                       '70.25mm', '15.6mm', '71mm', '15.6mm',
                       '0.3mm', eTopLayer, AddedTracks);
        R168V3AddVia(Board, Radar12V, '71mm', '15.6mm', AddedVias);
        R168V3AddTrack(Board, Radar12V,
                       '71mm', '15.6mm', '73mm', '15.6mm',
                       '0.5mm', eMidLayer2, AddedTracks);
        R168V3AddVia(Board, Radar12V, '73mm', '15.6mm', AddedVias);
        R168V3AddTrack(Board, Radar12V,
                       '73mm', '15.6mm', '73mm', '17.25mm',
                       '1.0mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, Radar12V,
                       '73mm', '17.25mm', '73.75mm', '18mm',
                       '1.0mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, Radar12V,
                       '73.75mm', '18mm', '83.5mm', '18mm',
                       '1.5mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, Radar12V,
                       '83.5mm', '18mm', '85mm', '16.5mm',
                       '1.5mm', eTopLayer, AddedTracks);
        R168V3AddTrack(Board, Radar12V,
                       '85mm', '16.5mm', '85mm', '14mm',
                       '1.5mm', eTopLayer, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 RADAR V3 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', removed vias=' +
                IntToStr(RemovedVias) + ', added tracks=' +
                IntToStr(AddedTracks) + ', added vias=' +
                IntToStr(AddedVias) + '.');
End;
