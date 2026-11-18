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

    SchServer.ProcessControl.PreProcess(TargetDoc, '');
    Try
        ClearCurrentSheet(TargetDoc);
        TargetDoc.UseCustomSheet := True;
        TargetDoc.CustomSheetStyle := 'R9 Full Element 3600 x 1400 mm';
        TargetDoc.CustomX := Mm(3600);
        TargetDoc.CustomY := Mm(1400);
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
            20, 1373, 24, True, $00202020);
        AddLabel(TargetDoc,
            'All 31 native schematic sheets flattened at 1:1 scale. RF tract and eight 8-element antenna arrays are shown in tile RF.',
            20, 1353, 14, False, $00404040);
        AddLabel(TargetDoc,
            'Civil drone tracking system. Measurement and target-state output only.',
            20, 1337, 12, False, $00404040);

        For TileIndex := 0 To 31 Do
        Begin
            ColIndex := TileIndex Mod 8;
            RowIndex := TileIndex Div 8;
            X0 := 20.0 + ColIndex * 445.0;
            Y0 := 1020.0 - RowIndex * 325.0;
            AddRectangle(TargetDoc, X0, Y0, X0 + 435.0, Y0 + 310.0,
                $00707070, $00FFFFFF, False, eSmall);
        End;

        AddRfAntennaTile(TargetDoc, 20.0, 1020.0);

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
            Y0 := 1020.0 - RowIndex * 325.0;

            AddLabel(TargetDoc, SourceName, X0 + 8.0, Y0 + 292.0,
                11, True, $00303030);
            OffsetX := Mm(X0 + 8.0) - MinX;
            OffsetY := Mm(Y0 + 8.0) - MinY;
            PrimitiveCount := PrimitiveCount +
                ReplicateSheet(SourceDoc, TargetDoc, OffsetX, OffsetY);
        End;
    Finally
        SchServer.ProcessControl.PostProcess(TargetDoc, '');
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
    ShowMessage('Full element master sheet saved. Replicated primitives: ' +
        IntToStr(PrimitiveCount) + '.');
End;
