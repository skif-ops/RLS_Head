Function Mm(ValueMm : Double) : TCoord;
Begin
    Result := MMsToCoord(ValueMm);
End;

Function FindR9Project : IProject;
Var
    WS : IWorkspace;
    I  : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    For I := 0 To WS.DM_ProjectCount - 1 Do
        If ExtractFileName(WS.DM_Projects(I).DM_ProjectFullPath) =
            'RADAR_D79_24V_R9.PrjPcb' Then
        Begin
            Result := WS.DM_Projects(I);
            Exit;
        End;
End;

Procedure RegisterObject(Doc : ISch_Document; Obj : ISch_BasicContainer);
Begin
    Doc.RegisterSchObjectInContainer(Obj);
    SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
        SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
End;

Procedure AddLabel(Doc : ISch_Document; S : WideString; Xmm, Ymm : Double;
    FontSize : Integer; Bold : Boolean; TextColor : TColor);
Var
    L : ISch_Label;
Begin
    L := SchServer.SchObjectFactory(eLabel, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(Xmm), Mm(Ymm));
    L.Text := S;
    L.Color := TextColor;
    L.Orientation := eRotate0;
    L.FontID := SchServer.FontManager.GetFontID(FontSize, 0, Bold, False,
        False, False, 'Arial');
    RegisterObject(Doc, L);
End;

Procedure AddLine(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    LineColor : TColor; LineWidth : TSize);
Var
    L : ISch_Line;
Begin
    L := SchServer.SchObjectFactory(eLine, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(X1), Mm(Y1));
    L.Corner := Point(Mm(X2), Mm(Y2));
    L.Color := LineColor;
    L.LineWidth := LineWidth;
    RegisterObject(Doc, L);
End;

Procedure AddWire(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    WireColor : TColor; WireWidth : TSize);
Var
    W : ISch_Wire;
Begin
    W := SchServer.SchObjectFactory(eWire, eCreate_GlobalCopy);
    If W = Nil Then Exit;
    W.SetState_VerticesCount(2);
    W.SetState_Vertex(1, Point(Mm(X1), Mm(Y1)));
    W.SetState_Vertex(2, Point(Mm(X2), Mm(Y2)));
    W.Color := WireColor;
    W.LineWidth := WireWidth;
    RegisterObject(Doc, W);
End;

Procedure AddNetLabel(Doc : ISch_Document; S : WideString; Xmm, Ymm : Double;
    FontSize : Integer; TextColor : TColor);
Var
    L : ISch_NetLabel;
Begin
    L := SchServer.SchObjectFactory(eNetLabel, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(Xmm), Mm(Ymm));
    L.Text := S;
    L.Color := TextColor;
    L.Orientation := eRotate0;
    L.FontID := SchServer.FontManager.GetFontID(FontSize, 0, False, False,
        False, False, 'Arial');
    RegisterObject(Doc, L);
End;

Procedure AddRectangle(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    LineColor, FillColor : TColor; Filled : Boolean; LineWidth : TSize);
Var
    R : ISch_Rectangle;
Begin
    R := SchServer.SchObjectFactory(eRectangle, eCreate_GlobalCopy);
    If R = Nil Then Exit;
    R.Location := Point(Mm(X1), Mm(Y1));
    R.Corner := Point(Mm(X2), Mm(Y2));
    R.Color := LineColor;
    R.AreaColor := FillColor;
    R.IsSolid := Filled;
    R.LineWidth := LineWidth;
    RegisterObject(Doc, R);
End;

Procedure ClearCurrentSheet(Doc : ISch_Document);
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
    Removed  : Integer;
Begin
    Removed := 0;
    While Removed < 50000 Do
    Begin
        Obj := Nil;
        Iterator := Doc.SchIterator_Create;
        If Iterator = Nil Then Exit;
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Try
            Obj := Iterator.FirstSchObject;
        Finally
            Doc.SchIterator_Destroy(Iterator);
        End;
        If Obj = Nil Then Break;
        Doc.RemoveSchObject(Obj);
        SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
            SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
        Removed := Removed + 1;
    End;
End;

Procedure AddPatchArray(Doc : ISch_Document; Xmm, Ymm : Double;
    ChannelName, PinName : String; ChannelColor : TColor);
Var
    I : Integer;
Begin
    AddLabel(Doc, ChannelName + '  ' + PinName, Xmm, Ymm + 3.0,
        10, True, ChannelColor);
    AddLine(Doc, Xmm + 55.0, Ymm + 1.0, Xmm + 75.0, Ymm + 1.0,
        ChannelColor, eSmall);
    For I := 0 To 7 Do
        AddRectangle(Doc,
            Xmm + 78.0 + I * 8.5, Ymm - 3.0,
            Xmm + 84.0 + I * 8.5, Ymm + 5.0,
            ChannelColor, ChannelColor, True, eSmall);
End;

Procedure AddRfAntennaTile(Doc : ISch_Document; X0, Y0 : Double);
Var
    RedColor  : TColor;
    BlueColor : TColor;
    DarkColor : TColor;
Begin
    RedColor := $000000C0;
    BlueColor := $00C00000;
    DarkColor := $00303030;

    AddLabel(Doc, 'RF TRACT AND PRINTED ANTENNA ARRAYS', X0 + 12.0,
        Y0 + 285.0, 13, True, DarkColor);
    AddLabel(Doc, '76 to 81 GHz / 4 TX + 4 coherent RX / eight patches per channel',
        X0 + 12.0, Y0 + 270.0, 9, False, DarkColor);
    AddRectangle(Doc, X0 + 12.0, Y0 + 35.0, X0 + 110.0, Y0 + 248.0,
        DarkColor, $00F0F0F0, True, eMedium);
    AddLabel(Doc, 'RAD_U29', X0 + 34.0, Y0 + 220.0, 12, True, DarkColor);
    AddLabel(Doc, 'AWR2944P', X0 + 28.0, Y0 + 204.0, 12, True, DarkColor);
    AddLabel(Doc, 'FMCW RF front end', X0 + 21.0, Y0 + 180.0,
        9, False, DarkColor);
    AddLabel(Doc, 'coherent TX/RX', X0 + 24.0, Y0 + 164.0,
        9, False, DarkColor);
    AddLabel(Doc, 'phase angle inputs', X0 + 22.0, Y0 + 148.0,
        9, False, DarkColor);

    AddPatchArray(Doc, X0 + 124.0, Y0 + 230.0, 'TX1', 'TI_TX1 / B3', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 204.0, 'TX2', 'TI_TX2 / B5', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 178.0, 'TX3', 'TI_TX3 / B7', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 152.0, 'TX4', 'TI_TX4 / B9', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 118.0, 'RX1', 'TI_RX1 / M2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 92.0, 'RX2', 'TI_RX2 / K2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 66.0, 'RX3', 'TI_RX3 / H2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 40.0, 'RX4', 'TI_RX4 / F2', BlueColor);

    AddLabel(Doc,
        'Controlled-impedance feeds and matching geometry are implemented in PCB copper.',
        X0 + 12.0, Y0 + 18.0, 8, False, DarkColor);
End;

Function IsDetailSheet(FileName : String) : Boolean;
Var
    N : Integer;
Begin
    Result := False;
    If Length(FileName) < 3 Then Exit;
    If FileName[3] <> '_' Then Exit;
    N := StrToIntDef(Copy(FileName, 1, 2), 0);
    Result := (N >= 1) And (N <= 31) And
        (LowerCase(ExtractFileExt(FileName)) = '.schdoc');
End;

Function LoadSchDocument(Path : String) : ISch_Document;
Var
    ServerDoc : IServerDocument;
Begin
    Result := SchServer.GetSchDocumentByPath(Path);
    If Result <> Nil Then Exit;
    ServerDoc := Client.OpenDocument('SCH', Path);
    If ServerDoc = Nil Then Exit;
    Client.ShowDocument(ServerDoc);
    Application.ProcessMessages;
    Result := SchServer.GetSchDocumentByPath(Path);
End;

Function CollectBounds(Doc : ISch_Document;
    Var MinX, MinY, MaxX, MaxY : TCoord) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
    R        : TCoordRect;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            R := Obj.BoundingRectangle_Full;
            If Not Result Then
            Begin
                MinX := R.Left;
                MinY := R.Bottom;
                MaxX := R.Right;
                MaxY := R.Top;
                Result := True;
            End
            Else
            Begin
                If R.Left < MinX Then MinX := R.Left;
                If R.Bottom < MinY Then MinY := R.Bottom;
                If R.Right > MaxX Then MaxX := R.Right;
                If R.Top > MaxY Then MaxY := R.Top;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function ReplicateSheet(SourceDoc, TargetDoc : ISch_Document;
    OffsetX, OffsetY : TCoord) : Integer;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
    NewObj   : ISch_BasicContainer;
    NewGraph : ISch_GraphicalObject;
Begin
    Result := 0;
    Iterator := SourceDoc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            NewObj := Obj.Replicate;
            If NewObj <> Nil Then
            Begin
                NewGraph := NewObj;
                NewGraph.MoveByXY(OffsetX, OffsetY);
                RegisterObject(TargetDoc, NewObj);
                Result := Result + 1;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        SourceDoc.SchIterator_Destroy(Iterator);
    End;
End;

Function CsvField(Line : String; FieldIndex : Integer) : String;
Var
    I          : Integer;
    Current    : Integer;
    StartPos   : Integer;
    InQuotes   : Boolean;
    Ch         : Char;
Begin
    Result := '';
    Current := 0;
    StartPos := 1;
    InQuotes := False;
    For I := 1 To Length(Line) + 1 Do
    Begin
        If I <= Length(Line) Then Ch := Line[I] Else Ch := ',';
        If Ch = '"' Then InQuotes := Not InQuotes;
        If (Ch = ',') And (Not InQuotes) Then
        Begin
            If Current = FieldIndex Then
            Begin
                Result := Copy(Line, StartPos, I - StartPos);
                Result := StringReplace(Result, '"', '', rfReplaceAll);
                Exit;
            End;
            Current := Current + 1;
            StartPos := I + 1;
        End;
    End;
End;

Function SheetListContains(SheetList : String; SheetNumber : Integer) : Boolean;
Var
    Token : String;
Begin
    If SheetNumber < 10 Then
        Token := '0' + IntToStr(SheetNumber)
    Else
        Token := IntToStr(SheetNumber);
    Result := Pos(';' + Token + ';', ';' + SheetList + ';') > 0;
End;

Function NetColor(NetName : String) : TColor;
Var
    U : String;
Begin
    U := UpperCase(NetName);
    If U = 'GND' Then
        Result := $00303030
    Else If (Pos('24V', U) > 0) Or (Pos('12V', U) > 0) Or
            (Pos('5V', U) > 0) Or (Pos('3V3', U) > 0) Or
            (Pos('1V', U) > 0) Then
        Result := $000000C0
    Else If (Pos('UART', U) > 0) Or (Pos('CAN', U) > 0) Or
            (Pos('USB', U) > 0) Or (Pos('GNSS', U) > 0) Or
            (Pos('IMU', U) > 0) Or (Pos('SWD', U) > 0) Then
        Result := $00C00000
    Else If Pos('TI_', U) = 1 Then
        Result := $00800080
    Else
        Result := $00606060;
End;

Procedure AddConnectivityMatrix(Doc : ISch_Document; Rows : TStringList);
Var
    I, S           : Integer;
    NetName        : String;
    SheetList      : String;
    Y              : Double;
    RowHeight      : Double;
    SheetX         : Double;
    C              : TColor;
Begin
    AddRectangle(Doc, 20.0, 20.0, 3580.0, 625.0,
        $00404040, $00FFFFFF, False, eMedium);
    AddLabel(Doc, 'INTER-SHEET ELECTRICAL CONNECTIONS / EXACT NET NAMES',
        35.0, 601.0, 13, True, $00202020);
    AddLabel(Doc,
        'Each row is an actual Altium wire with a net label. Identical labels electrically join the row to all matching endpoints in the 31 flattened sheets.',
        35.0, 584.0, 8, False, $00404040);
    AddLabel(Doc,
        'Full component-pad-to-net binding for PCB rerouting: R9_pad_binding.csv in the release verification folder.',
        35.0, 571.0, 8, False, $00404040);

    AddLabel(Doc, 'NET', 35.0, 552.0, 7, True, $00202020);
    For S := 1 To 31 Do
    Begin
        SheetX := 650.0 + (S - 1) * 94.0;
        If S < 10 Then
            AddLabel(Doc, '0' + IntToStr(S), SheetX - 2.0, 552.0,
                5, True, $00303030)
        Else
            AddLabel(Doc, IntToStr(S), SheetX - 2.0, 552.0,
                5, True, $00303030);
        AddLine(Doc, SheetX, 45.0, SheetX, 546.0,
            $00E0E0E0, eZeroSize);
    End;

    If Rows.Count <= 1 Then Exit;
    RowHeight := 500.0 / (Rows.Count - 1);
    If RowHeight > 6.0 Then RowHeight := 6.0;
    For I := 1 To Rows.Count - 1 Do
    Begin
        NetName := CsvField(Rows[I], 0);
        SheetList := CsvField(Rows[I], 1);
        If (NetName = '') Or (SheetList = '') Then Continue;
        Y := 542.0 - (I - 1) * RowHeight;
        C := NetColor(NetName);
        AddWire(Doc, 350.0, Y, 3550.0, Y, C, eSmall);
        AddNetLabel(Doc, NetName, 350.0, Y, 4, C);
        AddLabel(Doc, NetName, 35.0, Y - 1.0, 4, False, C);
        For S := 1 To 31 Do
            If SheetListContains(SheetList, S) Then
            Begin
                SheetX := 650.0 + (S - 1) * 94.0;
                AddRectangle(Doc, SheetX - 1.3, Y - 1.3,
                    SheetX + 1.3, Y + 1.3, C, C, True, eZeroSize);
            End;
    End;

    AddLabel(Doc, 'Power', 35.0, 31.0, 6, True, $000000C0);
    AddLabel(Doc, 'Interfaces', 100.0, 31.0, 6, True, $00C00000);
    AddLabel(Doc, 'AWR2944P', 190.0, 31.0, 6, True, $00800080);
    AddLabel(Doc, 'GND and other nets', 285.0, 31.0, 6, True, $00303030);
End;

Procedure PrepareFullElementSheet;
Var
    Project        : IProject;
    LogicalDoc     : IDocument;
    TargetServer   : IServerDocument;
    TargetDoc      : ISch_Document;
    SourceDoc      : ISch_Document;
    SourcePaths    : TStringList;
    BasePath       : String;
    TargetPath     : String;
    SourcePath     : String;
    SourceName     : String;
    I              : Integer;
    TileIndex      : Integer;
    RowIndex       : Integer;
    ColIndex       : Integer;
    X0, Y0         : Double;
    MinX, MinY     : TCoord;
    MaxX, MaxY     : TCoord;
    OffsetX        : TCoord;
    OffsetY        : TCoord;
    PrimitiveCount : Integer;
    Connectivity   : TStringList;
    ConnectivityPath : String;
    CrossNetCount  : Integer;
Begin
    If SchServer = Nil Then Exit;
    Project := FindR9Project;
    If Project = Nil Then
    Begin
        ShowMessage('Open RADAR_D79_24V_R9.PrjPcb before running this script.');
        Exit;
    End;

    BasePath := ExtractFilePath(Project.DM_ProjectFullPath);
    TargetPath := BasePath + '00_FULL_ELEMENT_SCHEMATIC.SchDoc';
    TargetDoc := LoadSchDocument(TargetPath);
    If TargetDoc = Nil Then
    Begin
        ShowMessage('Cannot open 00_FULL_ELEMENT_SCHEMATIC.SchDoc.');
        Exit;
    End;

    SourcePaths := TStringList.Create;
    SourcePaths.Sorted := True;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc <> Nil) And
           (LogicalDoc.DM_DocumentKind = 'SCH') And
           IsDetailSheet(ExtractFileName(LogicalDoc.DM_FullPath)) Then
            SourcePaths.Add(LogicalDoc.DM_FullPath);
    End;
    If SourcePaths.Count <> 31 Then
    Begin
        ShowMessage('Expected 31 detail sheets, found ' +
            IntToStr(SourcePaths.Count) + '. Master sheet was not changed.');
        SourcePaths.Free;
        Exit;
    End;

    ConnectivityPath := BasePath +
        'R9_master_inter_sheet_connectivity.csv';
    If Not FileExists(ConnectivityPath) Then
    Begin
        ShowMessage('Missing connectivity file: ' + ConnectivityPath +
            '. Master sheet was not changed.');
        SourcePaths.Free;
        Exit;
    End;
    Connectivity := TStringList.Create;
    Connectivity.LoadFromFile(ConnectivityPath);
    If Connectivity.Count <= 1 Then
    Begin
        ShowMessage('Connectivity file has no data. Master sheet was not changed.');
        Connectivity.Free;
        SourcePaths.Free;
        Exit;
    End;
    CrossNetCount := Connectivity.Count - 1;

    SchServer.ProcessControl.PreProcess(TargetDoc, '');
    Try
        ClearCurrentSheet(TargetDoc);
        TargetDoc.UseCustomSheet := True;
        TargetDoc.CustomSheetStyle := 'R9 Full Element 3600 x 2000 mm';
        TargetDoc.CustomX := Mm(3600);
        TargetDoc.CustomY := Mm(2000);
        TargetDoc.CustomMarginWidth := Mm(10);
        TargetDoc.BorderOn := True;
        TargetDoc.ReferenceZonesOn := False;
        TargetDoc.TitleBlockOn := False;
        TargetDoc.SnapGridOn := True;
        TargetDoc.SnapGridSize := Mm(1);
        TargetDoc.VisibleGridOn := True;
        TargetDoc.VisibleGridSize := Mm(10);

        AddLabel(TargetDoc,
            'RADAR D79 24 V / FULL ELEMENT SCHEMATIC / PCB v0.8.0 R9',
            20, 1973, 24, True, $00202020);
        AddLabel(TargetDoc,
            'All 31 native schematic sheets flattened at 1:1 scale. Complete inter-sheet electrical connectivity is shown below the sheet field.',
            20, 1953, 14, False, $00404040);
        AddLabel(TargetDoc,
            'Civil drone tracking system. Measurement and target-state output only. Production authority: NOT_AUTHORIZED.',
            20, 1937, 12, False, $00404040);

        For TileIndex := 0 To 31 Do
        Begin
            ColIndex := TileIndex Mod 8;
            RowIndex := TileIndex Div 8;
            X0 := 20.0 + ColIndex * 445.0;
            Y0 := 1620.0 - RowIndex * 325.0;
            AddRectangle(TargetDoc, X0, Y0, X0 + 435.0, Y0 + 310.0,
                $00707070, $00FFFFFF, False, eSmall);
        End;

        AddRfAntennaTile(TargetDoc, 20.0, 1620.0);

        PrimitiveCount := 0;
        For I := 0 To SourcePaths.Count - 1 Do
        Begin
            SourcePath := SourcePaths[I];
            SourceName := ExtractFileName(SourcePath);
            SourceDoc := LoadSchDocument(SourcePath);
            If SourceDoc = Nil Then Continue;
            If Not CollectBounds(SourceDoc, MinX, MinY, MaxX, MaxY) Then Continue;

            TileIndex := I + 1;
            ColIndex := TileIndex Mod 8;
            RowIndex := TileIndex Div 8;
            X0 := 20.0 + ColIndex * 445.0;
            Y0 := 1620.0 - RowIndex * 325.0;

            AddLabel(TargetDoc, SourceName, X0 + 8.0, Y0 + 292.0,
                11, True, $00303030);
            OffsetX := Mm(X0 + 8.0) - MinX;
            OffsetY := Mm(Y0 + 8.0) - MinY;
            PrimitiveCount := PrimitiveCount +
                ReplicateSheet(SourceDoc, TargetDoc, OffsetX, OffsetY);
        End;
        AddConnectivityMatrix(TargetDoc, Connectivity);
    Finally
        SchServer.ProcessControl.PostProcess(TargetDoc, '');
        Connectivity.Free;
        SourcePaths.Free;
    End;

    TargetDoc.GraphicallyInvalidate;
    TargetServer := Client.GetDocumentByPath(TargetPath);
    If TargetServer <> Nil Then
    Begin
        TargetServer.Modified := True;
        TargetServer.DoFileSave('Advanced Schematic binary');
        Client.ShowDocument(TargetServer);
    End;
    ShowMessage('Connected full element master sheet saved. Replicated primitives: ' +
        IntToStr(PrimitiveCount) + '. Cross-sheet nets: ' +
        IntToStr(CrossNetCount) + '.');
End;
