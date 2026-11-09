Function FindCI623DirectionProject : IProject;
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

Function CompilePinIndex(SheetName, Ref, Number : String) : Integer;
Begin
    Result := -1;
    If (SheetName = '10_POWER_INPUT.SchDoc') Then
    Begin
        If (Ref = 'U5') And (Number = '5') Then Result := 0;
        If (Ref = 'U5') And (Number = '9') Then Result := 1;
        If (Ref = 'U6') And (Number = '1') Then Result := 2;
        If (Ref = 'U6') And (Number = '2') Then Result := 3;
        If (Ref = 'U7') And (Number = '1') Then Result := 4;
        If (Ref = 'U7') And (Number = '2') Then Result := 5;
    End;
    If (SheetName = '20_MCU_CORE.SchDoc') Then
    Begin
        If (Ref = 'Y1') And (Number = '4') Then Result := 6;
        If (Ref = 'U1') And (Number = '31') Then Result := 7;
        If (Ref = 'U1') And (Number = '166') Then Result := 8;
    End;
    If (SheetName = '30_TIME_GNSS.SchDoc') And
       (Ref = 'J8') And (Number = '1') Then Result := 9;
    If (SheetName = '40_IMU.SchDoc') And
       (Ref = 'U2') And (Number = '9') Then Result := 10;
    If (SheetName = '50_RADAR_IO_CAN.SchDoc') Then
    Begin
        If (Ref = 'J4') And (Number = '4') Then Result := 11;
        If (Ref = 'U4') And (Number = '5') Then Result := 12;
        If (Ref = 'U4') And (Number = '8') Then Result := 13;
    End;
    If (SheetName = '60_ETHERNET.SchDoc') And
       (Ref = 'Y2') And (Number = '4') Then Result := 14;
End;

Function CompilePinIsOutput(Index : Integer) : Boolean;
Begin
    Result := (Index = 9) Or (Index = 11);
End;

Procedure RepairCI623CompilePins;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    Components, Pins : ISch_Iterator;
    Component : ISch_Component;
    Pin : ISch_Pin;
    SheetName, Ref : String;
    Found : Array[0..14] Of Integer;
    I, K, Pass : Integer;
    BadMatch : Boolean;
Begin
    Project := FindCI623DirectionProject;
    If Project = Nil Then
    Begin
        ShowMessage('Compile ECO stopped: canonical CI623 project not found.');
        Exit;
    End;
    For K := 0 To 14 Do Found[K] := 0;
    BadMatch := False;

    For Pass := 0 To 1 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Project.DM_LogicalDocuments(I);
            If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then Continue;
            SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then Continue;
            If Pass = 1 Then SchServer.ProcessControl.PreProcess(SchDoc, '');
            Try
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
                                    K := CompilePinIndex(SheetName, Ref, Pin.Designator);
                                    If K >= 0 Then
                                    Begin
                                        If Pass = 0 Then
                                            Found[K] := Found[K] + 1
                                        Else
                                        Begin
                                            SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                c_BroadCast, SCHM_BeginModify, c_NoEventData);
                                            If CompilePinIsOutput(K) Then
                                                Pin.SetState_Electrical(eElectricOutput)
                                            Else
                                                Pin.SetState_Electrical(eElectricPassive);
                                            SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                c_BroadCast, SCHM_EndModify, c_NoEventData);
                                            Pin.GraphicallyInvalidate;
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
                If Pass = 1 Then SchServer.ProcessControl.PostProcess(SchDoc, '');
            End;
        End;
        If Pass = 0 Then
        Begin
            For K := 0 To 14 Do
                If Found[K] <> 1 Then BadMatch := True;
            If BadMatch Then
            Begin
                ShowMessage('Compile ECO stopped: 15 target pins not uniquely present.');
                Exit;
            End;
        End;
    End;
    ShowMessage('CI623 compile ECO changed 15 exact pins in memory. Save and validate.');
End;

Function PowerConsumerIndex(SheetName, Ref, Number : String) : Integer;
Begin
    Result := -1;
    If (SheetName = '20_MCU_CORE.SchDoc') And (Ref = 'U1') Then
    Begin
        If Number = '6' Then Result := 0;
        If Number = '15' Then Result := 1;
        If Number = '23' Then Result := 2;
        If Number = '36' Then Result := 3;
        If Number = '49' Then Result := 4;
        If Number = '62' Then Result := 5;
        If Number = '72' Then Result := 6;
        If Number = '82' Then Result := 7;
        If Number = '91' Then Result := 8;
        If Number = '103' Then Result := 9;
        If Number = '114' Then Result := 10;
        If Number = '127' Then Result := 11;
        If Number = '136' Then Result := 12;
        If Number = '149' Then Result := 13;
        If Number = '159' Then Result := 14;
        If Number = '171' Then Result := 15;
        If Number = '172' Then Result := 16;
    End;
    If (SheetName = '40_IMU.SchDoc') And (Ref = 'U2') Then
    Begin
        If Number = '5' Then Result := 17;
        If Number = '8' Then Result := 18;
    End;
    If (SheetName = '60_ETHERNET.SchDoc') And (Ref = 'U3') Then
    Begin
        If Number = '1' Then Result := 19;
        If Number = '9' Then Result := 20;
        If Number = '19' Then Result := 21;
    End;
    If (SheetName = '50_RADAR_IO_CAN.SchDoc') And
       (Ref = 'U4') And (Number = '3') Then Result := 22;
    If (SheetName = '30_TIME_GNSS.SchDoc') And
       (Ref = 'U8') And (Number = '23') Then Result := 23;
End;

Function DirectionIndex(SheetName, Ref, Number : String) : Integer;
Begin
    Result := -1;
    If (SheetName = '20_MCU_CORE.SchDoc') And (Ref = 'U1') Then
    Begin
        If Number = '1' Then Result := 0;
        If Number = '2' Then Result := 1;
        If Number = '3' Then Result := 2;
        If Number = '29' Then Result := 3;
        If Number = '33' Then Result := 4;
        If Number = '40' Then Result := 5;
        If Number = '41' Then Result := 6;
        If Number = '53' Then Result := 7;
        If Number = '54' Then Result := 8;
        If Number = '55' Then Result := 9;
        If Number = '79' Then Result := 10;
        If Number = '80' Then Result := 11;
        If Number = '92' Then Result := 12;
        If Number = '93' Then Result := 13;
        If Number = '94' Then Result := 14;
        If Number = '95' Then Result := 15;
        If Number = '96' Then Result := 16;
        If Number = '97' Then Result := 17;
        If Number = '142' Then Result := 18;
        If Number = '143' Then Result := 19;
        If Number = '154' Then Result := 20;
        If Number = '156' Then Result := 21;
        If Number = '157' Then Result := 22;
    End;
    If (SheetName = '60_ETHERNET.SchDoc') And (Ref = 'U3') Then
    Begin
        If Number = '7' Then Result := 23;
        If Number = '8' Then Result := 24;
        If Number = '11' Then Result := 25;
    End;
End;

Function DirectionIsInput(Index : Integer) : Boolean;
Begin
    Result := False;
    Case Index Of
        0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 14, 17, 18: Result := True;
    End;
End;

Procedure RepairCI623DirectionPins;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    Components, Pins : ISch_Iterator;
    Component : ISch_Component;
    Pin : ISch_Pin;
    SheetName, Ref : String;
    I, K, Pass : Integer;
    Found : Array[0..25] Of Integer;
    BadType : Boolean;
Begin
    Project := FindCI623DirectionProject;
    If Project = Nil Then
    Begin
        ShowMessage('Direction ECO stopped: canonical CI623 project not unique.');
        Exit;
    End;
    For K := 0 To 25 Do Found[K] := 0;
    BadType := False;

    For Pass := 0 To 1 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Project.DM_LogicalDocuments(I);
            If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
            If (SheetName <> '20_MCU_CORE.SchDoc') And
               (SheetName <> '60_ETHERNET.SchDoc') Then Continue;
            If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then
            Begin
                ShowMessage('Direction ECO stopped: target sheet outside canonical native project.');
                Exit;
            End;
            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then
            Begin
                ShowMessage('Direction ECO stopped: target sheet not loaded.');
                Exit;
            End;
            If Pass = 1 Then SchServer.ProcessControl.PreProcess(SchDoc, '');
            Try
                Components := SchDoc.SchIterator_Create;
                If Components = Nil Then Continue;
                Components.SetState_IterationDepth(eIterateFirstLevel);
                Components.AddFilter_ObjectSet(MkSet(eSchComponent));
                Try
                    Component := Components.FirstSchObject;
                    While Component <> Nil Do
                    Begin
                        Ref := Component.Designator.Text;
                        If (Ref = 'U1') Or (Ref = 'U3') Then
                        Begin
                            Pins := Component.SchIterator_Create;
                            If Pins <> Nil Then
                            Begin
                                Pins.AddFilter_ObjectSet(MkSet(ePin));
                                Try
                                    Pin := Pins.FirstSchObject;
                                    While Pin <> Nil Do
                                    Begin
                                        K := DirectionIndex(SheetName, Ref, Pin.Designator);
                                        If K >= 0 Then
                                        Begin
                                            If Pass = 0 Then
                                            Begin
                                                Found[K] := Found[K] + 1;
                                                BadType := BadType Or (Pin.Electrical <> eElectricIO);
                                            End
                                            Else
                                            Begin
                                                SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                    c_BroadCast, SCHM_BeginModify, c_NoEventData);
                                                If DirectionIsInput(K) Then
                                                    Pin.SetState_Electrical(eElectricInput)
                                                Else
                                                    Pin.SetState_Electrical(eElectricOutput);
                                                SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                    c_BroadCast, SCHM_EndModify, c_NoEventData);
                                                Pin.GraphicallyInvalidate;
                                            End;
                                        End;
                                        Pin := Pins.NextSchObject;
                                    End;
                                Finally
                                    Component.SchIterator_Destroy(Pins);
                                End;
                            End;
                        End;
                        Component := Components.NextSchObject;
                    End;
                Finally
                    SchDoc.SchIterator_Destroy(Components);
                End;
            Finally
                If Pass = 1 Then SchServer.ProcessControl.PostProcess(SchDoc, '');
            End;
        End;
        If Pass = 0 Then
        Begin
            For K := 0 To 25 Do
                If Found[K] <> 1 Then BadType := True;
            If BadType Then
            Begin
                ShowMessage('Direction ECO stopped: 26 expected I/O pins not uniquely present.');
                Exit;
            End;
        End;
    End;
    ShowMessage('CI623 direction ECO changed 26 pins in memory. Save and validate.');
End;

Procedure RepairCI623PowerConsumerPins;
Var
    Project : IProject;
    LogicalDoc : IDocument;
    SchDoc : ISch_Document;
    Components, Pins : ISch_Iterator;
    Component : ISch_Component;
    Pin : ISch_Pin;
    SheetName, Ref : String;
    I, K, Pass : Integer;
    Found : Array[0..23] Of Integer;
    BadType : Boolean;
Begin
    Project := FindCI623DirectionProject;
    If Project = Nil Then
    Begin
        ShowMessage('Power consumer ECO stopped: canonical CI623 project not unique.');
        Exit;
    End;
    For K := 0 To 23 Do Found[K] := 0;
    BadType := False;

    For Pass := 0 To 1 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Project.DM_LogicalDocuments(I);
            If (LogicalDoc = Nil) Or (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            If Pos('\altium\native\', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then
            Begin
                ShowMessage('Power consumer ECO stopped: target sheet outside canonical native project.');
                Exit;
            End;
            SheetName := ExtractFileName(LogicalDoc.DM_FullPath);
            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then Continue;
            If Pass = 1 Then SchServer.ProcessControl.PreProcess(SchDoc, '');
            Try
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
                                    K := PowerConsumerIndex(SheetName, Ref, Pin.Designator);
                                    If K >= 0 Then
                                    Begin
                                        If Pass = 0 Then
                                        Begin
                                            Found[K] := Found[K] + 1;
                                        End
                                        Else
                                        Begin
                                            SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                c_BroadCast, SCHM_BeginModify, c_NoEventData);
                                            Pin.SetState_Electrical(eElectricPassive);
                                            SchServer.RobotManager.SendMessage(Pin.I_ObjectAddress,
                                                c_BroadCast, SCHM_EndModify, c_NoEventData);
                                            Pin.GraphicallyInvalidate;
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
                If Pass = 1 Then SchServer.ProcessControl.PostProcess(SchDoc, '');
            End;
        End;
        If Pass = 0 Then
        Begin
            For K := 0 To 23 Do
                If Found[K] <> 1 Then BadType := True;
            If BadType Then
            Begin
                ShowMessage('Power consumer ECO stopped: 24 expected power pins not uniquely present.');
                Exit;
            End;
        End;
    End;
    ShowMessage('CI623 power consumer ECO changed 24 pins to passive in memory. Save and validate.');
End;
