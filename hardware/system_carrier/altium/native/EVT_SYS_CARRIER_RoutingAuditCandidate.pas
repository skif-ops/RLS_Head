{ Export pad and routed-copper geometry from the PCB-A10 signal candidate.
  Run procedure: ExportRoutingGeometry
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function InvariantFloat(Value : Double) : String;
Begin
    Result := StringReplace(FloatToStr(Value), ',', '.', rfReplaceAll);
End;

Function ResolveNativeBoard : IPCB_Board;
Var
    Workspace     : IWorkspace;
    Project       : IProject;
    PcbDoc        : IServerDocument;
    I             : Integer;
    CandidatePath : String;
Begin
    Result := Nil;
    CandidatePath := '';
    Workspace := GetWorkspace;
    If Workspace = Nil Then Exit;
    For I := 0 To Workspace.DM_ProjectCount - 1 Do
    Begin
        Project := Workspace.DM_Projects(I);
        If Project = Nil Then Continue;
        If ExtractFileName(Project.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER_RoutingAuditCandidate.PrjScr' Then Continue;
        CandidatePath := ExtractFilePath(Project.DM_ProjectFullPath) + 'EVT_SYS_CARRIER_signal_candidate.PcbDoc';
        Break;
    End;
    If CandidatePath = '' Then Exit;

    Result := PCBServer.GetPCBBoardByPath(CandidatePath);
    If Result <> Nil Then Exit;

    Result := PCBServer.GetCurrentPCBBoard;
    If Result <> Nil Then
        If UpperCase(Result.FileName) = UpperCase(CandidatePath) Then Exit;
    Result := Nil;

    PcbDoc := Client.OpenDocument('PCB', CandidatePath);
    If PcbDoc = Nil Then Exit;
    Client.ShowDocument(PcbDoc);
    Result := PCBServer.GetPCBBoardByPath(CandidatePath);
End;

Procedure ExportPads(Board : IPCB_Board; BasePath : String);
Var
    Iterator   : IPCB_BoardIterator;
    Pad        : IPCB_Pad;
    Rpt        : TStringList;
    Designator : String;
    NetName    : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pad_name,net_name,x_mil,y_mil,x_raw,y_raw,layer,hole_mil,x_size_mil,y_size_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        Designator := '';
        NetName := '';
        If Pad.Component <> Nil Then
            Designator := Pad.Component.SourceDesignator;
        If Pad.Net <> Nil Then
            NetName := Pad.Net.Name;
        Rpt.Add(
            CsvQuote(Designator) + ',' + CsvQuote(Pad.Name) + ',' +
            CsvQuote(NetName) + ',' + InvariantFloat(CoordToMils(Pad.X)) + ',' +
            InvariantFloat(CoordToMils(Pad.Y)) + ',' + IntToStr(Pad.X) + ',' +
            IntToStr(Pad.Y) + ',' + IntToStr(Ord(Pad.Layer)) + ',' +
            InvariantFloat(CoordToMils(Pad.HoleSize)) + ',' +
            InvariantFloat(CoordToMils(Pad.TopXSize)) + ',' +
            InvariantFloat(CoordToMils(Pad.TopYSize))
        );
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'pad_geometry.csv');
    Rpt.Free;
End;

Procedure ExportTracks(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    Track    : IPCB_Track;
    Rpt      : TStringList;
    NetName  : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,x1_raw,y1_raw,x2_raw,y2_raw,width_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NetName := '';
        If Track.Net <> Nil Then NetName := Track.Net.Name;
        Rpt.Add(
            CsvQuote(NetName) + ',' + IntToStr(Ord(Track.Layer)) + ',' +
            InvariantFloat(CoordToMils(Track.X1)) + ',' +
            InvariantFloat(CoordToMils(Track.Y1)) + ',' +
            InvariantFloat(CoordToMils(Track.X2)) + ',' +
            InvariantFloat(CoordToMils(Track.Y2)) + ',' +
            IntToStr(Track.X1) + ',' + IntToStr(Track.Y1) + ',' +
            IntToStr(Track.X2) + ',' + IntToStr(Track.Y2) + ',' +
            InvariantFloat(CoordToMils(Track.Width))
        );
        Track := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'track_inventory.csv');
    Rpt.Free;
End;

Procedure ExportFills(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    FillObj  : IPCB_Fill;
    Rpt      : TStringList;
    NetName  : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,rotation_deg');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eFillObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    FillObj := Iterator.FirstPCBObject;
    While FillObj <> Nil Do
    Begin
        NetName := '';
        If FillObj.Net <> Nil Then NetName := FillObj.Net.Name;
        Rpt.Add(
            CsvQuote(NetName) + ',' + IntToStr(Ord(FillObj.Layer)) + ',' +
            InvariantFloat(CoordToMils(FillObj.X1Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.Y1Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.X2Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.Y2Location)) + ',' +
            InvariantFloat(FillObj.Rotation)
        );
        FillObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'fill_inventory.csv');
    Rpt.Free;
End;

Procedure ExportVias(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    Rpt      : TStringList;
    NetName  : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,x_mil,y_mil,x_raw,y_raw,size_mil,hole_mil,low_layer,high_layer');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NetName := '';
        If ViaObj.Net <> Nil Then NetName := ViaObj.Net.Name;
        Rpt.Add(
            CsvQuote(NetName) + ',' +
            InvariantFloat(CoordToMils(ViaObj.X)) + ',' +
            InvariantFloat(CoordToMils(ViaObj.Y)) + ',' +
            IntToStr(ViaObj.X) + ',' + IntToStr(ViaObj.Y) + ',' +
            InvariantFloat(CoordToMils(ViaObj.Size)) + ',' +
            InvariantFloat(CoordToMils(ViaObj.HoleSize)) + ',' +
            IntToStr(Ord(ViaObj.LowLayer)) + ',' +
            IntToStr(Ord(ViaObj.HighLayer))
        );
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'via_inventory.csv');
    Rpt.Free;
End;

Procedure ExportRoutingGeometry;
Var
    Board    : IPCB_Board;
    BasePath : String;
Begin
    Board := ResolveNativeBoard;
    If Board = Nil Then
    Begin
        ShowMessage('Routing audit: select the PCB-A10 signal candidate first.');
        Exit;
    End;
    BasePath := ExtractFilePath(Board.FileName) + '..\routing\signal_candidate\';
    ExportPads(Board, BasePath);
    ExportTracks(Board, BasePath);
    ExportFills(Board, BasePath);
    ExportVias(Board, BasePath);
    ShowMessage('Signal-candidate routing geometry exported.');
End;
