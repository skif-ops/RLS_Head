Function R168V10Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V10FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Procedure R168V10AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                          X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                          LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V10Coord(X1Text);
    TrackObj.Y1 := R168V10Coord(Y1Text);
    TrackObj.X2 := R168V10Coord(X2Text);
    TrackObj.Y2 := R168V10Coord(Y2Text);
    TrackObj.Width := R168V10Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V10AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                        XText, YText, SizeText, HoleText : String;
                        Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V10Coord(XText);
    ViaObj.Y := R168V10Coord(YText);
    ViaObj.Size := R168V10Coord(SizeText);
    ViaObj.HoleSize := R168V10Coord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure ApplyR168ConnectivityRepairV10;
Var
    Board        : IPCB_Board;
    VinProtected : IPCB_Net;
    GndNet       : IPCB_Net;
    AddedTracks  : Integer;
    AddedVias    : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 connectivity V10 stopped: EVT24_REWORK_R168.PcbDoc is unavailable.');
        Exit;
    End;

    VinProtected := R168V10FindNet(Board, 'VIN_PROTECTED_24V');
    GndNet := R168V10FindNet(Board, 'GND');
    If (VinProtected = Nil) Or (GndNet = Nil) Then
    Begin
        ShowMessage('R168 connectivity V10 stopped: a required net is missing.');
        Exit;
    End;

    AddedTracks := 0;
    AddedVias := 0;

    PCBServer.PreProcess;
    Try
        R168V10AddTrack(Board, GndNet,
                        '75.775mm', '13.125mm', '72.8mm', '11.325mm',
                        '0.30mm', eTopLayer, AddedTracks);

        R168V10AddTrack(Board, VinProtected,
                        '30.3mm', '14.2mm', '32mm', '13.8mm',
                        '0.40mm', eBottomLayer, AddedTracks);
        R168V10AddVia(Board, VinProtected,
                      '32mm', '13.8mm', '0.60mm', '0.30mm', AddedVias);
        R168V10AddTrack(Board, VinProtected,
                        '32mm', '13.8mm', '32.4mm', '14.2mm',
                        '0.20mm', eTopLayer, AddedTracks);
        R168V10AddTrack(Board, VinProtected,
                        '32.4mm', '14.2mm', '32.625mm', '14.5mm',
                        '0.20mm', eTopLayer, AddedTracks);
        R168V10AddTrack(Board, VinProtected,
                        '32.625mm', '13.5mm', '32.625mm', '14.5mm',
                        '0.20mm', eTopLayer, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 connectivity V10 applied. Added tracks=' +
                IntToStr(AddedTracks) + ', vias=' + IntToStr(AddedVias) + '.');
End;
