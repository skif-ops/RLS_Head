{ Export connection and geometry evidence from the canonical native PcbDoc.
  Run procedure: ExportConnectionIntegrity
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

Function IsCanonicalBoardPath(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (ExtractFileName(P) = 'evt_sys_carrier.pcbdoc') And
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0);
End;

Function ResolveCanonicalBoard : IPCB_Board;
Var
    Project : IProject;
    Doc     : IDocument;
    PcbDoc  : IServerDocument;
    I       : Integer;
    J       : Integer;
    WS      : IWorkspace;
    CanonicalPath : String;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If Result <> Nil Then
        If IsCanonicalBoardPath(Result.FileName) Then Exit;
    Result := Nil;

    WS := GetWorkspace;
    If WS = Nil Then Exit;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Project := WS.DM_Projects(I);
        If Project = Nil Then Continue;
        If ExtractFileName(Project.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER_ConnectionAudit.PrjScr' Then Continue;
        CanonicalPath := ExtractFilePath(Project.DM_ProjectFullPath) + 'EVT_SYS_CARRIER.PcbDoc';
        Result := PCBServer.GetPCBBoardByPath(CanonicalPath);
        If Result <> Nil Then Exit;
        PcbDoc := Client.OpenDocument('PCB', CanonicalPath);
        If PcbDoc = Nil Then Continue;
        Client.ShowDocument(PcbDoc);
        Result := PCBServer.GetPCBBoardByPath(CanonicalPath);
        If Result <> Nil Then Exit;
    End;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Project := WS.DM_Projects(I);
        If Project = Nil Then Continue;
        If ExtractFileName(Project.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        For J := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Project.DM_LogicalDocuments(J);
            If Doc = Nil Then Continue;
            If Not IsCanonicalBoardPath(Doc.DM_FullPath) Then Continue;
            Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
            If Result <> Nil Then Exit;
            PcbDoc := Client.OpenDocument('PCB', Doc.DM_FullPath);
            If PcbDoc = Nil Then Continue;
            Client.ShowDocument(PcbDoc);
            Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
            Exit;
        End;
    End;
End;

Function RectFields(R : TCoordRect) : String;
Begin
    Result :=
        InvariantFloat(CoordToMils(R.Left)) + ',' +
        InvariantFloat(CoordToMils(R.Bottom)) + ',' +
        InvariantFloat(CoordToMils(R.Right)) + ',' +
        InvariantFloat(CoordToMils(R.Top));
End;

Procedure ExportComponents(Board : IPCB_Board; BasePath : String);
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
    Rpt       : TStringList;
    R         : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pattern,x_mil,y_mil,rotation_deg,layer,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        R := Component.BoundingRectangle;
        Rpt.Add(
            CsvQuote(Component.SourceDesignator) + ',' +
            CsvQuote(Component.Pattern) + ',' +
            InvariantFloat(CoordToMils(Component.X)) + ',' +
            InvariantFloat(CoordToMils(Component.Y)) + ',' +
            InvariantFloat(Component.Rotation) + ',' +
            IntToStr(Ord(Component.Layer)) + ',' + RectFields(R)
        );
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'component_bounds.csv');
    Rpt.Free;
End;

Procedure ExportPads(Board : IPCB_Board; BasePath : String);
Var
    Iterator   : IPCB_BoardIterator;
    Pad        : IPCB_Pad;
    Rpt        : TStringList;
    Designator : String;
    NetName    : String;
    R          : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pad_name,net_name,x_mil,y_mil,layer,hole_mil,x_size_mil,y_size_mil,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        Designator := '';
        NetName := '';
        If Pad.Component <> Nil Then Designator := Pad.Component.SourceDesignator;
        If Pad.Net <> Nil Then NetName := Pad.Net.Name;
        R := Pad.BoundingRectangle;
        Rpt.Add(
            CsvQuote(Designator) + ',' + CsvQuote(Pad.Name) + ',' +
            CsvQuote(NetName) + ',' + InvariantFloat(CoordToMils(Pad.X)) + ',' +
            InvariantFloat(CoordToMils(Pad.Y)) + ',' + IntToStr(Ord(Pad.Layer)) + ',' +
            InvariantFloat(CoordToMils(Pad.HoleSize)) + ',' +
            InvariantFloat(CoordToMils(Pad.TopXSize)) + ',' +
            InvariantFloat(CoordToMils(Pad.TopYSize)) + ',' + RectFields(R)
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
    R        : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,width_mil,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Track := Iterator.FirstPCBObject;
    While Track <> Nil Do
    Begin
        NetName := '';
        If Track.Net <> Nil Then NetName := Track.Net.Name;
        R := Track.BoundingRectangle;
        Rpt.Add(
            CsvQuote(NetName) + ',' + IntToStr(Ord(Track.Layer)) + ',' +
            InvariantFloat(CoordToMils(Track.X1)) + ',' +
            InvariantFloat(CoordToMils(Track.Y1)) + ',' +
            InvariantFloat(CoordToMils(Track.X2)) + ',' +
            InvariantFloat(CoordToMils(Track.Y2)) + ',' +
            InvariantFloat(CoordToMils(Track.Width)) + ',' + RectFields(R)
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
    R        : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,layer,x1_mil,y1_mil,x2_mil,y2_mil,rotation_deg,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eFillObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    FillObj := Iterator.FirstPCBObject;
    While FillObj <> Nil Do
    Begin
        NetName := '';
        If FillObj.Net <> Nil Then NetName := FillObj.Net.Name;
        R := FillObj.BoundingRectangle;
        Rpt.Add(
            CsvQuote(NetName) + ',' + IntToStr(Ord(FillObj.Layer)) + ',' +
            InvariantFloat(CoordToMils(FillObj.X1Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.Y1Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.X2Location)) + ',' +
            InvariantFloat(CoordToMils(FillObj.Y2Location)) + ',' +
            InvariantFloat(FillObj.Rotation) + ',' + RectFields(R)
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
    R        : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name,x_mil,y_mil,size_mil,hole_mil,low_layer,high_layer,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NetName := '';
        If ViaObj.Net <> Nil Then NetName := ViaObj.Net.Name;
        R := ViaObj.BoundingRectangle;
        Rpt.Add(
            CsvQuote(NetName) + ',' +
            InvariantFloat(CoordToMils(ViaObj.X)) + ',' +
            InvariantFloat(CoordToMils(ViaObj.Y)) + ',' +
            InvariantFloat(CoordToMils(ViaObj.Size)) + ',' +
            InvariantFloat(CoordToMils(ViaObj.HoleSize)) + ',' +
            IntToStr(Ord(ViaObj.LowLayer)) + ',' +
            IntToStr(Ord(ViaObj.HighLayer)) + ',' + RectFields(R)
        );
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'via_inventory.csv');
    Rpt.Free;
End;

Procedure ExportConnectionIntegrity;
Var
    Board    : IPCB_Board;
    BasePath : String;
Begin
    Board := ResolveCanonicalBoard;
    If Board = Nil Then
    Begin
        ShowMessage('Connection audit: open the canonical EVT_SYS_CARRIER.PcbDoc first.');
        Exit;
    End;
    BasePath := ExtractFilePath(Board.FileName) + '..\routing\connection_audit\';
    ForceDirectories(BasePath);
    ExportComponents(Board, BasePath);
    ExportPads(Board, BasePath);
    ExportTracks(Board, BasePath);
    ExportFills(Board, BasePath);
    ExportVias(Board, BasePath);
    ShowMessage('Connection audit exported for the canonical PcbDoc.');
End;
