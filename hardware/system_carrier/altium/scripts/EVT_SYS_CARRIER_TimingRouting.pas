{ Route the locked EVT timing signals on the top layer. }

Function EVTTimingCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function IsExpectedTimingBoard(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0) And
        (UpperCase(ExtractFileName(APath)) = 'EVT_SYS_CARRIER.PCBDOC');
End;

Function ResolveTimingBoard : IPCB_Board;
Var
    Board : IPCB_Board;
Begin
    Result := Nil;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If Not IsExpectedTimingBoard(Board.FileName) Then Exit;
    Result := Board;
End;

Function FindTimingNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function ExistingTimingTrackCount(Board : IPCB_Board; NetName : String) : Integer;
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
        If Track.Net <> Nil Then
            If UpperCase(Track.Net.Name) = UpperCase(NetName) Then
                Result := Result + 1;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure AddTimingTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text : String;
                         Var TrackCount : Integer);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := EVTTimingCoord(X1Text);
    Track.Y1 := EVTTimingCoord(Y1Text);
    Track.X2 := EVTTimingCoord(X2Text);
    Track.Y2 := EVTTimingCoord(Y2Text);
    Track.Width := EVTTimingCoord('0.20mm');
    Track.Layer := eTopLayer;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure ApplyEVTTimingRouting;
Var
    Board      : IPCB_Board;
    GnssPpsNet : IPCB_Net;
    ImuDrdyNet : IPCB_Net;
    RadarRefNet: IPCB_Net;
    TrackCount : Integer;
Begin
    Board := ResolveTimingBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT timing routing stopped: select the expected native PcbDoc first.');
        Exit;
    End;

    If (ExistingTimingTrackCount(Board, 'GNSS_PPS') <> 0) Or
       (ExistingTimingTrackCount(Board, 'IMU_DRDY') <> 0) Or
       (ExistingTimingTrackCount(Board, 'RADAR_REF') <> 0) Then
    Begin
        ShowMessage('EVT timing routing stopped: one or more timing nets already have routed tracks.');
        Exit;
    End;

    GnssPpsNet := FindTimingNet(Board, 'GNSS_PPS');
    ImuDrdyNet := FindTimingNet(Board, 'IMU_DRDY');
    RadarRefNet := FindTimingNet(Board, 'RADAR_REF');
    If (GnssPpsNet = Nil) Or (ImuDrdyNet = Nil) Or (RadarRefNet = Nil) Then
    Begin
        ShowMessage('EVT timing routing stopped: a required timing net is missing.');
        Exit;
    End;

    TrackCount := 0;
    PCBServer.PreProcess;

    AddTimingTrack(Board, GnssPpsNet, '29.60mm', '66.80mm', '29.75mm', '66.75mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '29.75mm', '66.75mm', '30.00mm', '66.75mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '30.00mm', '66.75mm', '30.50mm', '67.25mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '30.50mm', '67.25mm', '31.50mm', '67.25mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '31.50mm', '67.25mm', '38.25mm', '60.50mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '38.25mm', '60.50mm', '38.25mm', '31.25mm', TrackCount);
    AddTimingTrack(Board, GnssPpsNet, '38.25mm', '31.25mm', '39.325mm', '31.25mm', TrackCount);

    AddTimingTrack(Board, ImuDrdyNet, '51.00mm', '58.75mm', '51.00mm', '60.00mm', TrackCount);
    AddTimingTrack(Board, ImuDrdyNet, '51.00mm', '60.00mm', '57.25mm', '60.00mm', TrackCount);
    AddTimingTrack(Board, ImuDrdyNet, '57.25mm', '60.00mm', '63.25mm', '54.00mm', TrackCount);
    AddTimingTrack(Board, ImuDrdyNet, '63.25mm', '54.00mm', '63.25mm', '44.75mm', TrackCount);
    AddTimingTrack(Board, ImuDrdyNet, '63.25mm', '44.75mm', '58.75mm', '40.25mm', TrackCount);
    AddTimingTrack(Board, ImuDrdyNet, '58.75mm', '40.25mm', '58.75mm', '27.325mm', TrackCount);

    AddTimingTrack(Board, RadarRefNet, '95.00mm', '33.00mm', '93.75mm', '31.75mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '93.75mm', '31.75mm', '85.25mm', '31.75mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '85.25mm', '31.75mm', '81.25mm', '27.75mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '81.25mm', '27.75mm', '70.50mm', '27.75mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '70.50mm', '27.75mm', '67.00mm', '24.25mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '67.00mm', '24.25mm', '60.25mm', '24.25mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '60.25mm', '24.25mm', '60.25mm', '25.25mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '60.25mm', '25.25mm', '59.25mm', '26.25mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '59.25mm', '26.25mm', '58.25mm', '26.25mm', TrackCount);
    AddTimingTrack(Board, RadarRefNet, '58.25mm', '26.25mm', '58.25mm', '27.325mm', TrackCount);

    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    ShowMessage('EVT timing routing applied: ' + IntToStr(TrackCount) +
                ' top-layer tracks, 0 vias. Save and run DRC.');
End;
