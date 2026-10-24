{ Route the locked EVT Ethernet MDI pairs on the top and bottom signal layers. }

Function EVTEthCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function IsExpectedEthernetBoard(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0) And
        (UpperCase(ExtractFileName(APath)) = 'EVT_SYS_CARRIER.PCBDOC');
End;

Function ResolveEthernetBoard : IPCB_Board;
Var
    Board : IPCB_Board;
Begin
    Result := Nil;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If Not IsExpectedEthernetBoard(Board.FileName) Then Exit;
    Result := Board;
End;
Function FindEthernetNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function ExistingEthernetTrackCount(Board : IPCB_Board) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Track    : IPCB_Track;
    N        : String;
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
        Begin
            N := UpperCase(Track.Net.Name);
            If (N = 'ETH_TXP') Or (N = 'ETH_TXN') Or
               (N = 'ETH_RXP') Or (N = 'ETH_RXN') Then
                Result := Result + 1;
        End;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure AddEthernetTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                           X1Text, Y1Text, X2Text, Y2Text : String;
                           Var TrackCount : Integer);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := EVTEthCoord(X1Text);
    Track.Y1 := EVTEthCoord(Y1Text);
    Track.X2 := EVTEthCoord(X2Text);
    Track.Y2 := EVTEthCoord(Y2Text);
    Track.Width := EVTEthCoord('0.26mm');
    Track.Layer := eTopLayer;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure AddEthernetBottomTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                                 X1Text, Y1Text, X2Text, Y2Text : String;
                                 Var TrackCount : Integer);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := EVTEthCoord(X1Text);
    Track.Y1 := EVTEthCoord(Y1Text);
    Track.X2 := EVTEthCoord(X2Text);
    Track.Y2 := EVTEthCoord(Y2Text);
    Track.Width := EVTEthCoord('0.26mm');
    Track.Layer := eBottomLayer;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure AddEthernetVia(Board : IPCB_Board; NetObj : IPCB_Net;
                         XText, YText : String; Var ViaCount : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := EVTEthCoord(XText);
    ViaObj.Y := EVTEthCoord(YText);
    ViaObj.Size := EVTEthCoord('0.60mm');
    ViaObj.HoleSize := EVTEthCoord('0.30mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    ViaCount := ViaCount + 1;
End;

Procedure ApplyEVTEthernetRouting;
Var
    Board      : IPCB_Board;
    TxP        : IPCB_Net;
    TxN        : IPCB_Net;
    RxP        : IPCB_Net;
    RxN        : IPCB_Net;
    TrackCount : Integer;
    ViaCount   : Integer;
Begin
    Board := ResolveEthernetBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT Ethernet routing stopped: select the expected canonical native PcbDoc first.');
        Exit;
    End;

    If ExistingEthernetTrackCount(Board) <> 0 Then
    Begin
        ShowMessage('EVT Ethernet routing stopped: an MDI net already has routed tracks.');
        Exit;
    End;

    TxP := FindEthernetNet(Board, 'ETH_TXP');
    TxN := FindEthernetNet(Board, 'ETH_TXN');
    RxP := FindEthernetNet(Board, 'ETH_RXP');
    RxN := FindEthernetNet(Board, 'ETH_RXN');
    If (TxP = Nil) Or (TxN = Nil) Or (RxP = Nil) Or (RxN = Nil) Then
    Begin
        ShowMessage('EVT Ethernet routing stopped: an MDI net is missing.');
        Exit;
    End;

    TrackCount := 0;
    ViaCount := 0;
    PCBServer.PreProcess;

    AddEthernetTrack(Board, TxP, '72.25mm', '59.9375mm', '72.25mm', '64.54mm', TrackCount);
    AddEthernetTrack(Board, TxP, '72.25mm', '64.54mm', '72.71mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '72.71mm', '65.00mm', '84.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '84.00mm', '65.00mm', '84.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '84.00mm', '65.9467mm', '85.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '85.00mm', '65.9467mm', '85.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '85.00mm', '65.00mm', '86.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '86.00mm', '65.00mm', '86.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '86.00mm', '65.9467mm', '87.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '87.00mm', '65.9467mm', '87.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '87.00mm', '65.00mm', '88.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '88.00mm', '65.00mm', '88.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '88.00mm', '65.9467mm', '89.00mm', '65.9467mm', TrackCount);
    AddEthernetTrack(Board, TxP, '89.00mm', '65.9467mm', '89.00mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '89.00mm', '65.00mm', '95.20mm', '65.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '95.20mm', '65.00mm', '95.20mm', '61.00mm', TrackCount);
    AddEthernetTrack(Board, TxP, '95.20mm', '61.00mm', '96.00mm', '60.00mm', TrackCount);

    AddEthernetTrack(Board, TxN, '72.75mm', '59.9375mm', '72.75mm', '64.08mm', TrackCount);
    AddEthernetTrack(Board, TxN, '72.75mm', '64.08mm', '73.21mm', '64.54mm', TrackCount);
    AddEthernetTrack(Board, TxN, '73.21mm', '64.54mm', '94.50mm', '64.54mm', TrackCount);
    AddEthernetTrack(Board, TxN, '94.50mm', '64.54mm', '94.50mm', '63.50mm', TrackCount);
    AddEthernetVia(Board, TxN, '94.50mm', '63.50mm', ViaCount);
    AddEthernetBottomTrack(Board, TxN, '94.50mm', '63.50mm', '94.50mm', '58.00mm', TrackCount);
    AddEthernetBottomTrack(Board, TxN, '94.50mm', '58.00mm', '98.54mm', '58.00mm', TrackCount);
    AddEthernetBottomTrack(Board, TxN, '98.54mm', '58.00mm', '98.54mm', '60.00mm', TrackCount);

    AddEthernetTrack(Board, RxP, '71.25mm', '59.9375mm', '71.25mm', '66.54mm', TrackCount);
    AddEthernetTrack(Board, RxP, '71.25mm', '66.54mm', '71.71mm', '67.00mm', TrackCount);
    AddEthernetTrack(Board, RxP, '71.71mm', '67.00mm', '90.00mm', '67.00mm', TrackCount);
    AddEthernetTrack(Board, RxP, '90.00mm', '67.00mm', '90.00mm', '67.3910mm', TrackCount);
    AddEthernetTrack(Board, RxP, '90.00mm', '67.3910mm', '91.00mm', '67.3910mm', TrackCount);
    AddEthernetTrack(Board, RxP, '91.00mm', '67.3910mm', '91.00mm', '67.00mm', TrackCount);
    AddEthernetTrack(Board, RxP, '91.00mm', '67.00mm', '96.50mm', '67.00mm', TrackCount);
    AddEthernetTrack(Board, RxP, '96.50mm', '67.00mm', '96.50mm', '68.00mm', TrackCount);
    AddEthernetVia(Board, RxP, '96.50mm', '68.00mm', ViaCount);
    AddEthernetBottomTrack(Board, RxP, '96.50mm', '68.00mm', '99.81mm', '65.50mm', TrackCount);
    AddEthernetBottomTrack(Board, RxP, '99.81mm', '65.50mm', '99.81mm', '62.54mm', TrackCount);

    AddEthernetTrack(Board, RxN, '71.75mm', '59.9375mm', '71.75mm', '66.08mm', TrackCount);
    AddEthernetTrack(Board, RxN, '71.75mm', '66.08mm', '72.21mm', '66.54mm', TrackCount);
    AddEthernetTrack(Board, RxN, '72.21mm', '66.54mm', '102.35mm', '66.54mm', TrackCount);
    AddEthernetTrack(Board, RxN, '102.35mm', '66.54mm', '102.35mm', '62.54mm', TrackCount);

    AddEthernetTrack(Board, TxN, '81.50mm', '64.54mm', '81.50mm', '60.50mm', TrackCount);
    AddEthernetTrack(Board, TxN, '81.50mm', '60.50mm', '83.615mm', '60.50mm', TrackCount);

    AddEthernetTrack(Board, TxP, '80.50mm', '65.00mm', '80.50mm', '65.75mm', TrackCount);
    AddEthernetVia(Board, TxP, '80.50mm', '65.75mm', ViaCount);
    AddEthernetBottomTrack(Board, TxP, '80.50mm', '65.75mm', '80.50mm', '61.50mm', TrackCount);
    AddEthernetBottomTrack(Board, TxP, '80.50mm', '61.50mm', '82.40mm', '61.50mm', TrackCount);
    AddEthernetVia(Board, TxP, '82.40mm', '61.50mm', ViaCount);
    AddEthernetTrack(Board, TxP, '82.40mm', '61.50mm', '83.615mm', '61.00mm', TrackCount);

    AddEthernetTrack(Board, RxN, '78.50mm', '66.54mm', '78.50mm', '65.79mm', TrackCount);
    AddEthernetVia(Board, RxN, '78.50mm', '65.79mm', ViaCount);
    AddEthernetBottomTrack(Board, RxN, '78.50mm', '65.79mm', '78.50mm', '58.60mm', TrackCount);
    AddEthernetBottomTrack(Board, RxN, '78.50mm', '58.60mm', '81.70mm', '58.60mm', TrackCount);
    AddEthernetVia(Board, RxN, '81.70mm', '58.60mm', ViaCount);
    AddEthernetTrack(Board, RxN, '81.70mm', '58.60mm', '83.615mm', '59.00mm', TrackCount);

    AddEthernetTrack(Board, RxP, '79.50mm', '67.00mm', '79.50mm', '67.75mm', TrackCount);
    AddEthernetVia(Board, RxP, '79.50mm', '67.75mm', ViaCount);
    AddEthernetBottomTrack(Board, RxP, '79.50mm', '67.75mm', '79.50mm', '59.50mm', TrackCount);
    AddEthernetBottomTrack(Board, RxP, '79.50mm', '59.50mm', '82.20mm', '59.50mm', TrackCount);
    AddEthernetVia(Board, RxP, '82.20mm', '59.50mm', ViaCount);
    AddEthernetTrack(Board, RxP, '82.20mm', '59.50mm', '83.615mm', '59.50mm', TrackCount);

    AddEthernetTrack(Board, TxN, '76.00mm', '57.49mm', '77.00mm', '57.49mm', TrackCount);
    AddEthernetTrack(Board, TxN, '77.00mm', '57.49mm', '77.00mm', '64.54mm', TrackCount);

    AddEthernetTrack(Board, TxP, '76.00mm', '55.49mm', '75.00mm', '55.49mm', TrackCount);
    AddEthernetVia(Board, TxP, '75.00mm', '55.49mm', ViaCount);
    AddEthernetBottomTrack(Board, TxP, '75.00mm', '55.49mm', '84.00mm', '55.49mm', TrackCount);
    AddEthernetBottomTrack(Board, TxP, '84.00mm', '55.49mm', '84.00mm', '61.50mm', TrackCount);
    AddEthernetBottomTrack(Board, TxP, '84.00mm', '61.50mm', '82.40mm', '61.50mm', TrackCount);

    AddEthernetTrack(Board, RxP, '76.00mm', '59.49mm', '75.00mm', '59.49mm', TrackCount);
    AddEthernetVia(Board, RxP, '75.00mm', '59.49mm', ViaCount);
    AddEthernetBottomTrack(Board, RxP, '75.00mm', '59.49mm', '75.00mm', '57.80mm', TrackCount);
    AddEthernetBottomTrack(Board, RxP, '75.00mm', '57.80mm', '82.80mm', '57.80mm', TrackCount);
    AddEthernetBottomTrack(Board, RxP, '82.80mm', '57.80mm', '82.80mm', '59.50mm', TrackCount);
    AddEthernetBottomTrack(Board, RxP, '82.80mm', '59.50mm', '82.20mm', '59.50mm', TrackCount);

    AddEthernetTrack(Board, RxN, '76.00mm', '61.49mm', '75.00mm', '61.49mm', TrackCount);
    AddEthernetVia(Board, RxN, '75.00mm', '61.49mm', ViaCount);
    AddEthernetBottomTrack(Board, RxN, '75.00mm', '61.49mm', '78.50mm', '61.49mm', TrackCount);
    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    ShowMessage('EVT Ethernet MDI routing applied: ' + IntToStr(TrackCount) +
                ' tracks, ' + IntToStr(ViaCount) + ' vias. Save and run DRC.');
End;
