{ Route the locked EVT GNSS_RF corridor on the top layer. }

Function EVTGnssCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function IsExpectedGnssBoard(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0) And
        (UpperCase(ExtractFileName(APath)) = 'EVT_SYS_CARRIER.PCBDOC');
End;

Function ResolveGnssBoard : IPCB_Board;
Var
    Board : IPCB_Board;
Begin
    Result := Nil;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If Not IsExpectedGnssBoard(Board.FileName) Then Exit;
    Result := Board;
End;

Function FindGnssNet(Board : IPCB_Board) : IPCB_Net;
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
        If UpperCase(NetObj.Name) = 'GNSS_RF' Then
        Begin
            Result := NetObj;
            Break;
        End;
        NetObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function ExistingGnssTrackCount(Board : IPCB_Board) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Track    : IPCB_Track;
Begin
    Result := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        If Track.Net <> Nil Then
            If UpperCase(Track.Net.Name) = 'GNSS_RF' Then
                Result := Result + 1;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure AddGnssTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                       X1Text, Y1Text, X2Text, Y2Text : String;
                       Var TrackCount : Integer);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := EVTGnssCoord(X1Text);
    Track.Y1 := EVTGnssCoord(Y1Text);
    Track.X2 := EVTGnssCoord(X2Text);
    Track.Y2 := EVTGnssCoord(Y2Text);
    Track.Width := EVTGnssCoord('0.36mm');
    Track.Layer := eTopLayer;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure ApplyEVTGnssRouting;
Var
    Board      : IPCB_Board;
    GnssNet    : IPCB_Net;
    TrackCount : Integer;
Begin
    Board := ResolveGnssBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT GNSS routing stopped: select the expected native PcbDoc first.');
        Exit;
    End;

    If ExistingGnssTrackCount(Board) <> 0 Then
    Begin
        ShowMessage('EVT GNSS routing stopped: GNSS_RF already has routed tracks.');
        Exit;
    End;

    GnssNet := FindGnssNet(Board);
    If GnssNet = Nil Then
    Begin
        ShowMessage('EVT GNSS routing stopped: GNSS_RF net is missing.');
        Exit;
    End;

    TrackCount := 0;
    PCBServer.PreProcess;
    AddGnssTrack(Board, GnssNet, '3.95mm', '66.00mm', '11.00mm', '66.36mm', TrackCount);
    AddGnssTrack(Board, GnssNet, '11.00mm', '66.36mm', '12.00mm', '66.36mm', TrackCount);
    AddGnssTrack(Board, GnssNet, '12.00mm', '66.36mm', '14.50mm', '63.98mm', TrackCount);
    AddGnssTrack(Board, GnssNet, '14.50mm', '63.98mm', '29.60mm', '56.10mm', TrackCount);
    PCBServer.PostProcess;

    Board.ViewManager_FullUpdate;
    ShowMessage('EVT GNSS routing applied: ' + IntToStr(TrackCount) +
                ' top-layer tracks, 0 vias. Save and run DRC.');
End;
