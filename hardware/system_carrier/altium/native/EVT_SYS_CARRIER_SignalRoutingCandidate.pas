{ Apply PCB-A10 signal routing to the isolated candidate board. }

Function A10Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function ExpectedA10BoardPath : String;
Var
    Workspace : IWorkspace;
    Project   : IProject;
    I         : Integer;
Begin
    Result := '';
    Workspace := GetWorkspace;
    If Workspace = Nil Then Exit;
    For I := 0 To Workspace.DM_ProjectCount - 1 Do
    Begin
        Project := Workspace.DM_Projects(I);
        If Project = Nil Then Continue;
        If ExtractFileName(Project.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER_SignalRoutingCandidate.PrjScr' Then Continue;
        Result := ExtractFilePath(Project.DM_ProjectFullPath) + 'EVT_SYS_CARRIER_signal_candidate.PcbDoc';
        Exit;
    End;
End;

Function IsExpectedA10Board(APath : String; ExpectedPath : String) : Boolean;
Begin
    Result := (ExpectedPath <> '') And (UpperCase(APath) = UpperCase(ExpectedPath));
End;

Function ResolveA10Board : IPCB_Board;
Var
    Board        : IPCB_Board;
    ExpectedPath : String;
Begin
    ExpectedPath := ExpectedA10BoardPath;
    If ExpectedPath = '' Then
    Begin
        Result := Nil;
        Exit;
    End;
    Result := PCBServer.GetPCBBoardByPath(ExpectedPath);
    If Result <> Nil Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If Not IsExpectedA10Board(Board.FileName, ExpectedPath) Then
    Begin
        Result := Nil;
        Exit;
    End;
    Result := Board;
End;

Function FindA10Net(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function IsA10TargetNet(NetName : String) : Boolean;
Var
    N : String;
Begin
    N := UpperCase(NetName);
    Result := (N = 'MCU_HSE_25M') Or
              (N = 'SWDIO') Or
              (N = 'SWCLK') Or
              (N = 'SWO') Or
              (N = 'DEBUG_RX') Or
              (N = 'DEBUG_TX') Or
              (N = 'ETH_CRS_DV') Or
              (N = 'ETH_50M') Or
              (N = 'ETH_NRST') Or
              (N = 'NetC60_1') Or
              (N = 'RADAR_CANH') Or
              (N = 'RADAR_CANL') Or
              (N = 'ETH_TX_EN') Or
              (N = 'IMU_MOSI') Or
              (N = 'IMU_SCK') Or
              (N = 'ETH_TXD0') Or
              (N = 'ETH_TXD1') Or
              (N = 'IMU_NSS') Or
              (N = 'IMU_MISO') Or
              (N = 'ETH_RXD0') Or
              (N = 'ETH_RXD1') Or
              (N = 'CAN_TX') Or
              (N = 'ETH_MDIO') Or
              (N = 'ETH_MDC') Or
              (N = 'ETH_CT') Or
              (N = 'CAN_RX') Or
              (N = 'NRST') Or
              (N = 'BOOT0');
End;

Function ExistingA10TrackCount(Board : IPCB_Board) : Integer;
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
        If (Track.Net <> Nil) And IsA10TargetNet(Track.Net.Name) Then
            Result := Result + 1;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function FindA10Component(Board : IPCB_Board; DesignatorText : String) : IPCB_Component;
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        If UpperCase(Component.SourceDesignator) = UpperCase(DesignatorText) Then
        Begin
            Result := Component;
            Break;
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure MoveA10Component(Board : IPCB_Board; DesignatorText, XText, YText : String);
Var
    Component : IPCB_Component;
Begin
    Component := FindA10Component(Board, DesignatorText);
    If Component = Nil Then Exit;
    Component.X := A10Coord(XText);
    Component.Y := A10Coord(YText);
End;

Function FindA10Pad(Board : IPCB_Board; DesignatorText, PadNameText : String) : IPCB_Pad;
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
        If PadObj.Component <> Nil Then
        Begin
            If (UpperCase(PadObj.Component.SourceDesignator) = UpperCase(DesignatorText)) And
               (UpperCase(PadObj.Name) = UpperCase(PadNameText)) Then
            Begin
                Result := PadObj;
                Break;
            End;
        End;
        PadObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure SnapA10PadConnections(Board : IPCB_Board; DesignatorText, PadNameText : String);
Var
    PadObj    : IPCB_Pad;
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    ViaObj    : IPCB_Via;
    Tolerance : TCoord;
Begin
    PadObj := FindA10Pad(Board, DesignatorText, PadNameText);
    If (PadObj = Nil) Or (PadObj.Net = Nil) Then Exit;
    Tolerance := A10Coord('0.02mm');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(PadObj.Net.Name)) Then
        Begin
            If (Abs(Track.X1 - PadObj.X) <= Tolerance) And
               (Abs(Track.Y1 - PadObj.Y) <= Tolerance) Then
            Begin
                Track.X1 := PadObj.X;
                Track.Y1 := PadObj.Y;
            End;
            If (Abs(Track.X2 - PadObj.X) <= Tolerance) And
               (Abs(Track.Y2 - PadObj.Y) <= Tolerance) Then
            Begin
                Track.X2 := PadObj.X;
                Track.Y2 := PadObj.Y;
            End;
        End;
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        If (ViaObj.Net <> Nil) And (UpperCase(ViaObj.Net.Name) = UpperCase(PadObj.Net.Name)) And
           (Abs(ViaObj.X - PadObj.X) <= Tolerance) And
           (Abs(ViaObj.Y - PadObj.Y) <= Tolerance) Then
        Begin
            ViaObj.X := PadObj.X;
            ViaObj.Y := PadObj.Y;
        End;
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure AddA10Track(Board : IPCB_Board; NetName, X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                      LayerValue : TLayer; Var TrackCount : Integer);
Var
    Track  : IPCB_Track;
    NetObj : IPCB_Net;
Begin
    NetObj := FindA10Net(Board, NetName);
    If NetObj = Nil Then Exit;
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := A10Coord(X1Text);
    Track.Y1 := A10Coord(Y1Text);
    Track.X2 := A10Coord(X2Text);
    Track.Y2 := A10Coord(Y2Text);
    Track.Width := A10Coord(WidthText);
    Track.Layer := LayerValue;
    Track.Net := NetObj;
    Board.AddPCBObject(Track);
    TrackCount := TrackCount + 1;
End;

Procedure AddA10Via(Board : IPCB_Board; NetName, XText, YText : String; Var ViaCount : Integer);
Var
    ViaObj : IPCB_Via;
    NetObj : IPCB_Net;
Begin
    NetObj := FindA10Net(Board, NetName);
    If NetObj = Nil Then Exit;
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := A10Coord(XText);
    ViaObj.Y := A10Coord(YText);
    ViaObj.Size := A10Coord('0.60mm');
    ViaObj.HoleSize := A10Coord('0.30mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    ViaCount := ViaCount + 1;
End;

Procedure RemoveAllTracksForNet(Board : IPCB_Board; NetName : String; Var RemovedCount : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(NetName)) Then
        Begin
            Board.RemovePCBObject(Track);
            RemovedCount := RemovedCount + 1;
        End;
        Track := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function SameA10Segment(Track : IPCB_Track; X1, Y1, X2, Y2 : TCoord) : Boolean;
Var
    Tolerance : TCoord;
Begin
    Tolerance := A10Coord('0.02mm');
    Result :=
        ((Abs(Track.X1 - X1) <= Tolerance) And (Abs(Track.Y1 - Y1) <= Tolerance) And
         (Abs(Track.X2 - X2) <= Tolerance) And (Abs(Track.Y2 - Y2) <= Tolerance)) Or
        ((Abs(Track.X1 - X2) <= Tolerance) And (Abs(Track.Y1 - Y2) <= Tolerance) And
         (Abs(Track.X2 - X1) <= Tolerance) And (Abs(Track.Y2 - Y1) <= Tolerance));
End;

Procedure RemoveA10Segment(Board : IPCB_Board; NetName, X1Text, Y1Text, X2Text, Y2Text : String;
                           Var RemovedCount : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    Track     : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (Track.Net <> Nil) And (UpperCase(Track.Net.Name) = UpperCase(NetName)) And
           SameA10Segment(Track, A10Coord(X1Text), A10Coord(Y1Text), A10Coord(X2Text), A10Coord(Y2Text)) Then
        Begin
            Board.RemovePCBObject(Track);
            RemovedCount := RemovedCount + 1;
        End;
        Track := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure RemoveA10Via(Board : IPCB_Board; NetName, XText, YText : String; Var RemovedCount : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
    Tolerance: TCoord;
Begin
    Tolerance := A10Coord('0.02mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And (UpperCase(ViaObj.Net.Name) = UpperCase(NetName)) And
           (Abs(ViaObj.X - A10Coord(XText)) <= Tolerance) And
           (Abs(ViaObj.Y - A10Coord(YText)) <= Tolerance) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            RemovedCount := RemovedCount + 1;
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyEVTSignalRoutingCandidate;
Var
    Board         : IPCB_Board;
    TrackCount    : Integer;
    ViaCount      : Integer;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
Begin
    Board := ResolveA10Board;
    If Board = Nil Then
    Begin
        ShowMessage('PCB-A10 stopped: open the isolated signal candidate PcbDoc.');
        Exit;
    End;
    If ExistingA10TrackCount(Board) <> 0 Then
    Begin
        ShowMessage('PCB-A10 stopped: one or more target nets already contain tracks.');
        Exit;
    End;
    If FindA10Net(Board, 'MCU_HSE_25M') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net MCU_HSE_25M.'); Exit; End;
    If FindA10Net(Board, 'SWDIO') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net SWDIO.'); Exit; End;
    If FindA10Net(Board, 'SWCLK') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net SWCLK.'); Exit; End;
    If FindA10Net(Board, 'SWO') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net SWO.'); Exit; End;
    If FindA10Net(Board, 'DEBUG_RX') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net DEBUG_RX.'); Exit; End;
    If FindA10Net(Board, 'DEBUG_TX') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net DEBUG_TX.'); Exit; End;
    If FindA10Net(Board, 'ETH_CRS_DV') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_CRS_DV.'); Exit; End;
    If FindA10Net(Board, 'ETH_50M') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_50M.'); Exit; End;
    If FindA10Net(Board, 'ETH_NRST') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_NRST.'); Exit; End;
    If FindA10Net(Board, 'NetC60_1') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net NetC60_1.'); Exit; End;
    If FindA10Net(Board, 'RADAR_CANH') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net RADAR_CANH.'); Exit; End;
    If FindA10Net(Board, 'RADAR_CANL') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net RADAR_CANL.'); Exit; End;
    If FindA10Net(Board, 'ETH_TX_EN') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_TX_EN.'); Exit; End;
    If FindA10Net(Board, 'IMU_MOSI') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net IMU_MOSI.'); Exit; End;
    If FindA10Net(Board, 'IMU_SCK') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net IMU_SCK.'); Exit; End;
    If FindA10Net(Board, 'ETH_TXD0') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_TXD0.'); Exit; End;
    If FindA10Net(Board, 'ETH_TXD1') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_TXD1.'); Exit; End;
    If FindA10Net(Board, 'IMU_NSS') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net IMU_NSS.'); Exit; End;
    If FindA10Net(Board, 'IMU_MISO') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net IMU_MISO.'); Exit; End;
    If FindA10Net(Board, 'ETH_RXD0') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_RXD0.'); Exit; End;
    If FindA10Net(Board, 'ETH_RXD1') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_RXD1.'); Exit; End;
    If FindA10Net(Board, 'CAN_TX') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net CAN_TX.'); Exit; End;
    If FindA10Net(Board, 'ETH_MDIO') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_MDIO.'); Exit; End;
    If FindA10Net(Board, 'ETH_MDC') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_MDC.'); Exit; End;
    If FindA10Net(Board, 'ETH_CT') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net ETH_CT.'); Exit; End;
    If FindA10Net(Board, 'CAN_RX') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net CAN_RX.'); Exit; End;
    If FindA10Net(Board, 'NRST') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net NRST.'); Exit; End;
    If FindA10Net(Board, 'BOOT0') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net BOOT0.'); Exit; End;
    If FindA10Net(Board, '3V3') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net 3V3.'); Exit; End;
    If FindA10Net(Board, 'GND') = Nil Then Begin ShowMessage('PCB-A10 stopped: missing net GND.'); Exit; End;

    TrackCount := 0; ViaCount := 0; RemovedTracks := 0; RemovedVias := 0;
    PCBServer.PreProcess;
    MoveA10Component(Board, 'C107', '69.499994mm', '30.999989mm');
    MoveA10Component(Board, 'C111', '64.000005mm', '54.499993mm');
    MoveA10Component(Board, 'C113', '47.000004mm', '54.499993mm');
    MoveA10Component(Board, 'C115', '35.750001mm', '37.500001mm');
    MoveA10Component(Board, 'C102', '34.500001mm', '35.000006mm');
    MoveA10Component(Board, 'C64', '67.999987mm', '54.999992mm');
    MoveA10Component(Board, 'C60', '66.49999mm', '57.000013mm');
    MoveA10Component(Board, 'R601', '77.5mm', '55.99999mm');
    MoveA10Component(Board, 'R602', '77.5mm', '58.000011mm');
    MoveA10Component(Board, 'C63', '82.499992mm', '57.000013mm');
    MoveA10Component(Board, 'R605', '77.499988mm', '52.499997mm');

    { Restore 3V3 and GND connections for moved components. }
    { R601-2 to U3-19 }
    AddA10Track(Board, '3V3', '77.5mm', '56.509996mm', '78.2mm', '56.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '78.2mm', '56.6mm', ViaCount);
    AddA10Track(Board, '3V3', '78.2mm', '56.6mm', '74.2mm', '56.6mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, '3V3', '74.2mm', '56.6mm', '74.2mm', '65.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, '3V3', '74.2mm', '65.0mm', '73.6mm', '65.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, '3V3', '73.6mm', '65.0mm', '73.6mm', '61.4mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Via(Board, '3V3', '73.6mm', '61.4mm', ViaCount);
    AddA10Track(Board, '3V3', '73.6mm', '61.4mm', '73.4mm', '61.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '73.4mm', '61.6mm', '73.4mm', '61.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '73.4mm', '61.0mm', '73.2mm', '60.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '73.2mm', '60.8mm', '73.249993mm', '59.937498mm', '0.15mm', eTopLayer, TrackCount);
    { R602-2 to R601-2 }
    AddA10Track(Board, '3V3', '77.5mm', '58.509992mm', '77.5mm', '59.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '77.5mm', '59.4mm', ViaCount);
    AddA10Track(Board, '3V3', '77.5mm', '59.4mm', '76.2mm', '59.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '76.2mm', '59.4mm', '76.2mm', '56.5mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '76.2mm', '56.5mm', '77.5mm', '56.509996mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, '3V3', '77.5mm', '56.509996mm', ViaCount);
    { C60-2 to U3-25 }
    AddA10Via(Board, 'GND', '66.49999mm', '57.774992mm', ViaCount);
    AddA10Track(Board, 'GND', '66.49999mm', '57.774992mm', '71.2mm', '58.8mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'GND', '71.2mm', '58.8mm', ViaCount);
    { C64-2 to U3-25 }
    AddA10Via(Board, 'GND', '67.999987mm', '55.480001mm', ViaCount);
    AddA10Track(Board, 'GND', '67.999987mm', '55.480001mm', '72.0mm', '57.2mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'GND', '72.0mm', '57.2mm', ViaCount);
    { C64-1 to R601-2 }
    AddA10Via(Board, '3V3', '67.999987mm', '54.520008mm', ViaCount);
    AddA10Track(Board, '3V3', '67.999987mm', '54.520008mm', '68.0mm', '51.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, '3V3', '68.0mm', '51.0mm', '78.2mm', '51.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, '3V3', '78.2mm', '51.0mm', '78.2mm', '56.6mm', '0.3mm', eBottomLayer, TrackCount);
    { R605-2 to U3-25 }
    AddA10Via(Board, 'GND', '77.499988mm', '53.324989mm', ViaCount);
    AddA10Track(Board, 'GND', '77.499988mm', '53.324989mm', '79.8mm', '54.2mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'GND', '79.8mm', '54.2mm', '79.8mm', '62.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'GND', '79.8mm', '62.4mm', '72.0mm', '62.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'GND', '72.0mm', '62.4mm', '72.0mm', '58.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'GND', '72.0mm', '58.0mm', ViaCount);
    { C63-2 to U3-25 }
    AddA10Track(Board, 'GND', '82.499992mm', '57.774992mm', '81.4mm', '57.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '81.4mm', '57.0mm', ViaCount);
    AddA10Track(Board, 'GND', '81.4mm', '57.0mm', '79.8mm', '57.0mm', '0.3mm', eMidLayer2, TrackCount);
    { C107-2 to U1-90 }
    AddA10Track(Board, 'GND', '69.499994mm', '31.479998mm', '69.4mm', '32.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '69.4mm', '32.2mm', ViaCount);
    AddA10Track(Board, 'GND', '69.4mm', '32.2mm', '70.2mm', '31.4mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'GND', '70.2mm', '31.4mm', '70.2mm', '28.4mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'GND', '70.2mm', '28.4mm', '66.6mm', '28.4mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'GND', '66.6mm', '28.4mm', ViaCount);
    AddA10Track(Board, 'GND', '66.6mm', '28.4mm', '66.6mm', '29.75mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GND', '66.6mm', '29.75mm', '64.675004mm', '29.750004mm', '0.15mm', eTopLayer, TrackCount);
    { C107-1 to U1-91 }
    AddA10Track(Board, '3V3', '69.499994mm', '30.520005mm', '69.4mm', '29.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '69.4mm', '29.8mm', ViaCount);
    AddA10Track(Board, '3V3', '69.4mm', '29.8mm', '69.4mm', '28.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '69.4mm', '28.0mm', '67.6mm', '28.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '67.6mm', '28.0mm', '67.6mm', '29.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, '3V3', '67.6mm', '29.4mm', ViaCount);
    AddA10Track(Board, '3V3', '67.6mm', '29.4mm', '67.6mm', '30.25mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '67.6mm', '30.25mm', '64.675004mm', '30.250003mm', '0.15mm', eTopLayer, TrackCount);
    { C102-2 to U1-37 }
    AddA10Track(Board, 'GND', '34.500001mm', '35.47999mm', '34.6mm', '36.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '34.6mm', '36.2mm', ViaCount);
    AddA10Track(Board, 'GND', '34.6mm', '36.2mm', '33.8mm', '35.4mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'GND', '33.8mm', '35.4mm', '33.8mm', '32.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'GND', '33.8mm', '32.0mm', '37.0mm', '32.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'GND', '37.0mm', '32.0mm', '37.0mm', '32.75mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'GND', '37.0mm', '32.75mm', ViaCount);
    AddA10Track(Board, 'GND', '37.0mm', '32.75mm', '39.324991mm', '32.749998mm', '0.15mm', eTopLayer, TrackCount);
    { C102-1 to U1-36 }
    AddA10Track(Board, '3V3', '34.500001mm', '34.519997mm', '34.6mm', '33.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '34.6mm', '33.8mm', '35.2mm', '33.2mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '35.2mm', '33.2mm', ViaCount);
    AddA10Track(Board, '3V3', '35.2mm', '33.2mm', '35.2mm', '34.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '35.2mm', '34.0mm', '36.4mm', '34.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '36.4mm', '34.0mm', '36.4mm', '33.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, '3V3', '36.4mm', '33.4mm', ViaCount);
    AddA10Track(Board, '3V3', '36.4mm', '33.4mm', '39.324991mm', '33.249997mm', '0.15mm', eTopLayer, TrackCount);
    { C111-2 to U1-135 }
    AddA10Track(Board, 'GND', '64.000005mm', '54.980002mm', '64.0mm', '55.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '64.0mm', '55.8mm', ViaCount);
    AddA10Track(Board, 'GND', '64.0mm', '55.8mm', '62.4mm', '54.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'GND', '62.4mm', '54.0mm', ViaCount);
    AddA10Track(Board, 'GND', '62.4mm', '54.0mm', '61.75mm', '54.0mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GND', '61.75mm', '54.0mm', '61.749991mm', '52.675003mm', '0.15mm', eTopLayer, TrackCount);
    { C111-1 to U1-136 }
    AddA10Track(Board, '3V3', '64.000005mm', '54.020009mm', '64.0mm', '53.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '64.0mm', '53.2mm', ViaCount);
    AddA10Track(Board, '3V3', '64.0mm', '53.2mm', '64.8mm', '52.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '64.8mm', '52.4mm', '61.25mm', '52.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, '3V3', '61.25mm', '52.4mm', '61.25mm', '55.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, '3V3', '61.25mm', '55.0mm', ViaCount);
    AddA10Track(Board, '3V3', '61.25mm', '55.0mm', '61.249992mm', '52.675003mm', '0.15mm', eTopLayer, TrackCount);
    { C113-2 to U1-158 }
    AddA10Track(Board, 'GND', '47.000004mm', '54.980002mm', '47.8mm', '55.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GND', '47.8mm', '55.4mm', '48.8mm', '56.0mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '48.8mm', '56.0mm', ViaCount);
    AddA10Track(Board, 'GND', '48.8mm', '56.0mm', '49.4mm', '56.0mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'GND', '49.4mm', '56.0mm', '49.4mm', '56.4mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'GND', '49.4mm', '56.4mm', ViaCount);
    AddA10Track(Board, 'GND', '49.4mm', '56.4mm', '50.25mm', '56.4mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GND', '50.25mm', '56.4mm', '50.250014mm', '52.675003mm', '0.15mm', eTopLayer, TrackCount);
    { C113-1 to U1-159 }
    AddA10Track(Board, '3V3', '47.000004mm', '54.020009mm', '48.0mm', '54.02mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '48.0mm', '54.02mm', '48.0mm', '54.6mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Via(Board, '3V3', '48.0mm', '54.6mm', ViaCount);
    AddA10Track(Board, '3V3', '48.0mm', '54.6mm', '48.8mm', '55.0mm', '0.3mm', eBottomLayer, TrackCount);
    AddA10Via(Board, '3V3', '48.8mm', '55.0mm', ViaCount);
    AddA10Track(Board, '3V3', '48.8mm', '55.0mm', '49.75mm', '55.0mm', '0.3mm', eTopLayer, TrackCount);
    AddA10Track(Board, '3V3', '49.75mm', '55.0mm', '49.749989mm', '52.675003mm', '0.15mm', eTopLayer, TrackCount);
    { C115-2 to C102-2 }
    AddA10Track(Board, 'GND', '35.750001mm', '37.98001mm', '35.8mm', '38.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'GND', '35.8mm', '38.8mm', ViaCount);
    AddA10Track(Board, 'GND', '35.8mm', '38.8mm', '34.6mm', '36.2mm', '0.3mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'GND', '34.6mm', '36.2mm', '34.500001mm', '35.47999mm', '0.15mm', eTopLayer, TrackCount);

    RemoveAllTracksForNet(Board, 'GNSS_PPS', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXP', '75.0mm', '55.49mm', '76.0mm', '55.49mm', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXP', '75.0mm', '55.49mm', '84.0mm', '55.49mm', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXP', '82.4mm', '61.5mm', '84.0mm', '61.5mm', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXP', '84.0mm', '55.49mm', '84.0mm', '61.5mm', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXN', '76.0mm', '57.49mm', '77.0mm', '57.49mm', RemovedTracks);
    RemoveA10Segment(Board, 'ETH_TXN', '77.0mm', '57.49mm', '77.0mm', '64.54mm', RemovedTracks);
    RemoveA10Via(Board, 'ETH_TXP', '75.0mm', '55.49mm', RemovedVias);

    AddA10Track(Board, 'GNSS_PPS', '29.6mm', '66.8mm', '29.75mm', '66.75mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '29.75mm', '66.75mm', '30.0mm', '66.75mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '30.0mm', '66.75mm', '30.5mm', '67.25mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '30.5mm', '67.25mm', '31.5mm', '67.25mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '31.5mm', '67.25mm', '34.0mm', '64.75mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '34.0mm', '64.75mm', '34.0mm', '37.3mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '34.0mm', '37.3mm', '33.5mm', '36.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '33.5mm', '36.6mm', '33.5mm', '32.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '33.5mm', '32.0mm', '34.0mm', '31.3mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'GNSS_PPS', '34.0mm', '31.3mm', '39.325mm', '31.25mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXP', '77.5mm', '55.49mm', '79.0mm', '55.49mm', '0.26mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXP', '79.0mm', '55.49mm', '84.0mm', '55.49mm', '0.26mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXP', '84.0mm', '55.49mm', '84.0mm', '61.5mm', '0.26mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXP', '84.0mm', '61.5mm', '82.4mm', '61.5mm', '0.26mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXN', '77.5mm', '57.49mm', '78.5mm', '57.49mm', '0.26mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXN', '78.5mm', '57.49mm', '78.5mm', '64.54mm', '0.26mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_TXP', '79.0mm', '55.49mm', ViaCount);

    { MCU_HSE_25M }
    AddA10Track(Board, 'MCU_HSE_25M', '36.724996mm', '39.075004mm', '36.8mm', '38.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'MCU_HSE_25M', '36.8mm', '38.2mm', '38.2mm', '36.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'MCU_HSE_25M', '38.2mm', '36.8mm', '39.324991mm', '36.74999mm', '0.20mm', eTopLayer, TrackCount);

    { SWDIO }
    AddA10Track(Board, 'SWDIO', '64.675004mm', '46.749995mm', '65.8mm', '46.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '65.8mm', '46.8mm', '66.0mm', '47.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'SWDIO', '66.0mm', '47.0mm', ViaCount);
    AddA10Track(Board, 'SWDIO', '66.0mm', '47.0mm', '62.4mm', '43.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '62.4mm', '43.4mm', '62.4mm', '12.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '62.4mm', '12.0mm', '54.4mm', '4.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '54.4mm', '4.0mm', '48.0mm', '4.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'SWDIO', '48.0mm', '4.0mm', ViaCount);
    AddA10Track(Board, 'SWDIO', '48.0mm', '4.0mm', '47.6mm', '4.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '47.6mm', '4.0mm', '47.5mm', '3.73mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWDIO', '47.5mm', '3.73mm', '49.365002mm', '3.72999mm', '0.15mm', eTopLayer, TrackCount);

    { SWCLK }
    AddA10Track(Board, 'SWCLK', '60.749993mm', '52.675003mm', '60.8mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWCLK', '60.8mm', '53.8mm', '60.6mm', '54.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWCLK', '60.6mm', '54.0mm', '60.4mm', '54.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'SWCLK', '60.4mm', '54.0mm', ViaCount);
    AddA10Track(Board, 'SWCLK', '60.4mm', '54.0mm', '60.4mm', '45.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWCLK', '60.4mm', '45.2mm', '80.4mm', '25.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWCLK', '80.4mm', '25.2mm', '80.4mm', '23.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWCLK', '80.4mm', '23.2mm', '62.4mm', '5.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWCLK', '62.4mm', '5.2mm', '47.6mm', '5.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'SWCLK', '47.6mm', '5.2mm', ViaCount);
    AddA10Track(Board, 'SWCLK', '47.6mm', '5.2mm', '47.5mm', '5.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWCLK', '47.5mm', '5.0mm', '49.365002mm', '4.99999mm', '0.15mm', eTopLayer, TrackCount);

    { SWO }
    AddA10Track(Board, 'SWO', '48.749991mm', '52.675003mm', '48.8mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWO', '48.8mm', '53.8mm', '48.8mm', '54.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'SWO', '48.8mm', '54.0mm', ViaCount);
    AddA10Track(Board, 'SWO', '48.8mm', '54.0mm', '24.4mm', '29.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWO', '24.4mm', '29.6mm', '24.4mm', '18.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWO', '24.4mm', '18.6mm', '36.8mm', '6.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'SWO', '36.8mm', '6.2mm', '47.0mm', '6.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'SWO', '47.0mm', '6.2mm', ViaCount);
    AddA10Track(Board, 'SWO', '47.0mm', '6.2mm', '47.4mm', '6.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWO', '47.4mm', '6.2mm', '47.5mm', '6.27mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'SWO', '47.5mm', '6.27mm', '49.365002mm', '6.26999mm', '0.15mm', eTopLayer, TrackCount);

    { DEBUG_RX }
    AddA10Track(Board, 'DEBUG_RX', '54.250006mm', '52.675003mm', '54.25mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_RX', '54.25mm', '53.75mm', '54.0mm', '54.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'DEBUG_RX', '54.0mm', '54.0mm', ViaCount);
    AddA10Track(Board, 'DEBUG_RX', '54.0mm', '54.0mm', '54.0mm', '26.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'DEBUG_RX', '54.0mm', '26.0mm', ViaCount);
    AddA10Track(Board, 'DEBUG_RX', '54.0mm', '26.0mm', '54.0mm', '12.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_RX', '54.0mm', '12.4mm', '60.0mm', '6.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_RX', '60.0mm', '6.4mm', '60.000007mm', '5.499989mm', '0.20mm', eTopLayer, TrackCount);

    { DEBUG_TX }
    AddA10Track(Board, 'DEBUG_TX', '55.750003mm', '52.675003mm', '55.75mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '55.75mm', '53.75mm', '56.25mm', '54.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '56.25mm', '54.25mm', '56.0mm', '54.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'DEBUG_TX', '56.0mm', '54.4mm', ViaCount);
    AddA10Track(Board, 'DEBUG_TX', '56.0mm', '54.4mm', '55.8mm', '54.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '55.8mm', '54.6mm', '53.6mm', '54.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '53.6mm', '54.6mm', '50.2mm', '51.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '50.2mm', '51.2mm', '50.2mm', '26.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'DEBUG_TX', '50.2mm', '26.0mm', ViaCount);
    AddA10Track(Board, 'DEBUG_TX', '50.2mm', '26.0mm', '50.2mm', '13.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '50.2mm', '13.2mm', '57.0mm', '6.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'DEBUG_TX', '57.0mm', '6.4mm', '57.000013mm', '5.499989mm', '0.20mm', eTopLayer, TrackCount);

    { ETH_CRS_DV }
    AddA10Track(Board, 'ETH_CRS_DV', '45.249998mm', '27.32499mm', '45.25mm', '26.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '45.25mm', '26.2mm', '44.2mm', '26.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '44.2mm', '26.2mm', '44.2mm', '25.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '44.2mm', '25.4mm', '44.4mm', '25.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '44.4mm', '25.4mm', '44.4mm', '25.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_CRS_DV', '44.4mm', '25.8mm', ViaCount);
    AddA10Track(Board, 'ETH_CRS_DV', '44.4mm', '25.8mm', '44.4mm', '32.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '44.4mm', '32.6mm', '67.4mm', '55.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '67.4mm', '55.6mm', '67.4mm', '55.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '67.4mm', '55.8mm', '67.8mm', '56.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '67.8mm', '56.2mm', '70.4mm', '56.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '70.4mm', '56.2mm', '73.2mm', '53.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_CRS_DV', '73.2mm', '53.4mm', ViaCount);
    AddA10Track(Board, 'ETH_CRS_DV', '73.2mm', '53.4mm', '73.4mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '73.4mm', '53.6mm', '72.9mm', '54.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '72.9mm', '54.4mm', '72.9mm', '55.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CRS_DV', '72.9mm', '55.2mm', '72.749994mm', '56.062499mm', '0.15mm', eTopLayer, TrackCount);

    { ETH_50M }
    AddA10Track(Board, 'ETH_50M', '67.92501mm', '50.724994mm', '67.93mm', '51.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '67.93mm', '51.6mm', '75.0mm', '51.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '75.0mm', '51.6mm', '75.0mm', '52.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_50M', '75.0mm', '52.6mm', ViaCount);
    AddA10Track(Board, 'ETH_50M', '75.0mm', '52.6mm', '70.8mm', '56.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '70.8mm', '56.8mm', '66.2mm', '56.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '66.2mm', '56.8mm', '40.0mm', '30.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '40.0mm', '30.6mm', '37.4mm', '30.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_50M', '37.4mm', '30.6mm', ViaCount);
    AddA10Track(Board, 'ETH_50M', '37.4mm', '30.6mm', '36.8mm', '30.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '36.8mm', '30.6mm', '36.8mm', '30.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '36.8mm', '30.4mm', '37.8mm', '30.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '37.8mm', '30.4mm', '38.6mm', '30.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '38.6mm', '30.75mm', '39.324991mm', '30.750002mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '70.062496mm', '57.25mm', '69.2mm', '57.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_50M', '69.2mm', '57.2mm', '69.0mm', '57.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_50M', '69.0mm', '57.2mm', ViaCount);
    AddA10Track(Board, 'ETH_50M', '69.0mm', '57.2mm', '70.8mm', '56.8mm', '0.20mm', eBottomLayer, TrackCount);

    { ETH_NRST }
    AddA10Track(Board, 'ETH_NRST', '77.499988mm', '51.675005mm', '77.4mm', '50.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '77.4mm', '50.8mm', '76.4mm', '50.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '76.4mm', '50.8mm', '76.4mm', '56.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '76.4mm', '56.4mm', '75.6mm', '57.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '75.6mm', '57.2mm', '75.0mm', '57.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '75.0mm', '57.2mm', '74.65mm', '57.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '74.65mm', '57.75mm', '73.937495mm', '57.749999mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '39.324991mm', '49.749989mm', '38.2mm', '49.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '38.2mm', '49.8mm', '38.2mm', '53.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '38.2mm', '53.2mm', '47.8mm', '62.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '47.8mm', '62.8mm', '58.4mm', '62.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '58.4mm', '62.8mm', '68.8mm', '52.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '68.8mm', '52.4mm', '73.8mm', '52.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '73.8mm', '52.4mm', '74.6mm', '53.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '74.6mm', '53.2mm', '75.4mm', '53.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '75.4mm', '53.2mm', '76.4mm', '52.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_NRST', '76.4mm', '52.2mm', '76.4mm', '50.8mm', '0.20mm', eTopLayer, TrackCount);

    { NetC60_1 }
    AddA10Track(Board, 'NetC60_1', '70.062496mm', '56.750001mm', '69.4mm', '56.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NetC60_1', '69.4mm', '56.4mm', '68.4mm', '56.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NetC60_1', '68.4mm', '56.4mm', '68.2mm', '56.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NetC60_1', '68.2mm', '56.2mm', '67.4mm', '56.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NetC60_1', '67.4mm', '56.2mm', '66.49999mm', '56.225008mm', '0.15mm', eTopLayer, TrackCount);

    { RADAR_CANH }
    AddA10Track(Board, 'RADAR_CANH', '86.06249mm', '30.950002mm', '87.2mm', '31.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '87.2mm', '31.0mm', '90.4mm', '31.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '90.4mm', '31.0mm', '90.6mm', '31.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '90.6mm', '31.2mm', '95.4mm', '31.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '95.4mm', '31.2mm', '96.2mm', '32.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '96.2mm', '32.0mm', '96.2mm', '34.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '96.2mm', '34.2mm', '85.8mm', '34.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '85.8mm', '34.2mm', '82.0mm', '30.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '82.0mm', '30.4mm', '81.39999mm', '30.325009mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '89.0mm', '29.999991mm', '90.2mm', '30.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '90.2mm', '30.0mm', '90.4mm', '30.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '90.4mm', '30.2mm', '90.4mm', '31.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '87.000004mm', '25.675006mm', '87.0mm', '24.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '87.0mm', '24.8mm', '87.2mm', '24.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '87.2mm', '24.6mm', '87.4mm', '24.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '87.4mm', '24.6mm', '88.0mm', '25.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '88.0mm', '25.2mm', '88.0mm', '25.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '88.0mm', '25.4mm', '90.2mm', '27.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANH', '90.2mm', '27.6mm', '90.2mm', '30.0mm', '0.20mm', eTopLayer, TrackCount);

    { RADAR_CANL }
    AddA10Track(Board, 'RADAR_CANL', '86.06249mm', '29.050005mm', '87.2mm', '29.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.2mm', '29.0mm', '87.2mm', '27.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.2mm', '27.6mm', '88.0mm', '27.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '88.0mm', '27.6mm', '88.0mm', '27.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '88.0mm', '27.8mm', '87.4mm', '28.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.4mm', '28.4mm', '83.4mm', '28.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'RADAR_CANL', '83.4mm', '28.4mm', ViaCount);
    AddA10Track(Board, 'RADAR_CANL', '83.4mm', '28.4mm', '82.2mm', '29.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'RADAR_CANL', '82.2mm', '29.6mm', ViaCount);
    AddA10Track(Board, 'RADAR_CANL', '82.2mm', '29.6mm', '82.0mm', '29.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '82.0mm', '29.6mm', '81.39999mm', '29.674998mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '94.999988mm', '29.999991mm', '96.2mm', '30.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '96.2mm', '30.0mm', '96.4mm', '29.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '96.4mm', '29.8mm', '96.4mm', '26.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '96.4mm', '26.6mm', '93.6mm', '23.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '93.6mm', '23.8mm', '87.4mm', '23.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.4mm', '23.8mm', '86.2mm', '25.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '86.2mm', '25.0mm', '86.2mm', '28.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '86.2mm', '28.2mm', '87.6mm', '28.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.6mm', '28.2mm', '88.0mm', '27.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.000004mm', '27.32499mm', '87.0mm', '28.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.0mm', '28.2mm', '87.2mm', '28.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.2mm', '28.4mm', '87.4mm', '28.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '87.4mm', '28.4mm', '88.0mm', '27.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'RADAR_CANL', '88.0mm', '27.8mm', '88.0mm', '27.6mm', '0.20mm', eTopLayer, TrackCount);

    { ETH_TX_EN }
    AddA10Track(Board, 'ETH_TX_EN', '52.25001mm', '52.675003mm', '52.25mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '52.25mm', '53.75mm', '53.0mm', '54.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '53.0mm', '54.2mm', '53.2mm', '54.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '53.2mm', '54.2mm', '53.2mm', '54.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '53.2mm', '54.4mm', '54.4mm', '55.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '54.4mm', '55.6mm', '60.6mm', '55.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_TX_EN', '60.6mm', '55.6mm', ViaCount);
    AddA10Track(Board, 'ETH_TX_EN', '60.6mm', '55.6mm', '63.4mm', '58.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '63.4mm', '58.4mm', '69.8mm', '58.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '69.8mm', '58.4mm', '73.6mm', '54.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '73.6mm', '54.6mm', '77.0mm', '54.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_TX_EN', '77.0mm', '54.6mm', ViaCount);
    AddA10Track(Board, 'ETH_TX_EN', '77.0mm', '54.6mm', '76.8mm', '54.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '76.8mm', '54.8mm', '76.8mm', '57.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '76.8mm', '57.2mm', '76.4mm', '57.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '76.4mm', '57.6mm', '75.5mm', '57.9mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '75.5mm', '57.9mm', '74.65mm', '58.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TX_EN', '74.65mm', '58.25mm', '73.937495mm', '58.249998mm', '0.15mm', eTopLayer, TrackCount);

    { IMU_MOSI }
    AddA10Track(Board, 'IMU_MOSI', '64.675004mm', '32.249999mm', '66.0mm', '32.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '66.0mm', '32.25mm', '67.6mm', '32.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '67.6mm', '32.8mm', '67.6mm', '33.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'IMU_MOSI', '67.6mm', '33.2mm', ViaCount);
    AddA10Track(Board, 'IMU_MOSI', '67.6mm', '33.2mm', '84.6mm', '50.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '84.6mm', '50.2mm', '84.6mm', '62.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '84.6mm', '62.6mm', '86.6mm', '64.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '86.6mm', '64.6mm', '86.6mm', '68.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '86.6mm', '68.2mm', '86.4mm', '68.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '86.4mm', '68.4mm', '62.8mm', '68.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '62.8mm', '68.4mm', '50.8mm', '56.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '50.8mm', '56.4mm', '51.0mm', '56.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'IMU_MOSI', '51.0mm', '56.2mm', ViaCount);
    AddA10Track(Board, 'IMU_MOSI', '51.0mm', '56.2mm', '51.0mm', '56.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MOSI', '51.0mm', '56.6mm', '51.499999mm', '56.737504mm', '0.20mm', eTopLayer, TrackCount);

    { IMU_SCK }
    AddA10Track(Board, 'IMU_SCK', '64.675004mm', '31.250001mm', '66.0mm', '31.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '66.0mm', '31.25mm', '68.0mm', '31.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '68.0mm', '31.25mm', '68.0mm', '31.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'IMU_SCK', '68.0mm', '31.6mm', ViaCount);
    AddA10Track(Board, 'IMU_SCK', '68.0mm', '31.6mm', '59.8mm', '39.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '59.8mm', '39.8mm', '59.8mm', '51.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '59.8mm', '51.6mm', '55.8mm', '55.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '55.8mm', '55.6mm', '52.6mm', '55.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'IMU_SCK', '52.6mm', '55.6mm', ViaCount);
    AddA10Track(Board, 'IMU_SCK', '52.6mm', '55.6mm', '52.2mm', '55.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '52.2mm', '55.6mm', '52.0mm', '55.5mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_SCK', '52.0mm', '55.5mm', '51.999998mm', '56.737504mm', '0.20mm', eTopLayer, TrackCount);

    { ETH_TXD0 }
    AddA10Track(Board, 'ETH_TXD0', '51.249986mm', '52.675003mm', '51.25mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '51.25mm', '53.75mm', '52.0mm', '54.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '52.0mm', '54.2mm', '52.2mm', '54.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_TXD0', '52.2mm', '54.8mm', ViaCount);
    AddA10Track(Board, 'ETH_TXD0', '52.2mm', '54.8mm', '52.0mm', '55.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '52.0mm', '55.0mm', '52.0mm', '56.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '52.0mm', '56.0mm', '52.2mm', '56.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '52.2mm', '56.2mm', '62.6mm', '56.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '62.6mm', '56.2mm', '65.0mm', '53.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '65.0mm', '53.8mm', '70.2mm', '53.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '70.2mm', '53.8mm', '75.65mm', '59.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '75.65mm', '59.2mm', '75.65mm', '59.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '75.65mm', '59.8mm', '76.4mm', '60.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '76.4mm', '60.4mm', '77.2mm', '60.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_TXD0', '77.2mm', '60.4mm', ViaCount);
    AddA10Track(Board, 'ETH_TXD0', '77.2mm', '60.4mm', '77.2mm', '60.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '77.2mm', '60.2mm', '76.8mm', '60.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '76.8mm', '60.0mm', '76.8mm', '59.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '76.8mm', '59.0mm', '76.2mm', '58.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '76.2mm', '58.4mm', '75.4mm', '58.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '75.4mm', '58.6mm', '74.65mm', '58.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD0', '74.65mm', '58.75mm', '73.937495mm', '58.749997mm', '0.15mm', eTopLayer, TrackCount);

    { ETH_TXD1 }
    AddA10Track(Board, 'ETH_TXD1', '50.750013mm', '52.675003mm', '50.75mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '50.75mm', '53.75mm', '50.75mm', '54.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '50.75mm', '54.4mm', '51.2mm', '55.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '51.2mm', '55.0mm', '51.2mm', '55.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_TXD1', '51.2mm', '55.2mm', ViaCount);
    AddA10Track(Board, 'ETH_TXD1', '51.2mm', '55.2mm', '61.6mm', '65.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '61.6mm', '65.6mm', '74.4mm', '65.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '74.4mm', '65.6mm', '75.0mm', '65.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '75.0mm', '65.0mm', '75.0mm', '63.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_TXD1', '75.0mm', '63.4mm', ViaCount);
    AddA10Track(Board, 'ETH_TXD1', '75.0mm', '63.4mm', '75.0mm', '63.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '75.0mm', '63.0mm', '74.4mm', '62.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '74.4mm', '62.4mm', '74.4mm', '59.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_TXD1', '74.4mm', '59.25mm', '73.937495mm', '59.249996mm', '0.15mm', eTopLayer, TrackCount);

    { IMU_NSS }
    AddA10Track(Board, 'IMU_NSS', '64.675004mm', '30.750002mm', '66.0mm', '30.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_NSS', '66.0mm', '30.75mm', '68.6mm', '30.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'IMU_NSS', '68.6mm', '30.75mm', ViaCount);
    AddA10Track(Board, 'IMU_NSS', '68.6mm', '30.8mm', '67.8mm', '30.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_NSS', '67.8mm', '30.8mm', '54.6mm', '44.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_NSS', '54.6mm', '44.0mm', '54.6mm', '51.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'IMU_NSS', '54.6mm', '51.4mm', ViaCount);
    AddA10Track(Board, 'IMU_NSS', '54.6mm', '51.4mm', '54.6mm', '56.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'IMU_NSS', '54.6mm', '56.8mm', ViaCount);
    AddA10Track(Board, 'IMU_NSS', '54.6mm', '56.8mm', '54.4mm', '56.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_NSS', '54.4mm', '56.6mm', '53.0mm', '56.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_NSS', '53.0mm', '56.2mm', '52.499997mm', '56.737504mm', '0.15mm', eTopLayer, TrackCount);

    { IMU_MISO }
    AddA10Track(Board, 'IMU_MISO', '64.675004mm', '31.75mm', '66.0mm', '31.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '66.0mm', '31.75mm', '66.8mm', '31.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '66.8mm', '31.8mm', '67.2mm', '31.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '67.2mm', '31.8mm', '68.4mm', '33.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '68.4mm', '33.0mm', '68.4mm', '33.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '68.4mm', '33.4mm', '68.0mm', '33.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '68.0mm', '33.8mm', '67.6mm', '33.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '67.6mm', '33.8mm', '67.6mm', '36.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '67.6mm', '36.8mm', '66.0mm', '38.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'IMU_MISO', '66.0mm', '38.4mm', ViaCount);
    AddA10Track(Board, 'IMU_MISO', '66.0mm', '38.4mm', '60.4mm', '44.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'IMU_MISO', '60.4mm', '44.0mm', ViaCount);
    AddA10Track(Board, 'IMU_MISO', '60.4mm', '44.0mm', '59.2mm', '45.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'IMU_MISO', '59.2mm', '45.2mm', ViaCount);
    AddA10Track(Board, 'IMU_MISO', '59.2mm', '45.2mm', '55.2mm', '49.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '55.2mm', '49.2mm', '55.2mm', '49.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'IMU_MISO', '55.2mm', '49.8mm', ViaCount);
    AddA10Track(Board, 'IMU_MISO', '55.2mm', '49.8mm', '50.4mm', '54.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '50.4mm', '54.6mm', '50.4mm', '55.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '50.4mm', '55.4mm', '50.4mm', '57.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '50.4mm', '57.2mm', '47.8mm', '57.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '47.8mm', '57.2mm', '47.8mm', '56.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'IMU_MISO', '47.8mm', '56.4mm', ViaCount);
    AddA10Track(Board, 'IMU_MISO', '47.8mm', '56.4mm', '47.8mm', '57.25mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'IMU_MISO', '47.8mm', '57.25mm', '50.987503mm', '57.25mm', '0.20mm', eTopLayer, TrackCount);

    { ETH_RXD0 }
    AddA10Track(Board, 'ETH_RXD0', '45.749997mm', '27.32499mm', '45.75mm', '26.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '45.75mm', '26.2mm', '45.2mm', '25.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '45.2mm', '25.6mm', '45.2mm', '24.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '45.2mm', '24.8mm', '44.6mm', '24.8mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '44.6mm', '24.8mm', '44.6mm', '23.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '44.6mm', '23.0mm', '42.0mm', '23.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '42.0mm', '23.0mm', '42.0mm', '25.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_RXD0', '42.0mm', '25.6mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD0', '42.0mm', '25.6mm', '42.6mm', '25.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '42.6mm', '25.0mm', '44.6mm', '25.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '44.6mm', '25.0mm', '62.0mm', '42.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '62.0mm', '42.4mm', '62.0mm', '44.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_RXD0', '62.0mm', '44.6mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD0', '62.0mm', '44.6mm', '70.6mm', '53.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_RXD0', '70.6mm', '53.2mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD0', '70.6mm', '53.2mm', '71.0mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '71.0mm', '53.6mm', '71.0mm', '54.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '71.0mm', '54.6mm', '71.25mm', '55.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD0', '71.25mm', '55.2mm', '71.249997mm', '56.062499mm', '0.15mm', eTopLayer, TrackCount);

    { ETH_RXD1 }
    AddA10Track(Board, 'ETH_RXD1', '46.249996mm', '27.32499mm', '46.25mm', '26.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '46.25mm', '26.2mm', '46.8mm', '25.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '46.8mm', '25.6mm', '47.4mm', '25.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '47.4mm', '25.6mm', '47.8mm', '26.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_RXD1', '47.8mm', '26.0mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD1', '47.8mm', '26.0mm', '47.8mm', '30.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '47.8mm', '30.4mm', '49.6mm', '32.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_RXD1', '49.6mm', '32.2mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD1', '49.6mm', '32.2mm', '61.2mm', '43.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '61.2mm', '43.8mm', '61.2mm', '45.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_RXD1', '61.2mm', '45.4mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD1', '61.2mm', '45.4mm', '69.0mm', '53.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_RXD1', '69.0mm', '53.2mm', ViaCount);
    AddA10Track(Board, 'ETH_RXD1', '69.0mm', '53.2mm', '69.0mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '69.0mm', '53.6mm', '70.2mm', '54.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '70.2mm', '54.6mm', '70.75mm', '55.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_RXD1', '70.75mm', '55.2mm', '70.749998mm', '56.062499mm', '0.15mm', eTopLayer, TrackCount);

    { CAN_TX }
    AddA10Track(Board, 'CAN_TX', '57.749999mm', '52.675003mm', '57.75mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '57.75mm', '53.75mm', '57.0mm', '54.5mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '57.0mm', '54.5mm', '57.2mm', '54.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '57.2mm', '54.6mm', '57.8mm', '54.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'CAN_TX', '57.8mm', '54.6mm', ViaCount);
    AddA10Track(Board, 'CAN_TX', '57.8mm', '54.6mm', '57.8mm', '51.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '57.8mm', '51.4mm', '37.6mm', '31.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '37.6mm', '31.2mm', '30.8mm', '31.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '30.8mm', '31.2mm', '21.4mm', '21.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '21.4mm', '21.8mm', '21.4mm', '15.0mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '21.4mm', '15.0mm', '33.2mm', '3.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '33.2mm', '3.2mm', '49.2mm', '3.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '49.2mm', '3.2mm', '49.4mm', '3.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '49.4mm', '3.4mm', '89.6mm', '3.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '89.6mm', '3.4mm', '93.4mm', '7.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '93.4mm', '7.2mm', '95.2mm', '7.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '95.2mm', '7.2mm', '96.2mm', '8.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '96.2mm', '8.2mm', '96.2mm', '15.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '96.2mm', '15.2mm', '83.6mm', '27.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '83.6mm', '27.8mm', '80.0mm', '27.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '80.0mm', '27.8mm', '77.6mm', '30.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'CAN_TX', '77.6mm', '30.2mm', ViaCount);
    AddA10Track(Board, 'CAN_TX', '77.6mm', '30.2mm', '77.6mm', '30.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '77.6mm', '30.8mm', '77.8mm', '31.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_TX', '77.8mm', '31.0mm', '78.599995mm', '30.974995mm', '0.20mm', eTopLayer, TrackCount);

    { ETH_MDIO }
    AddA10Track(Board, 'ETH_MDIO', '39.324991mm', '30.250003mm', '38.6mm', '30.25mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '38.6mm', '30.25mm', '38.1mm', '30.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '38.1mm', '30.0mm', '37.2mm', '29.6mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '37.2mm', '29.6mm', '37.0mm', '29.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_MDIO', '37.0mm', '29.4mm', ViaCount);
    AddA10Track(Board, 'ETH_MDIO', '37.0mm', '29.4mm', '42.4mm', '29.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '42.4mm', '29.4mm', '49.6mm', '36.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_MDIO', '49.6mm', '36.6mm', ViaCount);
    AddA10Track(Board, 'ETH_MDIO', '49.6mm', '36.6mm', '60.8mm', '47.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '60.8mm', '47.8mm', '66.2mm', '47.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_MDIO', '66.2mm', '47.8mm', ViaCount);
    AddA10Track(Board, 'ETH_MDIO', '66.2mm', '47.8mm', '68.8mm', '47.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '68.8mm', '47.8mm', '74.8mm', '53.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_MDIO', '74.8mm', '53.8mm', ViaCount);
    AddA10Track(Board, 'ETH_MDIO', '74.8mm', '53.8mm', '74.6mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '74.6mm', '53.8mm', '74.4mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '74.4mm', '53.6mm', '74.2mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '74.2mm', '53.6mm', '74.2mm', '54.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '74.2mm', '54.4mm', '73.25mm', '55.2mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDIO', '73.25mm', '55.2mm', '73.249993mm', '56.062499mm', '0.15mm', eTopLayer, TrackCount);

    { ETH_MDC }
    AddA10Track(Board, 'ETH_MDC', '39.324991mm', '34.749994mm', '38.2mm', '34.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '38.2mm', '34.75mm', '38.0mm', '34.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_MDC', '38.0mm', '34.0mm', ViaCount);
    AddA10Track(Board, 'ETH_MDC', '38.0mm', '34.0mm', '41.4mm', '34.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '41.4mm', '34.0mm', '49.6mm', '42.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_MDC', '49.6mm', '42.2mm', ViaCount);
    AddA10Track(Board, 'ETH_MDC', '49.6mm', '42.2mm', '59.8mm', '52.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '59.8mm', '52.4mm', '59.8mm', '55.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '59.8mm', '55.8mm', '63.4mm', '59.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '63.4mm', '59.4mm', '71.6mm', '59.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '71.6mm', '59.4mm', '73.6mm', '57.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '73.6mm', '57.4mm', '73.6mm', '56.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '73.6mm', '56.4mm', '74.2mm', '55.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'ETH_MDC', '74.2mm', '55.8mm', ViaCount);
    AddA10Track(Board, 'ETH_MDC', '74.2mm', '55.8mm', '74.8mm', '55.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '74.8mm', '55.2mm', '75.8mm', '55.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '75.8mm', '55.2mm', '76.0mm', '55.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '76.0mm', '55.4mm', '74.65mm', '56.75mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_MDC', '74.65mm', '56.75mm', '73.937495mm', '56.750001mm', '0.15mm', eTopLayer, TrackCount);

    { ETH_CT }
    AddA10Track(Board, 'ETH_CT', '89.670001mm', '60.000007mm', '88.4mm', '60.0mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '88.4mm', '60.0mm', '88.4mm', '61.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '88.4mm', '61.4mm', '85.4mm', '61.4mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '61.4mm', '85.4mm', '59.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'ETH_CT', '85.4mm', '59.4mm', ViaCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '59.4mm', '84.6mm', '58.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.6mm', '58.6mm', '84.4mm', '56.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.4mm', '56.2mm', '84.8mm', '55.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.8mm', '55.8mm', '85.4mm', '55.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'ETH_CT', '85.4mm', '55.8mm', ViaCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '55.8mm', '83.6mm', '55.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '83.6mm', '55.8mm', '83.2mm', '56.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '83.2mm', '56.2mm', '82.499992mm', '56.225008mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '93.480001mm', '57.460007mm', '92.4mm', '57.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '92.4mm', '57.4mm', '92.4mm', '56.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '92.4mm', '56.2mm', '92.0mm', '55.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '92.0mm', '55.8mm', '85.4mm', '55.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '55.8mm', '84.8mm', '55.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.8mm', '55.8mm', '84.4mm', '56.2mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.4mm', '56.2mm', '84.6mm', '58.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '84.6mm', '58.6mm', '85.4mm', '59.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '59.4mm', '85.4mm', '60.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '85.4mm', '60.8mm', '86.0mm', '61.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'ETH_CT', '86.0mm', '61.4mm', '88.4mm', '61.4mm', '0.20mm', eTopLayer, TrackCount);

    { CAN_RX }
    AddA10Track(Board, 'CAN_RX', '58.249998mm', '52.675003mm', '58.25mm', '53.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '58.25mm', '53.75mm', '59.0mm', '54.5mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '59.0mm', '54.5mm', '59.2mm', '54.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '59.2mm', '54.6mm', '59.4mm', '54.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '59.4mm', '54.8mm', '60.4mm', '54.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'CAN_RX', '60.4mm', '54.8mm', ViaCount);
    AddA10Track(Board, 'CAN_RX', '60.4mm', '54.8mm', '60.6mm', '54.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '60.6mm', '54.8mm', '61.0mm', '54.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '61.0mm', '54.4mm', '61.6mm', '54.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '61.6mm', '54.4mm', '63.4mm', '56.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '63.4mm', '56.2mm', '63.4mm', '56.4mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'CAN_RX', '63.4mm', '56.4mm', ViaCount);
    AddA10Track(Board, 'CAN_RX', '63.4mm', '56.4mm', '64.4mm', '56.4mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'CAN_RX', '64.4mm', '56.4mm', '65.2mm', '55.6mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Track(Board, 'CAN_RX', '65.2mm', '55.6mm', '65.2mm', '54.8mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'CAN_RX', '65.2mm', '54.8mm', ViaCount);
    AddA10Track(Board, 'CAN_RX', '65.2mm', '54.8mm', '66.4mm', '53.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '66.4mm', '53.6mm', '66.4mm', '51.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'CAN_RX', '66.4mm', '51.8mm', ViaCount);
    AddA10Track(Board, 'CAN_RX', '66.4mm', '51.8mm', '69.0mm', '49.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'CAN_RX', '69.0mm', '49.2mm', ViaCount);
    AddA10Track(Board, 'CAN_RX', '69.0mm', '49.2mm', '73.2mm', '45.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '73.2mm', '45.0mm', '73.2mm', '33.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '73.2mm', '33.6mm', '77.8mm', '29.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'CAN_RX', '77.8mm', '29.0mm', '78.599995mm', '29.025012mm', '0.20mm', eTopLayer, TrackCount);

    { NRST }
    AddA10Track(Board, 'NRST', '35.750001mm', '37.019992mm', '35.8mm', '36.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '35.8mm', '36.2mm', '36.2mm', '35.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '36.2mm', '35.8mm', '36.8mm', '35.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '36.8mm', '35.8mm', '38.8mm', '35.75mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '38.8mm', '35.75mm', '39.324991mm', '35.749992mm', '0.15mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '67.750004mm', '15.050008mm', '66.6mm', '15.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '66.6mm', '15.0mm', '65.2mm', '15.0mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '65.2mm', '15.0mm', '62.8mm', '17.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '62.8mm', '17.4mm', '62.8mm', '20.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '62.8mm', '20.2mm', '61.8mm', '21.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'NRST', '61.8mm', '21.2mm', ViaCount);
    AddA10Track(Board, 'NRST', '61.8mm', '21.2mm', '59.4mm', '23.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'NRST', '59.4mm', '23.6mm', '42.6mm', '23.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'NRST', '42.6mm', '23.6mm', '37.6mm', '28.6mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'NRST', '37.6mm', '28.6mm', ViaCount);
    AddA10Track(Board, 'NRST', '37.6mm', '28.6mm', '36.0mm', '28.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '36.0mm', '28.6mm', '32.8mm', '31.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '32.8mm', '31.8mm', '32.8mm', '35.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'NRST', '32.8mm', '35.4mm', ViaCount);
    AddA10Track(Board, 'NRST', '32.8mm', '35.4mm', '34.2mm', '36.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'NRST', '34.2mm', '36.8mm', '35.0mm', '36.8mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Track(Board, 'NRST', '35.0mm', '36.8mm', '35.6mm', '36.2mm', '0.20mm', eBottomLayer, TrackCount);
    AddA10Via(Board, 'NRST', '35.6mm', '36.2mm', ViaCount);
    AddA10Track(Board, 'NRST', '35.6mm', '36.2mm', '35.8mm', '36.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '35.8mm', '36.4mm', '35.750001mm', '37.019992mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '67.750004mm', '5.950001mm', '67.8mm', '7.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '67.8mm', '7.4mm', '67.8mm', '13.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'NRST', '67.8mm', '13.6mm', '67.750004mm', '15.050008mm', '0.20mm', eTopLayer, TrackCount);

    { BOOT0 }
    AddA10Track(Board, 'BOOT0', '46.00001mm', '54.674999mm', '46.0mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '46.0mm', '53.8mm', '45.8mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '45.8mm', '53.8mm', '46.2mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '46.2mm', '53.8mm', '46.249996mm', '52.675003mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '63.999999mm', '4.674997mm', '64.0mm', '3.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '64.0mm', '3.8mm', '63.8mm', '3.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '63.8mm', '3.6mm', '57.4mm', '3.6mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '57.4mm', '3.6mm', '46.2mm', '14.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '46.2mm', '14.8mm', '46.2mm', '17.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '46.2mm', '17.8mm', '32.2mm', '31.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '32.2mm', '31.8mm', '32.2mm', '41.2mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '32.2mm', '41.2mm', '33.4mm', '42.4mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Via(Board, 'BOOT0', '33.4mm', '42.4mm', ViaCount);
    AddA10Track(Board, 'BOOT0', '33.4mm', '42.4mm', '45.0mm', '54.0mm', '0.20mm', eMidLayer2, TrackCount);
    AddA10Via(Board, 'BOOT0', '45.0mm', '54.0mm', ViaCount);
    AddA10Track(Board, 'BOOT0', '45.0mm', '54.0mm', '45.2mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '45.2mm', '53.8mm', '46.0mm', '53.8mm', '0.20mm', eTopLayer, TrackCount);
    AddA10Track(Board, 'BOOT0', '46.0mm', '53.8mm', '46.00001mm', '54.674999mm', '0.20mm', eTopLayer, TrackCount);

    { Snap generated primitives to the native pad coordinates after component moves. }
    SnapA10PadConnections(Board, 'C102', '1');
    SnapA10PadConnections(Board, 'C102', '2');
    SnapA10PadConnections(Board, 'C107', '1');
    SnapA10PadConnections(Board, 'C107', '2');
    SnapA10PadConnections(Board, 'C111', '1');
    SnapA10PadConnections(Board, 'C111', '2');
    SnapA10PadConnections(Board, 'C113', '1');
    SnapA10PadConnections(Board, 'C113', '2');
    SnapA10PadConnections(Board, 'C115', '1');
    SnapA10PadConnections(Board, 'C115', '2');
    SnapA10PadConnections(Board, 'C60', '1');
    SnapA10PadConnections(Board, 'C60', '2');
    SnapA10PadConnections(Board, 'C63', '1');
    SnapA10PadConnections(Board, 'C63', '2');
    SnapA10PadConnections(Board, 'C64', '1');
    SnapA10PadConnections(Board, 'C64', '2');
    SnapA10PadConnections(Board, 'R601', '1');
    SnapA10PadConnections(Board, 'R601', '2');
    SnapA10PadConnections(Board, 'R602', '1');
    SnapA10PadConnections(Board, 'R602', '2');
    SnapA10PadConnections(Board, 'R605', '1');
    SnapA10PadConnections(Board, 'R605', '2');

    PCBServer.PostProcess;
    Board.ViewManager_FullUpdate;
    ShowMessage('PCB-A10 candidate applied: added ' + IntToStr(TrackCount) +
                ' tracks and ' + IntToStr(ViaCount) + ' vias; removed ' +
                IntToStr(RemovedTracks) + ' tracks and ' + IntToStr(RemovedVias) +
                ' vias. Save and run DRC plus connection audit.');
End;
