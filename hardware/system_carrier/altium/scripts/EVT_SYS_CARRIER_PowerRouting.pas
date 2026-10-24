{ Apply the reviewed EVT power-copper plan to the canonical native PcbDoc.
  The wide rails use fills because the power contract prefers pours and permits
  narrow copper only at component pins.
}

Function EVTPowerCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function IsCanonicalPowerBoard(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0) And
        (UpperCase(ExtractFileName(APath)) = 'EVT_SYS_CARRIER.PCBDOC');
End;

Function FindPowerProject : IProject;
Var
    WS        : IWorkspace;
    Candidate : IProject;
    Doc       : IDocument;
    I         : Integer;
    J         : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;

    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Candidate := WS.DM_Projects(I);
        If Candidate = Nil Then Continue;
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        If Pos('\hardware\system_carrier\altium\native\', LowerCase(Candidate.DM_ProjectFullPath)) = 0 Then Continue;

        For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Candidate.DM_LogicalDocuments(J);
            If Doc = Nil Then Continue;
            If IsCanonicalPowerBoard(Doc.DM_FullPath) Then
            Begin
                Result := Candidate;
                Exit;
            End;
        End;
    End;
End;

Function ResolvePowerBoard : IPCB_Board;
Var
    Project : IProject;
    Doc     : IDocument;
    PcbDoc  : IServerDocument;
    I       : Integer;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If Result <> Nil Then
        If IsCanonicalPowerBoard(Result.FileName) Then Exit;
    Result := Nil;

    Project := FindPowerProject;
    If Project = Nil Then Exit;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then Continue;
        If Not IsCanonicalPowerBoard(Doc.DM_FullPath) Then Continue;
        PcbDoc := Client.OpenDocument('PCB', Doc.DM_FullPath);
        If PcbDoc = Nil Then Continue;
        Client.ShowDocument(PcbDoc);
        Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
        Exit;
    End;
End;

Function FindPowerNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Procedure AddPowerFill(Board : IPCB_Board; NetObj : IPCB_Net; LayerKind : TLayer;
                       LeftText : String; BottomText : String;
                       RightText : String; TopText : String;
                       Var FillCount : Integer);
Var
    FillObj : IPCB_Fill;
Begin
    FillObj := PCBServer.PCBObjectFactory(eFillObject, eNoDimension, eCreate_Default);
    FillObj.X1Location := EVTPowerCoord(LeftText);
    FillObj.Y1Location := EVTPowerCoord(BottomText);
    FillObj.X2Location := EVTPowerCoord(RightText);
    FillObj.Y2Location := EVTPowerCoord(TopText);
    FillObj.Rotation := 0;
    FillObj.Layer := LayerKind;
    FillObj.Net := NetObj;
    Board.AddPCBObject(FillObj);
    FillCount := FillCount + 1;
End;

Procedure AddPowerVia(Board : IPCB_Board; NetObj : IPCB_Net;
                      XText : String; YText : String;
                      SizeText : String; HoleText : String;
                      Var ViaCount : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := EVTPowerCoord(XText);
    ViaObj.Y := EVTPowerCoord(YText);
    ViaObj.Size := EVTPowerCoord(SizeText);
    ViaObj.HoleSize := EVTPowerCoord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    ViaCount := ViaCount + 1;
End;

Procedure RouteVinRaw(Board : IPCB_Board; NetObj : IPCB_Net;
                      Var FillCount, ViaCount : Integer);
Begin
    AddPowerFill(Board, NetObj, eBottomLayer, '5mm', '6.9mm', '19.5mm', '9.9mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '4.6mm', '8.4mm', '5.4mm', '14mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '12.5mm', '10mm', '13.5mm', '11.2mm', FillCount);

    AddPowerVia(Board, NetObj, '19.175mm', '9.7mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eTopLayer, '18.95mm', '9.7mm', '19.40mm', '10.5mm', FillCount);

    AddPowerFill(Board, NetObj, eBottomLayer, '19.3mm', '8mm', '20.9mm', '8.8mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '20.1mm', '8.4mm', '20.9mm', '12mm', FillCount);
    AddPowerVia(Board, NetObj, '20.5mm', '12mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eTopLayer, '20.5mm', '12.05mm', '21.75mm', '12.35mm', FillCount);
    AddPowerFill(Board, NetObj, eTopLayer, '21.65mm', '12.25mm', '21.85mm', '13mm', FillCount);
End;

Procedure RouteVinProtected(Board : IPCB_Board; NetObj : IPCB_Net;
                            Var FillCount, ViaCount : Integer);
Begin
    AddPowerFill(Board, NetObj, eBottomLayer, '25mm', '20.1mm', '59.2mm', '23.1mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '22.10mm', '15mm', '22.40mm', '15.8mm', FillCount);
    AddPowerVia(Board, NetObj, '22.25mm', '15.8mm', '0.5mm', '0.25mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '21.85mm', '15.8mm', '22.65mm', '21.6mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '22.25mm', '21.2mm', '25mm', '22mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '29.425mm', '17.5mm', '30.025mm', '19mm', FillCount);
    AddPowerVia(Board, NetObj, '29.725mm', '19mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '29.425mm', '19mm', '30.025mm', '21.6mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '28.4mm', '8.7mm', '30mm', '9.3mm', FillCount);
    AddPowerVia(Board, NetObj, '28.4mm', '9mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '28.1mm', '9mm', '28.7mm', '21.6mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '31.2mm', '12.95mm', '32.95mm', '14.4mm', FillCount);
    AddPowerFill(Board, NetObj, eTopLayer, '32.4mm', '12.3mm', '33.35mm', '12.95mm', FillCount);
    AddPowerVia(Board, NetObj, '31.2mm', '13.75mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '30.8mm', '13.75mm', '31.6mm', '21.6mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '58.95mm', '9.7mm', '59.4mm', '10.5mm', FillCount);
    AddPowerVia(Board, NetObj, '59.175mm', '9.7mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '58.875mm', '9.7mm', '59.475mm', '21.6mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '61.60mm', '15mm', '61.90mm', '15.8mm', FillCount);
    AddPowerVia(Board, NetObj, '61.75mm', '15.8mm', '0.5mm', '0.25mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '59mm', '15.5mm', '61.75mm', '16.1mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '58.7mm', '15.8mm', '59.3mm', '21.6mm', FillCount);
End;

Procedure RouteBuckAnd3V3(Board : IPCB_Board; BuckNet, RailNet : IPCB_Net;
                          Var FillCount, ViaCount : Integer);
Begin
    AddPowerFill(Board, BuckNet, eTopLayer, '35.35mm', '13.13mm', '40.815mm', '14.35mm', FillCount);

    AddPowerFill(Board, RailNet, eTopLayer, '42.435mm', '7.6mm', '43.935mm', '14mm', FillCount);
    AddPowerFill(Board, RailNet, eTopLayer, '38.5mm', '7.6mm', '43.185mm', '9.1mm', FillCount);
    AddPowerFill(Board, RailNet, eTopLayer, '33.625mm', '7.9mm', '33.875mm', '12.95mm', FillCount);
    AddPowerFill(Board, RailNet, eTopLayer, '33.75mm', '7.9mm', '38.5mm', '8.15mm', FillCount);
    AddPowerFill(Board, RailNet, eTopLayer, '43.185mm', '13.25mm', '45.7mm', '14.75mm', FillCount);
    AddPowerVia(Board, RailNet, '45.7mm', '14mm', '0.8mm', '0.4mm', ViaCount);

    AddPowerFill(Board, RailNet, eMidLayer2, '25mm', '23.45mm', '80mm', '24.95mm', FillCount);
    AddPowerFill(Board, RailNet, eMidLayer2, '44.95mm', '14mm', '46.45mm', '24.2mm', FillCount);

    AddPowerFill(Board, RailNet, eTopLayer, '24.75mm', '18.3mm', '25.25mm', '19mm', FillCount);
    AddPowerVia(Board, RailNet, '25mm', '19mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, RailNet, eMidLayer2, '24.7mm', '19mm', '25.3mm', '24.2mm', FillCount);

    AddPowerFill(Board, RailNet, eTopLayer, '36.75mm', '18.3mm', '37.25mm', '19mm', FillCount);
    AddPowerVia(Board, RailNet, '37mm', '19mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, RailNet, eMidLayer2, '36.7mm', '19mm', '37.3mm', '24.2mm', FillCount);

    AddPowerFill(Board, RailNet, eTopLayer, '64.75mm', '18.3mm', '65.25mm', '19mm', FillCount);
    AddPowerVia(Board, RailNet, '65mm', '19mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, RailNet, eMidLayer2, '64.7mm', '19mm', '65.3mm', '24.2mm', FillCount);
End;

Procedure RouteRadar12V(Board : IPCB_Board; NetObj : IPCB_Net;
                        Var FillCount, ViaCount : Integer);
Begin
    AddPowerFill(Board, NetObj, eTopLayer, '62.15mm', '12.25mm', '62.35mm', '13mm', FillCount);
    AddPowerFill(Board, NetObj, eTopLayer, '62.25mm', '12.05mm', '63.5mm', '12.35mm', FillCount);
    AddPowerVia(Board, NetObj, '63mm', '12mm', '0.5mm', '0.25mm', ViaCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '63mm', '11.7mm', '65.5mm', '12.3mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '65.1mm', '8.4mm', '65.9mm', '12mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '65.5mm', '7.65mm', '95mm', '9.15mm', FillCount);
    AddPowerFill(Board, NetObj, eBottomLayer, '94.6mm', '8.4mm', '95.4mm', '14mm', FillCount);
End;

Procedure RoutePowerGround(Board : IPCB_Board; NetObj : IPCB_Net;
                           Var FillCount, ViaCount : Integer);
Begin
    AddPowerFill(Board, NetObj, eMidLayer1, '8mm', '15.25mm', '20.8mm', '16.75mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '20.55mm', '16mm', '21.55mm', '18.5mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '21.05mm', '18mm', '23.45mm', '19mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '22.95mm', '16mm', '23.95mm', '18.5mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '23.45mm', '15.25mm', '60.3mm', '16.75mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '60.05mm', '16mm', '61.05mm', '18.5mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '60.55mm', '18mm', '62.95mm', '19mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '62.45mm', '16mm', '63.45mm', '18.5mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '62.95mm', '15.25mm', '94mm', '16.75mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '94mm', '15.25mm', '98mm', '16.55mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '7.6mm', '14mm', '8.4mm', '15.3mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '97.6mm', '14mm', '98.4mm', '15.3mm', FillCount);

    AddPowerVia(Board, NetObj, '13mm', '16mm', '0.8mm', '0.4mm', ViaCount);
    AddPowerVia(Board, NetObj, '23.65mm', '13.75mm', '0.5mm', '0.25mm', ViaCount);
    AddPowerFill(Board, NetObj, eTopLayer, '23mm', '13.65mm', '23.65mm', '13.85mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '23.15mm', '13.775mm', '23.85mm', '16mm', FillCount);

    AddPowerVia(Board, NetObj, '30mm', '12mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '29.7mm', '12mm', '30.3mm', '16mm', FillCount);
    AddPowerVia(Board, NetObj, '32.2mm', '17.5mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eTopLayer, '31.275mm', '17.2mm', '32.2mm', '17.8mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '31.9mm', '16mm', '32.5mm', '17.5mm', FillCount);
    AddPowerVia(Board, NetObj, '38.5mm', '12mm', '0.6mm', '0.3mm', ViaCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '38.2mm', '12mm', '38.8mm', '16mm', FillCount);

    AddPowerFill(Board, NetObj, eTopLayer, '34.1mm', '12.8mm', '34.825mm', '13.55mm', FillCount);
    AddPowerFill(Board, NetObj, eTopLayer, '34.1mm', '14.45mm', '34.825mm', '15.2mm', FillCount);
    AddPowerVia(Board, NetObj, '33.7mm', '13.7mm', '0.4mm', '0.2mm', ViaCount);
    AddPowerVia(Board, NetObj, '34.3mm', '13.7mm', '0.4mm', '0.2mm', ViaCount);
    AddPowerVia(Board, NetObj, '33.7mm', '14.3mm', '0.4mm', '0.2mm', ViaCount);
    AddPowerVia(Board, NetObj, '34.3mm', '14.3mm', '0.4mm', '0.2mm', ViaCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '33.2mm', '13.85mm', '34.8mm', '16mm', FillCount);

    AddPowerVia(Board, NetObj, '63.65mm', '13.75mm', '0.5mm', '0.25mm', ViaCount);
    AddPowerFill(Board, NetObj, eTopLayer, '63mm', '13.65mm', '63.65mm', '13.85mm', FillCount);
    AddPowerFill(Board, NetObj, eMidLayer1, '63.15mm', '13.775mm', '63.85mm', '16mm', FillCount);
End;

Procedure ApplyEVTPowerRouting;
Var
    Board        : IPCB_Board;
    VinRaw       : IPCB_Net;
    VinProtected : IPCB_Net;
    BuckSwitch   : IPCB_Net;
    Rail3V3      : IPCB_Net;
    Radar12V     : IPCB_Net;
    Ground       : IPCB_Net;
    FillCount    : Integer;
    ViaCount     : Integer;
Begin
    Board := ResolvePowerBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT power routing stopped: canonical native PcbDoc not found.');
        Exit;
    End;
    If Not IsCanonicalPowerBoard(Board.FileName) Then
    Begin
        ShowMessage('EVT power routing stopped: active board is not the canonical native PcbDoc.');
        Exit;
    End;

    VinRaw := FindPowerNet(Board, 'VIN_RAW');
    VinProtected := FindPowerNet(Board, 'VIN_PROTECTED');
    BuckSwitch := FindPowerNet(Board, 'BUCK_SW');
    Rail3V3 := FindPowerNet(Board, '3V3');
    Radar12V := FindPowerNet(Board, 'RADAR_12V');
    Ground := FindPowerNet(Board, 'GND');
    If (VinRaw = Nil) Or (VinProtected = Nil) Or (BuckSwitch = Nil) Or
       (Rail3V3 = Nil) Or (Radar12V = Nil) Or (Ground = Nil) Then
    Begin
        ShowMessage('EVT power routing stopped: one or more required nets are missing.');
        Exit;
    End;

    FillCount := 0;
    ViaCount := 0;
    PCBServer.PreProcess;
    RouteVinRaw(Board, VinRaw, FillCount, ViaCount);
    RouteVinProtected(Board, VinProtected, FillCount, ViaCount);
    RouteBuckAnd3V3(Board, BuckSwitch, Rail3V3, FillCount, ViaCount);
    RouteRadar12V(Board, Radar12V, FillCount, ViaCount);
    RoutePowerGround(Board, Ground, FillCount, ViaCount);
    PCBServer.PostProcess;

    Board.ViewManager_FullUpdate;
    ShowMessage('EVT power routing applied: ' + IntToStr(FillCount) +
                ' copper fills and ' + IntToStr(ViaCount) + ' vias. Save and run DRC.');
End;
