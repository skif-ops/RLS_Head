Function FindCI623Project : IProject;
Var
    WS : IWorkspace;
    Candidate : IProject;
    LogicalDoc : IDocument;
    SheetName : String;
    I, J, Score, BestScore : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    BestScore := -1;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Candidate := WS.DM_Projects(I);
        If Candidate = Nil Then Continue;
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        If Pos('\altium\native\', LowerCase(Candidate.DM_ProjectFullPath)) = 0 Then Continue;
        Score := 0;
        For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Candidate.DM_LogicalDocuments(J);
            If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
            If (SheetName <> '10_POWER_INPUT.SchDoc') And
               (SheetName <> '20_MCU_CORE.SchDoc') And
               (SheetName <> '30_TIME_GNSS.SchDoc') And
               (SheetName <> '40_IMU.SchDoc') And
               (SheetName <> '50_RADAR_IO_CAN.SchDoc') And
               (SheetName <> '60_ETHERNET.SchDoc') Then Continue;
            If SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath) <> Nil Then
                Score := Score + 1;
        End;
        If Score >= BestScore Then
        Begin
            BestScore := Score;
            Result := Candidate;
        End;
    End;
End;

Function CI623OrphanWireIndex(Wire : ISch_Wire) : Integer;
Var
    P1, P2 : TLocation;
    X1, Y1, X2, Y2 : Integer;
Begin
    Result := -1;
    If Wire = Nil Then Exit;
    If Wire.GetState_VerticesCount <> 2 Then Exit;
    P1 := Wire.GetState_Vertex(1);
    P2 := Wire.GetState_Vertex(2);
    X1 := Round(CoordToMils(P1.X));
    Y1 := Round(CoordToMils(P1.Y));
    X2 := Round(CoordToMils(P2.X));
    Y2 := Round(CoordToMils(P2.Y));
    If (((X1 = 3950) And (Y1 = 3250) And (X2 = 3950) And (Y2 = 3450)) Or
        ((X2 = 3950) And (Y2 = 3250) And (X1 = 3950) And (Y1 = 3450))) Then
        Result := 0;
    If (((X1 = 5300) And (Y1 = 1900) And (X2 = 5300) And (Y2 = 2100)) Or
        ((X2 = 5300) And (Y2 = 1900) And (X1 = 5300) And (Y1 = 2100))) Then
        Result := 1;
End;

Procedure RemoveCI623OrphanWires;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    Iterator : ISch_Iterator;
    Obj, Target : ISch_GraphicalObject;
    Wire : ISch_Wire;
    I, K, Matches, Removed : Integer;
Begin
    Project := FindCI623Project;
    If Project = Nil Then
    Begin
        ShowMessage('CI623 orphan cleanup stopped: native project not found.');
        Exit;
    End;

    SchDoc := Nil;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If LogicalDoc = Nil Then Continue;
        If ExtractFileName(LogicalDoc.DM_FullPath) <> '30_TIME_GNSS.SchDoc' Then Continue;
        If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
        SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
    End;
    If SchDoc = Nil Then
    Begin
        ShowMessage('CI623 orphan cleanup stopped: 30_TIME_GNSS.SchDoc is not loaded.');
        Exit;
    End;

    Matches := 0;
    Iterator := SchDoc.SchIterator_Create;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eWire));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            Wire := Obj;
            If CI623OrphanWireIndex(Wire) >= 0 Then Matches := Matches + 1;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        SchDoc.SchIterator_Destroy(Iterator);
    End;
    If Matches <> 2 Then
    Begin
        ShowMessage('CI623 orphan cleanup stopped: expected two exact wires, found ' + IntToStr(Matches));
        Exit;
    End;

    Removed := 0;
    For K := 0 To 1 Do
    Begin
        Target := Nil;
        Iterator := SchDoc.SchIterator_Create;
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(eWire));
        Try
            Obj := Iterator.FirstSchObject;
            While Obj <> Nil Do
            Begin
                Wire := Obj;
                If CI623OrphanWireIndex(Wire) = K Then Target := Obj;
                Obj := Iterator.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Iterator);
        End;
        If Target = Nil Then Continue;
        SchServer.ProcessControl.PreProcess(SchDoc, '');
        Try
            SchDoc.RemoveSchObject(Target);
            SchServer.RobotManager.SendMessage(SchDoc.I_ObjectAddress,
                c_BroadCast, SCHM_PrimitiveRegistration, Target.I_ObjectAddress);
            Removed := Removed + 1;
        Finally
            SchServer.ProcessControl.PostProcess(SchDoc, '');
        End;
    End;
    SchDoc.GraphicallyInvalidate;
    ShowMessage('Removed ' + IntToStr(Removed) + ' exact CI623 orphan wires. Save and validate.');
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
        If (XMil = 3450) And (YMil = 4600) Then Result := 2;
        If (XMil = 4950) And (YMil = 4600) Then Result := 3;
    End;
    If SheetName = '30_TIME_GNSS.SchDoc' Then
    Begin
        If (XMil = 5300) And (YMil = 2100) Then Result := 4;
        If (XMil = 3950) And (YMil = 3450) Then Result := 5;
    End;
End;

Function TargetLabelIndex(SheetName : String; XMil, YMil : Integer) : Integer;
Begin
    Result := TargetIndex(SheetName, XMil, YMil);
    If SheetName <> '30_TIME_GNSS.SchDoc' Then Exit;
    If (XMil = 5300) And (YMil = 1900) Then Result := 4;
    If (XMil = 3950) And (YMil = 3250) Then Result := 5;
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
            If Kind = 2 Then
                K := TargetLabelIndex(SheetName, XMil, YMil)
            Else
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

Procedure AuditCI623FlagLocations;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    Iterator : ISch_Iterator;
    Obj : ISch_GraphicalObject;
    Component : ISch_Component;
    Report : TStringList;
    SheetName, BasePath : String;
    I : Integer;
Begin
    Project := FindCI623Project;
    If Project = Nil Then Exit;

    Report := TStringList.Create;
    Report.Add('sheet,kind,x_mil,y_mil');
    BasePath := '';
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
        If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
        SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
        If SchDoc = Nil Then Continue;
        BasePath := ExtractFilePath(LogicalDoc.DM_FullPath);
        SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
        Iterator := SchDoc.SchIterator_Create;
        If Iterator = Nil Then Continue;
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(eSchComponent, eNetLabel));
        Try
            Obj := Iterator.FirstSchObject;
            While Obj <> Nil Do
            Begin
                If Obj.ObjectId = eSchComponent Then
                Begin
                    Component := Obj;
                    If Component.LibReference = 'PWR_FLAG' Then
                        Report.Add(SheetName + ',flag,' +
                            IntToStr(Round(CoordToMils(Component.Location.X))) + ',' +
                            IntToStr(Round(CoordToMils(Component.Location.Y))));
                End;
                If Obj.ObjectId = eNetLabel Then
                    Report.Add(SheetName + ',label,' +
                        IntToStr(Round(CoordToMils(Obj.Location.X))) + ',' +
                        IntToStr(Round(CoordToMils(Obj.Location.Y))));
                Obj := Iterator.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Iterator);
        End;
    End;
    If BasePath <> '' Then
        Report.SaveToFile(BasePath + 'ci623_flag_locations.csv');
    ShowMessage('CI623 flag location audit exported: ' + IntToStr(Report.Count - 1));
    Report.Free;
End;

Procedure RemoveCI623FloatingFlagPairs;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    FlagObj, LabelObj : ISch_GraphicalObject;
    SheetName : String;
    I, K, Matches : Integer;
Begin
    Project := FindCI623Project;
    If Project = Nil Then
    Begin
        ShowMessage('CI623 cleanup stopped: qualified project not unique.');
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
            If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then Continue;
            FlagObj := FindObjectAtTarget(SchDoc, SheetName, K, 1);
            LabelObj := FindObjectAtTarget(SchDoc, SheetName, K, 2);
            If (FlagObj <> Nil) And (LabelObj <> Nil) Then Matches := Matches + 1;
        End;
    End;
    If Matches <> 6 Then
    Begin
        ShowMessage('CI623 cleanup stopped: expected six exact flag/label pairs, found ' + IntToStr(Matches));
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
    ShowMessage('Removed six CI623 imported PWR_FLAG/label pairs. Save documents and validate.');
End;

Function IsCI623LegacyPowerNoERC(XMil, YMil : Integer) : Boolean;
Begin
    Result :=
        ((XMil = 3600) And (YMil = 6000)) Or
        ((XMil = 5400) And (YMil = 5700)) Or
        ((XMil = 3600) And (YMil = 3550)) Or
        ((XMil = 5400) And (YMil = 3250)) Or
        ((XMil = 7400) And (YMil = 6900)) Or
        ((XMil = 9200) And (YMil = 6900));
End;

Procedure RepairCI623NoERCLocations;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc, RootDoc, PowerDoc : ISch_Document;
    Iterator : ISch_Iterator;
    Obj, RootNoERC, PowerNoERC : ISch_GraphicalObject;
    Entry : ISch_SheetEntry;
    RootLocation, PowerLocation : TLocation;
    SheetName : String;
    I, RootNoERCCount, PowerTargetCount, EntryCount, XMil, YMil : Integer;
Begin
    Project := FindCI623Project;
    If Project = Nil Then
    Begin
        ShowMessage('CI623 No ERC repair stopped: native project not found.');
        Exit;
    End;

    RootDoc := Nil;
    PowerDoc := Nil;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
        If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
        SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
        SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
        If SheetName = 'EVT_SYS_CARRIER.SchDoc' Then RootDoc := SchDoc;
        If SheetName = '10_POWER_INPUT.SchDoc' Then PowerDoc := SchDoc;
    End;
    If (RootDoc = Nil) Or (PowerDoc = Nil) Then
    Begin
        ShowMessage('CI623 No ERC repair stopped: root or power sheet is not loaded.');
        Exit;
    End;

    RootNoERC := Nil;
    RootNoERCCount := 0;
    Iterator := RootDoc.SchIterator_Create;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNoERC));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            RootNoERC := Obj;
            RootNoERCCount := RootNoERCCount + 1;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        RootDoc.SchIterator_Destroy(Iterator);
    End;

    EntryCount := 0;
    Iterator := RootDoc.SchIterator_Create;
    Iterator.SetState_IterationDepth(eIterateAllLevels);
    Iterator.AddFilter_ObjectSet(MkSet(eSheetEntry));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            Entry := Obj;
            If Entry.UniqueId = 'OJOQKTZM' Then
            Begin
                RootLocation := Entry.Location;
                EntryCount := EntryCount + 1;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        RootDoc.SchIterator_Destroy(Iterator);
    End;

    PowerNoERC := Nil;
    PowerTargetCount := 0;
    Iterator := PowerDoc.SchIterator_Create;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNoERC));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            XMil := Round(CoordToMils(Obj.Location.X));
            YMil := Round(CoordToMils(Obj.Location.Y));
            If Not IsCI623LegacyPowerNoERC(XMil, YMil) Then
            Begin
                PowerNoERC := Obj;
                PowerTargetCount := PowerTargetCount + 1;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        PowerDoc.SchIterator_Destroy(Iterator);
    End;

    If (RootNoERCCount <> 1) Or (EntryCount <> 1) Or (PowerTargetCount <> 1) Then
    Begin
        ShowMessage('CI623 No ERC repair stopped: expected root/power targets were not unique.');
        Exit;
    End;

    PowerLocation := Point(MilsToCoord(8950), MilsToCoord(4100));

    SchServer.ProcessControl.PreProcess(RootDoc, '');
    Try
        SchServer.RobotManager.SendMessage(RootNoERC.I_ObjectAddress,
            c_BroadCast, SCHM_BeginModify, c_NoEventData);
        RootNoERC.Location := RootLocation;
        SchServer.RobotManager.SendMessage(RootNoERC.I_ObjectAddress,
            c_BroadCast, SCHM_EndModify, c_NoEventData);
    Finally
        SchServer.ProcessControl.PostProcess(RootDoc, '');
    End;

    SchServer.ProcessControl.PreProcess(PowerDoc, '');
    Try
        SchServer.RobotManager.SendMessage(PowerNoERC.I_ObjectAddress,
            c_BroadCast, SCHM_BeginModify, c_NoEventData);
        PowerNoERC.Location := PowerLocation;
        SchServer.RobotManager.SendMessage(PowerNoERC.I_ObjectAddress,
            c_BroadCast, SCHM_EndModify, c_NoEventData);
    Finally
        SchServer.ProcessControl.PostProcess(PowerDoc, '');
    End;

    RootNoERC.GraphicallyInvalidate;
    PowerNoERC.GraphicallyInvalidate;
    RootDoc.GraphicallyInvalidate;
    PowerDoc.GraphicallyInvalidate;
    ShowMessage('CI623 specific No ERC directives moved to BOOT0 and 3V3 violation points. Save and validate.');
End;
