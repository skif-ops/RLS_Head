Function FindCI616DirectionProject : IProject;
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

Procedure RepairCI616DirectionPins;
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
    Project := FindCI616DirectionProject;
    If Project = Nil Then
    Begin
        ShowMessage('Direction ECO stopped: qualified CI616 project not unique.');
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
            If Pos('ci616-qualified', LowerCase(LogicalDoc.DM_FullPath)) = 0 Then
            Begin
                ShowMessage('Direction ECO stopped: target sheet outside CI616 project.');
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
    ShowMessage('CI616 direction ECO changed 26 pins in memory. Save and validate.');
End;
