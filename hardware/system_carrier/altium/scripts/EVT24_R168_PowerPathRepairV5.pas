Function R168V5Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V5FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V5Near(A, B : TCoord) : Boolean;
Begin
    Result := Abs(A - B) <= R168V5Coord('0.001mm');
End;

Function R168V5TrackMatches(TrackObj : IPCB_Track;
                            X1Text, Y1Text, X2Text, Y2Text : String) : Boolean;
Var
    X1, Y1, X2, Y2 : TCoord;
    ForwardMatch   : Boolean;
    ReverseMatch   : Boolean;
Begin
    X1 := R168V5Coord(X1Text);
    Y1 := R168V5Coord(Y1Text);
    X2 := R168V5Coord(X2Text);
    Y2 := R168V5Coord(Y2Text);
    ForwardMatch := R168V5Near(TrackObj.X1, X1) And
                    R168V5Near(TrackObj.Y1, Y1) And
                    R168V5Near(TrackObj.X2, X2) And
                    R168V5Near(TrackObj.Y2, Y2);
    ReverseMatch := R168V5Near(TrackObj.X1, X2) And
                    R168V5Near(TrackObj.Y1, Y2) And
                    R168V5Near(TrackObj.X2, X1) And
                    R168V5Near(TrackObj.Y2, Y1);
    Result := ForwardMatch Or ReverseMatch;
End;

Procedure R168V5AddTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                         X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                         LayerId : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V5Coord(X1Text);
    TrackObj.Y1 := R168V5Coord(Y1Text);
    TrackObj.X2 := R168V5Coord(X2Text);
    TrackObj.Y2 := R168V5Coord(Y2Text);
    TrackObj.Width := R168V5Coord(WidthText);
    TrackObj.Layer := LayerId;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V5AddFill(Board : IPCB_Board; NetObj : IPCB_Net;
                        LeftText, BottomText, RightText, TopText : String;
                        LayerId : TLayer; Var Count : Integer);
Var
    FillObj : IPCB_Fill;
Begin
    FillObj := PCBServer.PCBObjectFactory(eFillObject, eNoDimension,
                                          eCreate_Default);
    FillObj.X1Location := R168V5Coord(LeftText);
    FillObj.Y1Location := R168V5Coord(BottomText);
    FillObj.X2Location := R168V5Coord(RightText);
    FillObj.Y2Location := R168V5Coord(TopText);
    FillObj.Rotation := 0;
    FillObj.Layer := LayerId;
    FillObj.Net := NetObj;
    Board.AddPCBObject(FillObj);
    Inc(Count);
End;

Procedure R168V5AddVia(Board : IPCB_Board; NetObj : IPCB_Net;
                       XText, YText : String; Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V5Coord(XText);
    ViaObj.Y := R168V5Coord(YText);
    ViaObj.Size := R168V5Coord('0.60mm');
    ViaObj.HoleSize := R168V5Coord('0.30mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure R168V5Audit(Board : IPCB_Board;
                      Var VinRawBottomTracks, VinRawVias,
                          V12LocalTracks, VinProtectedFills : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
    ViaObj   : IPCB_Via;
    FillObj  : IPCB_Fill;
    NetName  : String;
Begin
    VinRawBottomTracks := 0;
    VinRawVias := 0;
    V12LocalTracks := 0;
    VinProtectedFills := 0;

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
            If (NetName = 'VIN_RAW') And (TrackObj.Layer = eBottomLayer) Then
                Inc(VinRawBottomTracks);
            If (NetName = 'V12_SYS') And (TrackObj.Layer = eTopLayer) And
               (TrackObj.X1 >= R168V5Coord('68mm')) And
               (TrackObj.X2 >= R168V5Coord('68mm')) And
               (TrackObj.Y1 >= R168V5Coord('14mm')) And
               (TrackObj.Y2 >= R168V5Coord('14mm')) Then
                Inc(V12LocalTracks);
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
        If (ViaObj.Net <> Nil) And
           (UpperCase(ViaObj.Net.Name) = 'VIN_RAW') Then
            Inc(VinRawVias);
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
           (UpperCase(FillObj.Net.Name) = 'VIN_PROTECTED_24V') Then
            Inc(VinProtectedFills);
        FillObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V5RemoveObsoleteCopper(Board : IPCB_Board;
                                     Var RemovedTracks, RemovedVias : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    ViaObj    : IPCB_Via;
    NextVia   : IPCB_Via;
    NetName   : String;
    RemoveIt  : Boolean;
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
        RemoveIt := False;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) Then
        Begin
            NetName := UpperCase(TrackObj.Net.Name);
            If (NetName = 'VIN_RAW') And (TrackObj.Layer = eBottomLayer) Then
                RemoveIt := True;
            If (NetName = 'V12_SYS') And (TrackObj.Layer = eTopLayer) And
               (TrackObj.X1 >= R168V5Coord('68mm')) And
               (TrackObj.X2 >= R168V5Coord('68mm')) And
               (TrackObj.Y1 >= R168V5Coord('14mm')) And
               (TrackObj.Y2 >= R168V5Coord('14mm')) Then
                RemoveIt := True;
        End;
        If RemoveIt Then
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
        If (ViaObj.Net <> Nil) And
           (UpperCase(ViaObj.Net.Name) = 'VIN_RAW') Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(RemovedVias);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V5WidenVinRawEntry(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj : IPCB_Track;
Begin
    Count := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) And
           (UpperCase(TrackObj.Net.Name) = 'VIN_RAW') Then
        Begin
            If R168V5TrackMatches(TrackObj,
                                  '5mm', '14mm', '8.4mm', '10.6mm') Then
            Begin
                TrackObj.Width := R168V5Coord('1.80mm');
                Inc(Count);
            End;
            If R168V5TrackMatches(TrackObj,
                                  '8.4mm', '10.6mm', '11mm', '10.6mm') Or
               R168V5TrackMatches(TrackObj,
                                  '11mm', '10.6mm', '16.1mm', '10.6mm') Then
            Begin
                TrackObj.Width := R168V5Coord('2.00mm');
                Inc(Count);
            End;
        End;
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyR168PowerPathRepairV5;
Var
    Board              : IPCB_Board;
    VinRaw             : IPCB_Net;
    VinProtected       : IPCB_Net;
    V12Sys             : IPCB_Net;
    VinRawBottomTracks : Integer;
    VinRawVias         : Integer;
    V12LocalTracks     : Integer;
    VinProtectedFills  : Integer;
    RemovedTracks      : Integer;
    RemovedVias        : Integer;
    WidenedTracks      : Integer;
    AddedTracks        : Integer;
    AddedVias          : Integer;
    AddedFills         : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 power V5 stopped: activate EVT24_REWORK_R168.PcbDoc.');
        Exit;
    End;

    VinRaw := R168V5FindNet(Board, 'VIN_RAW');
    VinProtected := R168V5FindNet(Board, 'VIN_PROTECTED_24V');
    V12Sys := R168V5FindNet(Board, 'V12_SYS');
    If (VinRaw = Nil) Or (VinProtected = Nil) Or (V12Sys = Nil) Then
    Begin
        ShowMessage('R168 power V5 stopped: a required power net is missing.');
        Exit;
    End;

    R168V5Audit(Board, VinRawBottomTracks, VinRawVias,
                V12LocalTracks, VinProtectedFills);
    If (VinRawBottomTracks <> 5) Or (VinRawVias <> 2) Or
       (V12LocalTracks <> 3) Or (VinProtectedFills <> 2) Then
    Begin
        ShowMessage('R168 power V5 stopped: audited geometry differs. VIN_RAW=' +
                    IntToStr(VinRawBottomTracks) + '/' + IntToStr(VinRawVias) +
                    ', V12 local=' + IntToStr(V12LocalTracks) +
                    ', VIN_PROT fills=' + IntToStr(VinProtectedFills) + '.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    WidenedTracks := 0;
    AddedTracks := 0;
    AddedVias := 0;
    AddedFills := 0;

    PCBServer.PreProcess;
    Try
        R168V5RemoveObsoleteCopper(Board, RemovedTracks, RemovedVias);
        R168V5WidenVinRawEntry(Board, WidenedTracks);

        R168V5AddTrack(Board, VinRaw,
                       '16.1mm', '10.6mm', '14.8mm', '11.9mm',
                       '2.00mm', eTopLayer, AddedTracks);
        R168V5AddTrack(Board, VinRaw,
                       '14.8mm', '11.9mm', '14.8mm', '14.5mm',
                       '2.00mm', eTopLayer, AddedTracks);
        R168V5AddTrack(Board, VinRaw,
                       '14.8mm', '14.5mm', '16.245mm', '14.5mm',
                       '2.00mm', eTopLayer, AddedTracks);

        R168V5AddFill(Board, VinProtected,
                      '26.5mm', '14.625mm', '27.95mm', '15.375mm',
                      eTopLayer, AddedFills);
        R168V5AddVia(Board, VinProtected, '27.7mm', '14.7mm', AddedVias);
        R168V5AddVia(Board, VinProtected, '27.7mm', '15.3mm', AddedVias);
        R168V5AddTrack(Board, VinProtected,
                       '27.7mm', '15.3mm', '32.2mm', '15.3mm',
                       '3.00mm', eBottomLayer, AddedTracks);
        R168V5AddVia(Board, VinProtected, '32.2mm', '13.7mm', AddedVias);
        R168V5AddVia(Board, VinProtected, '32.2mm', '14.3mm', AddedVias);
        R168V5AddFill(Board, VinProtected,
                      '31.9mm', '13.4mm', '33.65mm', '14.6mm',
                      eTopLayer, AddedFills);

        R168V5AddFill(Board, V12Sys,
                      '68.2mm', '15.15mm', '69.9mm', '16.15mm',
                      eTopLayer, AddedFills);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 power V5 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', removed vias=' +
                IntToStr(RemovedVias) + ', widened tracks=' +
                IntToStr(WidenedTracks) + ', added tracks=' +
                IntToStr(AddedTracks) + ', added vias=' +
                IntToStr(AddedVias) + ', added fills=' +
                IntToStr(AddedFills) + '.');
End;
