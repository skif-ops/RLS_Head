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

Function CsvField(Line : String; FieldIndex : Integer) : String;
Var
    I        : Integer;
    Current  : Integer;
    StartPos : Integer;
    InQuotes : Boolean;
    Ch       : Char;
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

Function PinElectricalPoint(Pin : ISch_Pin) : TLocation;
Begin
    Result := Pin.Location;
    Case Pin.Orientation Of
        0 : Result.X := Result.X + Pin.PinLength;
        1 : Result.Y := Result.Y + Pin.PinLength;
        2 : Result.X := Result.X - Pin.PinLength;
        3 : Result.Y := Result.Y - Pin.PinLength;
    End;
End;

Function SamePoint(A, B : TLocation) : Boolean;
Begin
    Result := (Abs(A.X - B.X) <= MilsToCoord(1)) And
        (Abs(A.Y - B.Y) <= MilsToCoord(1));
End;

Function HasObjectAt(Doc : ISch_Document; ObjectId : Integer;
    P : TLocation) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(ObjectId));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            If SamePoint(Obj.Location, P) Then
            Begin
                Result := True;
                Exit;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function HasWireVertexAt(Doc : ISch_Document; P : TLocation) : Boolean;
Var
    Iterator : ISch_Iterator;
    Wire     : ISch_Wire;
    I        : Integer;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eWire));
    Try
        Wire := Iterator.FirstSchObject;
        While Wire <> Nil Do
        Begin
            For I := 1 To Wire.GetState_VerticesCount Do
                If SamePoint(Wire.GetState_Vertex(I), P) Then
                Begin
                    Result := True;
                    Exit;
                End;
            Wire := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function HasElectricalConnectionAt(Doc : ISch_Document;
    P : TLocation) : Boolean;
Begin
    Result := HasWireVertexAt(Doc, P) Or
        HasObjectAt(Doc, eNetLabel, P) Or
        HasObjectAt(Doc, ePort, P);
End;

Function RemoveZeroLengthWires(Doc : ISch_Document) : Integer;
Var
    Iterator : ISch_Iterator;
    Wire     : ISch_Wire;
    NextWire : ISch_Wire;
    A, B     : TLocation;
Begin
    Result := 0;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eWire));
    Try
        Wire := Iterator.FirstSchObject;
        While Wire <> Nil Do
        Begin
            NextWire := Iterator.NextSchObject;
            If Wire.GetState_VerticesCount >= 2 Then
            Begin
                A := Wire.GetState_Vertex(1);
                B := Wire.GetState_Vertex(2);
                If SamePoint(A, B) Then
                Begin
                    Doc.RemoveSchObject(Wire);
                    SchServer.RobotManager.SendMessage(
                        Doc.I_ObjectAddress, c_BroadCast,
                        SCHM_PrimitiveRegistration, Wire.I_ObjectAddress);
                    Result := Result + 1;
                End;
            End;
            Wire := NextWire;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure RegisterObject(Doc : ISch_Document; Obj : ISch_BasicContainer);
Begin
    Doc.RegisterSchObjectInContainer(Obj);
    SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
        SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
End;

Procedure AddNoERC(Doc : ISch_Document; P : TLocation);
Var
    Directive : ISch_GraphicalObject;
Begin
    Directive := SchServer.SchObjectFactory(eNoERC, eCreate_GlobalCopy);
    If Directive = Nil Then Exit;
    Directive.Location := P;
    Directive.Color := $000000FF;
    RegisterObject(Doc, Directive);
End;

Procedure AddWire(Doc : ISch_Document; A, B : TLocation);
Var
    Wire : ISch_Wire;
Begin
    Wire := SchServer.SchObjectFactory(eWire, eCreate_GlobalCopy);
    If Wire = Nil Then Exit;
    Wire.SetState_VerticesCount(2);
    Wire.SetState_Vertex(1, A);
    Wire.SetState_Vertex(2, B);
    Wire.Color := $00008000;
    Wire.LineWidth := eSmall;
    RegisterObject(Doc, Wire);
End;

Procedure AddNetLabel(Doc : ISch_Document; Text : String; P : TLocation);
Var
    LabelObj : ISch_NetLabel;
Begin
    LabelObj := SchServer.SchObjectFactory(eNetLabel, eCreate_GlobalCopy);
    If LabelObj = Nil Then Exit;
    LabelObj.Location := P;
    LabelObj.Text := Text;
    LabelObj.Color := $00008000;
    LabelObj.Orientation := eRotate0;
    LabelObj.Justification := eJustify_BottomLeft;
    LabelObj.FontID := SchServer.FontManager.GetFontID(8, 0, False, False,
        False, False, 'Arial');
    RegisterObject(Doc, LabelObj);
End;

Procedure AddGroundStub(Doc : ISch_Document; Pin : ISch_Pin);
Var
    StartPoint : TLocation;
    EndPoint   : TLocation;
    StubLength : TCoord;
Begin
    StartPoint := PinElectricalPoint(Pin);
    StubLength := MilsToCoord(200);
    Case Pin.Orientation Of
        0 : EndPoint := Point(StartPoint.X + StubLength, StartPoint.Y);
        1 : EndPoint := Point(StartPoint.X, StartPoint.Y + StubLength);
        2 : EndPoint := Point(StartPoint.X - StubLength, StartPoint.Y);
        3 : EndPoint := Point(StartPoint.X, StartPoint.Y - StubLength);
    Else
        EndPoint := Point(StartPoint.X, StartPoint.Y);
    End;
    AddWire(Doc, StartPoint, EndPoint);
    AddNetLabel(Doc, 'GND', EndPoint);
End;

Function HasNetLabelTextAt(Doc : ISch_Document; P : TLocation;
    LabelText : String) : Boolean;
Var
    Iterator : ISch_Iterator;
    LabelObj : ISch_NetLabel;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNetLabel));
    Try
        LabelObj := Iterator.FirstSchObject;
        While LabelObj <> Nil Do
        Begin
            If SamePoint(LabelObj.Location, P) And
               SameText(LabelObj.Text, LabelText) Then
            Begin
                Result := True;
                Exit;
            End;
            LabelObj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function NormalizeRadU2Pin7(Doc : ISch_Document; Pin : ISch_Pin) : Boolean;
Var
    Iterator    : ISch_Iterator;
    Wire        : ISch_Wire;
    NextWire    : ISch_Wire;
    LabelIter   : ISch_Iterator;
    LabelObj    : ISch_NetLabel;
    NextLabel   : ISch_NetLabel;
    Hotspot     : TLocation;
    OtherPoint  : TLocation;
    A, B        : TLocation;
    StubRemoved : Boolean;
Begin
    Result := False;
    StubRemoved := False;
    Hotspot := PinElectricalPoint(Pin);
    OtherPoint := Hotspot;

    Iterator := Doc.SchIterator_Create;
    If Iterator <> Nil Then
    Begin
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(eWire));
        Try
            Wire := Iterator.FirstSchObject;
            While Wire <> Nil Do
            Begin
                NextWire := Iterator.NextSchObject;
                If Wire.GetState_VerticesCount = 2 Then
                Begin
                    A := Wire.GetState_Vertex(1);
                    B := Wire.GetState_Vertex(2);
                    If SamePoint(A, Hotspot) Then OtherPoint := B
                    Else If SamePoint(B, Hotspot) Then OtherPoint := A
                    Else
                    Begin
                        Wire := NextWire;
                        Continue;
                    End;

                    If HasNetLabelTextAt(Doc, OtherPoint,
                        'TI_NetR4_2') Then
                    Begin
                        Doc.RemoveSchObject(Wire);
                        SchServer.RobotManager.SendMessage(
                            Doc.I_ObjectAddress, c_BroadCast,
                            SCHM_PrimitiveRegistration,
                            Wire.I_ObjectAddress);
                        StubRemoved := True;
                        Result := True;
                    End;
                End;
                Wire := NextWire;
            End;
        Finally
            Doc.SchIterator_Destroy(Iterator);
        End;
    End;

    If StubRemoved Then
    Begin
        LabelIter := Doc.SchIterator_Create;
        If LabelIter <> Nil Then
        Begin
            LabelIter.SetState_IterationDepth(eIterateFirstLevel);
            LabelIter.AddFilter_ObjectSet(MkSet(eNetLabel));
            Try
                LabelObj := LabelIter.FirstSchObject;
                While LabelObj <> Nil Do
                Begin
                    NextLabel := LabelIter.NextSchObject;
                    If SamePoint(LabelObj.Location, OtherPoint) And
                       SameText(LabelObj.Text, 'TI_NetR4_2') Then
                    Begin
                        Doc.RemoveSchObject(LabelObj);
                        SchServer.RobotManager.SendMessage(
                            Doc.I_ObjectAddress, c_BroadCast,
                            SCHM_PrimitiveRegistration,
                            LabelObj.I_ObjectAddress);
                    End;
                    LabelObj := NextLabel;
                End;
            Finally
                Doc.SchIterator_Destroy(LabelIter);
            End;
        End;
    End;

    If Not HasObjectAt(Doc, eNoERC, Hotspot) Then
    Begin
        AddNoERC(Doc, Hotspot);
        Result := True;
    End;
End;

Function FindManifestRow(Rows : TStringList; Ref, PinNumber : String) : Integer;
Var
    I : Integer;
Begin
    Result := -1;
    For I := 1 To Rows.Count - 1 Do
        If SameText(CsvField(Rows[I], 0), Ref) And
           SameText(CsvField(Rows[I], 1), PinNumber) Then
        Begin
            Result := I;
            Exit;
        End;
End;

Procedure ApplyR9OpenPinDispositions;
Var
    Project       : IProject;
    LogicalDoc    : IDocument;
    ServerDoc     : IServerDocument;
    SchDoc        : ISch_Document;
    Components    : ISch_Iterator;
    Pins          : ISch_Iterator;
    Component     : ISch_Component;
    Pin           : ISch_Pin;
    Rows          : TStringList;
    Audit         : TStringList;
    FoundCounts   : Array[0..500] Of Integer;
    I, RowIndex   : Integer;
    Ref           : String;
    PinNumber     : String;
    Disposition   : String;
    Suppress      : String;
    Hotspot       : TLocation;
    BasePath      : String;
    ManifestPath  : String;
    AuditPath     : String;
    DetailCount   : Integer;
    MissingCount  : Integer;
    AddedNoERC    : Integer;
    ExistingNoERC : Integer;
    AddedGround   : Integer;
    ExistingWire  : Integer;
    RemovedZeroLength : Integer;
    RemovedOnSheet : Integer;
    SaveFailures  : Integer;
    ModifiedDoc   : Boolean;
Begin
    Project := FindR9Project;
    If Project = Nil Then
    Begin
        ShowMessage('Open RADAR_D79_24V_R9.PrjPcb before running this script.');
        Exit;
    End;

    BasePath := ExtractFilePath(Project.DM_ProjectFullPath);
    ManifestPath := BasePath + 'R9_open_pin_dispositions.csv';
    AuditPath := BasePath + 'R9_open_pin_disposition_application.csv';
    If Not FileExists(ManifestPath) Then
    Begin
        ShowMessage('Missing manifest: ' + ManifestPath);
        Exit;
    End;

    Rows := TStringList.Create;
    Audit := TStringList.Create;
    Rows.LoadFromFile(ManifestPath);
    For I := Rows.Count - 1 DownTo 0 Do
        If Trim(Rows[I]) = '' Then Rows.Delete(I);
    Audit.Add('Sheet,Ref,Pin,Disposition,Application');
    If Rows.Count <> 181 Then
    Begin
        ShowMessage('Expected 180 manifest rows, found ' +
            IntToStr(Rows.Count - 1) + '. No changes were made.');
        Rows.Free;
        Audit.Free;
        Exit;
    End;

    For I := 0 To 500 Do FoundCounts[I] := 0;
    DetailCount := 0;

    { The preflight must find every reviewed pin exactly once before mutation. }
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc = Nil) Or
           (LogicalDoc.DM_DocumentKind <> 'SCH') Or
           Not IsDetailSheet(ExtractFileName(LogicalDoc.DM_FullPath)) Then
            Continue;
        DetailCount := DetailCount + 1;
        SchDoc := LoadSchDocument(LogicalDoc.DM_FullPath);
        If SchDoc = Nil Then
        Begin
            ShowMessage('Preflight could not load ' +
                ExtractFileName(LogicalDoc.DM_FullPath) +
                '. No changes were made.');
            Rows.Free;
            Audit.Free;
            Exit;
        End;

        Components := SchDoc.SchIterator_Create;
        If Components = Nil Then Continue;
        Components.SetState_IterationDepth(eIterateFirstLevel);
        Components.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Components.FirstSchObject;
            While Component <> Nil Do
            Begin
                Ref := Component.Designator.Text;
                Pins := Component.SchIterator_Create;
                If Pins <> Nil Then
                Begin
                    Pins.AddFilter_ObjectSet(MkSet(ePin));
                    Try
                        Pin := Pins.FirstSchObject;
                        While Pin <> Nil Do
                        Begin
                            RowIndex := FindManifestRow(Rows, Ref,
                                Pin.Designator);
                            If RowIndex >= 1 Then
                                FoundCounts[RowIndex] :=
                                    FoundCounts[RowIndex] + 1;
                            Pin := Pins.NextSchObject;
                        End;
                    Finally
                        Component.SchIterator_Destroy(Pins);
                    End;
                End;
                Component := Components.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Components);
        End;
    End;

    MissingCount := 0;
    If DetailCount <> 31 Then MissingCount := MissingCount + 1;
    For I := 1 To Rows.Count - 1 Do
        If FoundCounts[I] <> 1 Then
        Begin
            MissingCount := MissingCount + 1;
            Audit.Add(','
                + CsvField(Rows[I], 0) + ','
                + CsvField(Rows[I], 1) + ','
                + CsvField(Rows[I], 3) + ',PREFLIGHT_COUNT_'
                + IntToStr(FoundCounts[I]));
        End;
    If MissingCount <> 0 Then
    Begin
        Audit.SaveToFile(AuditPath);
        ShowMessage('Open-pin repair preflight failed. Detail sheets: ' +
            IntToStr(DetailCount) + ', failed checks: ' +
            IntToStr(MissingCount) + '. No changes were made.');
        Rows.Free;
        Audit.Free;
        Exit;
    End;

    AddedNoERC := 0;
    ExistingNoERC := 0;
    AddedGround := 0;
    ExistingWire := 0;
    RemovedZeroLength := 0;
    SaveFailures := 0;

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc = Nil) Or
           (LogicalDoc.DM_DocumentKind <> 'SCH') Or
           Not IsDetailSheet(ExtractFileName(LogicalDoc.DM_FullPath)) Then
            Continue;
        SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
        If SchDoc = Nil Then Continue;
        ModifiedDoc := False;
        SchServer.ProcessControl.PreProcess(SchDoc, '');
        Try
            RemovedOnSheet := RemoveZeroLengthWires(SchDoc);
            If RemovedOnSheet > 0 Then
            Begin
                RemovedZeroLength := RemovedZeroLength + RemovedOnSheet;
                ModifiedDoc := True;
            End;
            Components := SchDoc.SchIterator_Create;
            If Components = Nil Then Continue;
            Components.SetState_IterationDepth(eIterateFirstLevel);
            Components.AddFilter_ObjectSet(MkSet(eSchComponent));
            Try
                Component := Components.FirstSchObject;
                While Component <> Nil Do
                Begin
                    Ref := Component.Designator.Text;
                    Pins := Component.SchIterator_Create;
                    If Pins <> Nil Then
                    Begin
                        Pins.AddFilter_ObjectSet(MkSet(ePin));
                        Try
                            Pin := Pins.FirstSchObject;
                            While Pin <> Nil Do
                            Begin
                                PinNumber := Pin.Designator;
                                If SameText(Ref, 'RAD_U2') And
                                   (PinNumber = '7') Then
                                    If NormalizeRadU2Pin7(SchDoc, Pin) Then
                                    Begin
                                        ModifiedDoc := True;
                                        Audit.Add(
                                            ExtractFileName(
                                                LogicalDoc.DM_FullPath)
                                            + ',RAD_U2,7,INTENTIONAL_NC,'
                                            + 'STUB_REMOVED_OR_NC_ADDED');
                                    End;
                                RowIndex := FindManifestRow(Rows, Ref,
                                    PinNumber);
                                If RowIndex >= 1 Then
                                Begin
                                    Disposition := UpperCase(
                                        CsvField(Rows[RowIndex], 3));
                                    Suppress := UpperCase(
                                        CsvField(Rows[RowIndex], 4));
                                    Hotspot := PinElectricalPoint(Pin);
                                    If Disposition = 'CONNECT_GND' Then
                                    Begin
                                        If HasElectricalConnectionAt(
                                            SchDoc, Hotspot) Then
                                        Begin
                                            ExistingWire :=
                                                ExistingWire + 1;
                                            Audit.Add(
                                                ExtractFileName(
                                                    LogicalDoc.DM_FullPath)
                                                + ',' + Ref + ','
                                                + PinNumber + ','
                                                + Disposition
                                                + ',EXISTING_CONNECTION');
                                        End
                                        Else
                                        Begin
                                            AddGroundStub(SchDoc, Pin);
                                            AddedGround := AddedGround + 1;
                                            ModifiedDoc := True;
                                            Audit.Add(
                                                ExtractFileName(
                                                    LogicalDoc.DM_FullPath)
                                                + ',' + Ref + ','
                                                + PinNumber + ','
                                                + Disposition
                                                + ',GND_ADDED');
                                        End;
                                    End
                                    Else If Suppress = 'YES' Then
                                    Begin
                                        If HasElectricalConnectionAt(
                                            SchDoc, Hotspot) Then
                                            Audit.Add(
                                                ExtractFileName(
                                                    LogicalDoc.DM_FullPath)
                                                + ',' + Ref + ','
                                                + PinNumber + ','
                                                + Disposition
                                                + ',SKIPPED_CONNECTED')
                                        Else If HasObjectAt(SchDoc,
                                            eNoERC, Hotspot) Then
                                        Begin
                                            ExistingNoERC :=
                                                ExistingNoERC + 1;
                                            Audit.Add(
                                                ExtractFileName(
                                                    LogicalDoc.DM_FullPath)
                                                + ',' + Ref + ','
                                                + PinNumber + ','
                                                + Disposition
                                                + ',EXISTING_NOERC');
                                        End
                                        Else
                                        Begin
                                            AddNoERC(SchDoc, Hotspot);
                                            AddedNoERC := AddedNoERC + 1;
                                            ModifiedDoc := True;
                                            Audit.Add(
                                                ExtractFileName(
                                                    LogicalDoc.DM_FullPath)
                                                + ',' + Ref + ','
                                                + PinNumber + ','
                                                + Disposition
                                                + ',NOERC_ADDED');
                                        End;
                                    End;
                                End;
                                Pin := Pins.NextSchObject;
                            End;
                        Finally
                            Component.SchIterator_Destroy(Pins);
                        End;
                    End;
                    Component := Components.NextSchObject;
                End;
            Finally
                SchDoc.SchIterator_Destroy(Components);
            End;
        Finally
            SchServer.ProcessControl.PostProcess(SchDoc, '');
        End;

        If ModifiedDoc Then
        Begin
            SchDoc.GraphicallyInvalidate;
            ServerDoc := Client.GetDocumentByPath(LogicalDoc.DM_FullPath);
            If ServerDoc <> Nil Then
            Begin
                ServerDoc.Modified := True;
                If Not ServerDoc.DoFileSave('Advanced Schematic binary') Then
                    SaveFailures := SaveFailures + 1;
            End
            Else
                SaveFailures := SaveFailures + 1;
            Application.ProcessMessages;
        End;
    End;

    Audit.SaveToFile(AuditPath);
    Rows.Free;
    Audit.Free;
    ShowMessage('Open-pin dispositions applied. NoERC added: ' +
        IntToStr(AddedNoERC) + ', existing: ' +
        IntToStr(ExistingNoERC) + ', GND connections added: ' +
        IntToStr(AddedGround) + ', existing connections: ' +
        IntToStr(ExistingWire) + ', save failures: ' +
        IntToStr(SaveFailures) + ', zero-length wires removed: ' +
        IntToStr(RemovedZeroLength) + '.');
End;
