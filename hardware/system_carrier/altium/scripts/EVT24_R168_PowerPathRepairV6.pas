Function R168V6Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V6Near(A, B : TCoord) : Boolean;
Begin
    Result := Abs(A - B) <= R168V6Coord('0.001mm');
End;

Function R168V6FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V6FindComponent(Board : IPCB_Board;
                             DesignatorText : String) : IPCB_Component;
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
        If UpperCase(CompObj.Name.Text) = UpperCase(DesignatorText) Then
        Begin
            Result := CompObj;
            Break;
        End;
        CompObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function R168V6TrackMatches(TrackObj : IPCB_Track;
                            X1Text, Y1Text, X2Text, Y2Text : String) : Boolean;
Var
    X1, Y1, X2, Y2 : TCoord;
Begin
    X1 := R168V6Coord(X1Text);
    Y1 := R168V6Coord(Y1Text);
    X2 := R168V6Coord(X2Text);
    Y2 := R168V6Coord(Y2Text);
    Result :=
        (R168V6Near(TrackObj.X1, X1) And R168V6Near(TrackObj.Y1, Y1) And
         R168V6Near(TrackObj.X2, X2) And R168V6Near(TrackObj.Y2, Y2)) Or
        (R168V6Near(TrackObj.X1, X2) And R168V6Near(TrackObj.Y1, Y2) And
         R168V6Near(TrackObj.X2, X1) And R168V6Near(TrackObj.Y2, Y1));
End;

Function R168V6FillMatches(FillObj : IPCB_Fill;
                           LeftText, BottomText, RightText, TopText : String) : Boolean;
Begin
    Result := R168V6Near(FillObj.X1Location, R168V6Coord(LeftText)) And
              R168V6Near(FillObj.Y1Location, R168V6Coord(BottomText)) And
              R168V6Near(FillObj.X2Location, R168V6Coord(RightText)) And
              R168V6Near(FillObj.Y2Location, R168V6Coord(TopText));
End;

Function R168V6ViaMatches(ViaObj : IPCB_Via;
                          XText, YText : String) : Boolean;
Begin
    Result := R168V6Near(ViaObj.X, R168V6Coord(XText)) And
              R168V6Near(ViaObj.Y, R168V6Coord(YText));
End;

Procedure R168V6AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V6Coord(X1Text);
    TrackObj.Y1 := R168V6Coord(Y1Text);
    TrackObj.X2 := R168V6Coord(X2Text);
    TrackObj.Y2 := R168V6Coord(Y2Text);
    TrackObj.Width := R168V6Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V6AddFill(Board : IPCB_Board; NetObj : IPCB_Net;
                        LeftText, BottomText, RightText, TopText : String;
                        LayerId : TLayer; Var Count : Integer);
Var
    FillObj : IPCB_Fill;
Begin
    FillObj := PCBServer.PCBObjectFactory(eFillObject, eNoDimension,
                                          eCreate_Default);
    FillObj.X1Location := R168V6Coord(LeftText);
    FillObj.Y1Location := R168V6Coord(BottomText);
    FillObj.X2Location := R168V6Coord(RightText);
    FillObj.Y2Location := R168V6Coord(TopText);
    FillObj.Rotation := 0;
    FillObj.Layer := LayerId;
    FillObj.Net := NetObj;
    Board.AddPCBObject(FillObj);
    Inc(Count);
End;

Procedure R168V6AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                       XText, YText, SizeText, HoleText : String;
                       Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V6Coord(XText);
    ViaObj.Y := R168V6Coord(YText);
    ViaObj.Size := R168V6Coord(SizeText);
    ViaObj.HoleSize := R168V6Coord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure R168V6RemoveTracks(Board : IPCB_Board; Var Count : Integer);
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
            If (NetName = 'VIN_PROTECTED_24V') And
               (TrackObj.Layer = eBottomLayer) And
               R168V6TrackMatches(TrackObj,
                                  '27.7mm', '15.3mm', '32.2mm', '15.3mm') Then
                RemoveIt := True;
            If (NetName = 'VIN_RAW') And (TrackObj.Layer = eTopLayer) And
               (R168V6TrackMatches(TrackObj,
                                   '21.4mm', '12.1mm', '22.6mm', '13.3mm') Or
                R168V6TrackMatches(TrackObj,
                                   '22.6mm', '13.3mm', '23.0625mm', '13.25mm')) Then
                RemoveIt := True;
            If (NetName = 'U7_DVDT') And (TrackObj.Layer = eTopLayer) And
               R168V6TrackMatches(TrackObj,
                                  '70.725mm', '13.125mm', '71.725mm', '13.125mm') Then
                RemoveIt := True;
            If (NetName = 'GND') And (TrackObj.Layer = eTopLayer) And
               (R168V6TrackMatches(TrackObj,
                                   '73.275mm', '13.125mm', '74mm', '13.125mm') Or
                R168V6TrackMatches(TrackObj,
                                   '71.4mm', '13.2mm', '71.4mm', '13.3mm') Or
                R168V6TrackMatches(TrackObj,
                                   '70.9mm', '13.775mm', '71.4mm', '13.3mm')) Then
                RemoveIt := True;
            If (NetName = 'GND') And (TrackObj.Layer = eMidLayer1) And
               (R168V6TrackMatches(TrackObj,
                                   '71.4mm', '13.2mm', '72.8mm', '11.8mm') Or
                R168V6TrackMatches(TrackObj,
                                   '71.4mm', '13.2mm', '72mm', '13.8mm')) Then
                RemoveIt := True;
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

Procedure R168V6RemoveVias(Board : IPCB_Board; Var Count : Integer);
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
               (R168V6ViaMatches(ViaObj, '27.7mm', '14.7mm') Or
                R168V6ViaMatches(ViaObj, '27.7mm', '15.3mm') Or
                R168V6ViaMatches(ViaObj, '32.2mm', '13.7mm') Or
                R168V6ViaMatches(ViaObj, '32.2mm', '14.3mm')) Then
                RemoveIt := True;
            If (NetName = 'GND') And
               (R168V6ViaMatches(ViaObj, '74mm', '13.125mm') Or
                R168V6ViaMatches(ViaObj, '71.4mm', '13.2mm')) Then
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

Procedure R168V6RemoveFills(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    FillObj  : IPCB_Fill;
    NextFill : IPCB_Fill;
    NetName  : String;
    RemoveIt : Boolean;
Begin
    Count := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eFillObject));
    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));
    Iterator.AddFilter_Method(eProcessAll);
    FillObj := Iterator.FirstPCBObject;
    While FillObj <> Nil Do
    Begin
        NextFill := Iterator.NextPCBObject;
        RemoveIt := False;
        If (FillObj.Component = Nil) And (FillObj.Net <> Nil) Then
        Begin
            NetName := UpperCase(FillObj.Net.Name);
            If (NetName = 'VIN_PROTECTED_24V') And
               (R168V6FillMatches(FillObj,
                                  '26.5mm', '14.625mm', '27.95mm', '15.375mm') Or
                R168V6FillMatches(FillObj,
                                  '31.9mm', '13.4mm', '33.65mm', '14.6mm')) Then
                RemoveIt := True;
            If (NetName = 'V12_SYS') And
               R168V6FillMatches(FillObj,
                                 '68.2mm', '15.15mm', '69.9mm', '16.15mm') Then
                RemoveIt := True;
            If (NetName = 'U6_IN_BLOCKED') Then
                RemoveIt := True;
        End;
        If RemoveIt Then
        Begin
            Board.RemovePCBObject(FillObj);
            Inc(Count);
        End;
        FillObj := NextFill;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V6AdjustTracks(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
    NetName  : String;
Begin
    Count := 0;
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
            If (NetName = 'VIN_RAW') And (TrackObj.Layer = eTopLayer) And
               R168V6TrackMatches(TrackObj,
                                  '5mm', '14mm', '8.4mm', '10.6mm') Then
            Begin
                TrackObj.Width := R168V6Coord('1.60mm');
                Inc(Count);
            End;
            If NetName = 'VIN_PROTECTED_24V' Then
            Begin
                If (TrackObj.Layer = eBottomLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '27.2mm', '17.3mm', '29mm', '15.5mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('1.30mm');
                    Inc(Count);
                End;
                If (TrackObj.Layer = eBottomLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '29mm', '12.8mm', '29mm', '15.5mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('1.50mm');
                    Inc(Count);
                End;
                If (TrackObj.Layer = eTopLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '29.1mm', '12.8mm', '30.9mm', '12.8mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('0.80mm');
                    Inc(Count);
                End;
                If (TrackObj.Layer = eTopLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '30.9mm', '12.8mm', '31mm', '12.7mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('0.50mm');
                    Inc(Count);
                End;
                If (TrackObj.Layer = eTopLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '31mm', '12.7mm', '31.8mm', '13.5mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('0.50mm');
                    Inc(Count);
                End;
                If (TrackObj.Layer = eTopLayer) And
                   R168V6TrackMatches(TrackObj,
                                      '31.8mm', '13.5mm', '33.1375mm', '13.5mm') Then
                Begin
                    TrackObj.Width := R168V6Coord('0.80mm');
                    Inc(Count);
                End;
            End;
        End;
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyR168PowerPathRepairV6;
Var
    Board          : IPCB_Board;
    VinRaw         : IPCB_Net;
    VinProtected   : IPCB_Net;
    U6Blocked      : IPCB_Net;
    V12Sys         : IPCB_Net;
    U7Dvdt         : IPCB_Net;
    GndNet         : IPCB_Net;
    C7D            : IPCB_Component;
    RemovedTracks  : Integer;
    RemovedVias    : Integer;
    RemovedFills   : Integer;
    AdjustedTracks : Integer;
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
        ShowMessage('R168 power V6 stopped: activate EVT24_REWORK_R168.PcbDoc.');
        Exit;
    End;

    VinRaw := R168V6FindNet(Board, 'VIN_RAW');
    VinProtected := R168V6FindNet(Board, 'VIN_PROTECTED_24V');
    U6Blocked := R168V6FindNet(Board, 'U6_IN_BLOCKED');
    V12Sys := R168V6FindNet(Board, 'V12_SYS');
    U7Dvdt := R168V6FindNet(Board, 'U7_DVDT');
    GndNet := R168V6FindNet(Board, 'GND');
    C7D := R168V6FindComponent(Board, 'C7D');
    If (VinRaw = Nil) Or (VinProtected = Nil) Or (U6Blocked = Nil) Or
       (V12Sys = Nil) Or (U7Dvdt = Nil) Or (GndNet = Nil) Or (C7D = Nil) Then
    Begin
        ShowMessage('R168 power V6 stopped: a required object is missing.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    RemovedFills := 0;
    AdjustedTracks := 0;
    AddedTracks := 0;
    AddedVias := 0;
    AddedFills := 0;

    PCBServer.PreProcess;
    Try
        R168V6RemoveTracks(Board, RemovedTracks);
        R168V6RemoveVias(Board, RemovedVias);
        R168V6RemoveFills(Board, RemovedFills);
        R168V6AdjustTracks(Board, AdjustedTracks);

        R168V6AddTrack(Board, VinRaw,
                       '21.4mm', '12.1mm', '22.6mm', '12.1mm',
                       '0.20mm', eTopLayer, AddedTracks);
        R168V6AddTrack(Board, VinRaw,
                       '22.6mm', '12.1mm', '23.0625mm', '13.25mm',
                       '0.20mm', eTopLayer, AddedTracks);

        R168V6AddFill(Board, U6Blocked,
                      '18.25mm', '12.65mm', '21.55mm', '15.65mm',
                      eTopLayer, AddedFills);
        R168V6AddFill(Board, U6Blocked,
                      '21.45mm', '14.65mm', '22.8mm', '15.375mm',
                      eTopLayer, AddedFills);

        R168V6AddFill(Board, VinProtected,
                      '26.5mm', '14.7mm', '27.55mm', '18.3mm',
                      eTopLayer, AddedFills);
        R168V6AddVia(Board, VinProtected,
                     '27.2mm', '18mm', '0.60mm', '0.30mm', AddedVias);
        R168V6AddTrack(Board, VinProtected,
                       '27.2mm', '18mm', '29mm', '15.5mm',
                       '1.30mm', eBottomLayer, AddedTracks);
        R168V6AddVia(Board, VinProtected,
                     '28.4mm', '11.8mm', '0.60mm', '0.30mm', AddedVias);
        R168V6AddTrack(Board, VinProtected,
                       '28.4mm', '11.8mm', '29mm', '12.8mm',
                       '1.00mm', eTopLayer, AddedTracks);
        R168V6AddTrack(Board, VinProtected,
                       '28.4mm', '11.8mm', '29mm', '12.8mm',
                       '1.00mm', eBottomLayer, AddedTracks);

        R168V6AddFill(Board, V12Sys,
                      '68.2mm', '15.15mm', '69.65mm', '16.15mm',
                      eTopLayer, AddedFills);

        C7D.X := R168V6Coord('75mm');
        C7D.Y := R168V6Coord('13.125mm');
        C7D.Rotation := 0;
        C7D.Name.Rotation := 0;
        C7D.NameAutoPosition := eAutoPos_TopCenter;
        C7D.AutoPosition_NameComment;
        C7D.Selected := False;

        R168V6AddTrack(Board, U7Dvdt,
                       '70.725mm', '13.125mm', '74.225mm', '13.125mm',
                       '0.20mm', eTopLayer, AddedTracks);
        R168V6AddTrack(Board, GndNet,
                       '70.9mm', '13.775mm', '71.7mm', '13.7mm',
                       '0.15mm', eTopLayer, AddedTracks);
        R168V6AddVia(Board, GndNet,
                     '71.7mm', '13.7mm', '0.40mm', '0.20mm', AddedVias);
        R168V6AddTrack(Board, GndNet,
                       '71.7mm', '13.7mm', '72mm', '13.8mm',
                       '0.30mm', eMidLayer1, AddedTracks);
        R168V6AddTrack(Board, GndNet,
                       '75.775mm', '13.125mm', '76.7mm', '13.125mm',
                       '0.30mm', eTopLayer, AddedTracks);
        R168V6AddVia(Board, GndNet,
                     '76.7mm', '13.125mm', '0.60mm', '0.30mm', AddedVias);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 power V6 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', vias=' + IntToStr(RemovedVias) +
                ', fills=' + IntToStr(RemovedFills) + ', adjusted tracks=' +
                IntToStr(AdjustedTracks) + ', added tracks=' +
                IntToStr(AddedTracks) + ', vias=' + IntToStr(AddedVias) +
                ', fills=' + IntToStr(AddedFills) + '.');
End;
