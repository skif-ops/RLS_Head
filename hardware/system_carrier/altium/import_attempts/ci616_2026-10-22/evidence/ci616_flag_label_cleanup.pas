Function FindCI616Project : IProject;
Var
    WS : IWorkspace;
    Candidate : IProject;
    I, Count : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Count := 0;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Candidate := WS.DM_Projects(I);
        If Candidate = Nil Then Continue;
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER_CI616.PrjPcb' Then Continue;
        If Pos('ci616-qualified', LowerCase(Candidate.DM_ProjectFullPath)) = 0 Then Continue;
        Count := Count + 1;
        Result := Candidate;
    End;
    If Count <> 1 Then Result := Nil;
End;

Function TargetIndex(SheetName : String; XMil, YMil : Integer) : Integer;
Begin
    Result := -1;
    If SheetName = '10_POWER_INPUT.SchDoc' Then
    Begin
        If (XMil = 1550) And (YMil = 5250) Then Result := 0;
        If (XMil = 1200) And (YMil = 800) Then Result := 1;
    End;
    If SheetName = '20_MCU_CORE.SchDoc' Then
    Begin
        If (XMil = 2300) And (YMil = 9200) Then Result := 2;
        If (XMil = 3200) And (YMil = 9200) Then Result := 3;
    End;
    If SheetName = '30_TIME_GNSS.SchDoc' Then
    Begin
        If (XMil = 6350) And (YMil = 3700) Then Result := 4;
        If (XMil = 6350) And (YMil = 3950) Then Result := 5;
    End;
End;

Function TargetNet(Index : Integer) : String;
Begin
    Result := '';
    Case Index Of
        0: Result := 'VIN_RAW';
        1: Result := 'GND';
        2: Result := '3V3';
        3: Result := 'VDDA_FILTERED';
        4: Result := 'GNSS_BCKP_LOCAL';
        5: Result := 'GNSS_VUSB_LOCAL';
    End;
End;

Function FindObjectAtTarget(Doc : ISch_Document; SheetName : String;
    Target, Kind : Integer) : ISch_GraphicalObject;
Var
    Iterator : ISch_Iterator;
    Obj : ISch_GraphicalObject;
    Component : ISch_Component;
    K, XMil, YMil : Integer;
Begin
    Result := Nil;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eSchComponent, eNetLabel));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            XMil := -1;
            YMil := -1;
            If Obj.ObjectId = eSchComponent Then
            Begin
                Component := Obj;
                XMil := Round(CoordToMils(Component.Location.X));
                YMil := Round(CoordToMils(Component.Location.Y));
            End;
            If Obj.ObjectId = eNetLabel Then
            Begin
                XMil := Round(CoordToMils(Obj.Location.X));
                YMil := Round(CoordToMils(Obj.Location.Y));
            End;
            K := TargetIndex(SheetName, XMil, YMil);
            If K = Target Then
            Begin
                If (Kind = 1) And (Obj.ObjectId = eSchComponent) Then
                    If Component.LibReference = 'PWR_FLAG' Then
                        Result := Obj;
                If (Kind = 2) And (Obj.ObjectId = eNetLabel) Then
                    Result := Obj;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure RemoveCI616FloatingFlagPairs;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    FlagObj, LabelObj : ISch_GraphicalObject;
    SheetName : String;
    I, K, Matches : Integer;
Begin
    Project := FindCI616Project;
    If Project = Nil Then
    Begin
        ShowMessage('CI616 cleanup stopped: qualified project not unique.');
        Exit;
    End;

    Matches := 0;
    For K := 0 To 5 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Project.DM_LogicalDocuments(I);
            If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
            If Pos('ci616-qualified', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then Continue;
            FlagObj := FindObjectAtTarget(SchDoc, SheetName, K, 1);
            LabelObj := FindObjectAtTarget(SchDoc, SheetName, K, 2);
            If (FlagObj <> Nil) And (LabelObj <> Nil) Then Matches := Matches + 1;
        End;
    End;
    If Matches <> 6 Then
    Begin
        ShowMessage('CI616 cleanup stopped: expected six exact flag/label pairs, found ' + IntToStr(Matches));
        Exit;
    End;

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
        SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
        If (SheetName <> '10_POWER_INPUT.SchDoc') And
           (SheetName <> '20_MCU_CORE.SchDoc') And
           (SheetName <> '30_TIME_GNSS.SchDoc') Then Continue;
        SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
        If SchDoc = Nil Then Continue;
        SchServer.ProcessControl.PreProcess(SchDoc, '');
        Try
            For K := 0 To 5 Do
            Begin
                LabelObj := FindObjectAtTarget(SchDoc, SheetName, K, 2);
                If LabelObj <> Nil Then
                Begin
                    SchDoc.RemoveSchObject(LabelObj);
                    SchServer.RobotManager.SendMessage(SchDoc.I_ObjectAddress,
                        c_BroadCast, SCHM_PrimitiveRegistration, LabelObj.I_ObjectAddress);
                End;
                FlagObj := FindObjectAtTarget(SchDoc, SheetName, K, 1);
                If FlagObj <> Nil Then
                Begin
                    SchDoc.RemoveSchObject(FlagObj);
                    SchServer.RobotManager.SendMessage(SchDoc.I_ObjectAddress,
                        c_BroadCast, SCHM_PrimitiveRegistration, FlagObj.I_ObjectAddress);
                End;
            End;
        Finally
            SchServer.ProcessControl.PostProcess(SchDoc, '');
        End;
        SchDoc.GraphicallyInvalidate;
    End;
    ShowMessage('Removed six CI616 imported PWR_FLAG/label pairs. Save documents and validate.');
End;
