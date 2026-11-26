Function R168V13Coord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function R168V13FindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
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

Function R168V13Near(A, B : TCoord) : Boolean;
Begin
    Result := Abs(A - B) <= R168V13Coord('0.001mm');
End;

Function R168V13TrackMatches(TrackObj : IPCB_Track;
                             X1Text, Y1Text, X2Text, Y2Text : String) : Boolean;
Var
    X1, Y1, X2, Y2 : TCoord;
Begin
    X1 := R168V13Coord(X1Text);
    Y1 := R168V13Coord(Y1Text);
    X2 := R168V13Coord(X2Text);
    Y2 := R168V13Coord(Y2Text);
    Result :=
        (R168V13Near(TrackObj.X1, X1) And R168V13Near(TrackObj.Y1, Y1) And
         R168V13Near(TrackObj.X2, X2) And R168V13Near(TrackObj.Y2, Y2)) Or
        (R168V13Near(TrackObj.X1, X2) And R168V13Near(TrackObj.Y1, Y2) And
         R168V13Near(TrackObj.X2, X1) And R168V13Near(TrackObj.Y2, Y1));
End;

Procedure R168V13RemoveTracks(Board : IPCB_Board; GndNet : IPCB_Net;
                              Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
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
        RemoveIt := (TrackObj.Net = GndNet) And
            (R168V13TrackMatches(TrackObj,
                                 '75.775mm', '13.125mm',
                                 '76.7mm', '13.125mm') Or
             R168V13TrackMatches(TrackObj,
                                 '72mm', '13.8mm',
                                 '76.7mm', '13.125mm') Or
             R168V13TrackMatches(TrackObj,
                                 '72mm', '13.8mm',
                                 '75.775mm', '13.125mm'));
        If RemoveIt Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V13RemoveVias(Board : IPCB_Board; GndNet : IPCB_Net;
                            Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
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
        RemoveIt := (ViaObj.Net = GndNet) And
            (((R168V13Near(ViaObj.X, R168V13Coord('76.7mm'))) And
              (R168V13Near(ViaObj.Y, R168V13Coord('13.125mm')))) Or
             ((R168V13Near(ViaObj.X, R168V13Coord('75.775mm'))) And
              (R168V13Near(ViaObj.Y, R168V13Coord('13.125mm')))));
        If RemoveIt Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure R168V13AddMidLayerTrack(Board : IPCB_Board; NetObj : IPCB_Net;
                                  Var Count : Integer);
Var
    TrackObj : IPCB_Track;
Begin
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension,
                                           eCreate_Default);
    TrackObj.X1 := R168V13Coord('72mm');
    TrackObj.Y1 := R168V13Coord('13.8mm');
    TrackObj.X2 := R168V13Coord('75.775mm');
    TrackObj.Y2 := R168V13Coord('13.125mm');
    TrackObj.Width := R168V13Coord('0.30mm');
    TrackObj.Layer := eMidLayer1;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure R168V13AddViaInPad(Board : IPCB_Board; NetObj : IPCB_Net;
                             Var Count : Integer);
Var
    ViaObj : IPCB_Via;
Begin
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension,
                                         eCreate_Default);
    ViaObj.X := R168V13Coord('75.775mm');
    ViaObj.Y := R168V13Coord('13.125mm');
    ViaObj.Size := R168V13Coord('0.60mm');
    ViaObj.HoleSize := R168V13Coord('0.30mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure ApplyR168GroundReturnRepairV13;
Var
    Board         : IPCB_Board;
    GndNet        : IPCB_Net;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
    AddedTracks   : Integer;
    AddedVias     : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If (Board = Nil) Or
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT24_REWORK_R168.PCBDOC') Then
    Begin
        ShowMessage('R168 ground return V13 stopped: EVT24_REWORK_R168.PcbDoc is unavailable.');
        Exit;
    End;

    GndNet := R168V13FindNet(Board, 'GND');
    If GndNet = Nil Then
    Begin
        ShowMessage('R168 ground return V13 stopped: GND net is missing.');
        Exit;
    End;

    RemovedTracks := 0;
    RemovedVias := 0;
    AddedTracks := 0;
    AddedVias := 0;

    PCBServer.PreProcess;
    Try
        R168V13RemoveTracks(Board, GndNet, RemovedTracks);
        R168V13RemoveVias(Board, GndNet, RemovedVias);
        R168V13AddMidLayerTrack(Board, GndNet, AddedTracks);
        R168V13AddViaInPad(Board, GndNet, AddedVias);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');

    ShowMessage('R168 ground return V13 applied. Removed tracks=' +
                IntToStr(RemovedTracks) + ', removed vias=' +
                IntToStr(RemovedVias) + ', added tracks=' +
                IntToStr(AddedTracks) + ', added vias=' +
                IntToStr(AddedVias) + '.');
End;
