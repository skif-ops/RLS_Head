{ The audit is read-only; the guarded ECO changes six CI623 pin types. }

Function FindCI623ImportProject : IProject;
Var
    WS : IWorkspace;
    Candidate : IProject;
    LogicalDoc : IDocument;
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

Procedure AuditCI623ImportedPinTypes;
Var
    WS         : IWorkspace;
    Project    : IProject;
    Doc        : IDocument;
    SchDoc     : ISch_Document;
    Components : ISch_Iterator;
    Pins       : ISch_Iterator;
    Component  : ISch_Component;
    Pin        : ISch_Pin;
    Report     : TStringList;
    I          : Integer;
    Ref        : String;
    SheetName  : String;
    BasePath   : String;
Begin
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Project := FindCI623ImportProject;
    If Project = Nil Then Exit;

    Report := TStringList.Create;
    Report.Add('sheet,reference,pin_number,pin_name,electrical_type');
    BasePath := '';

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
        SheetName := ExtractFileName(Doc.DM_FullPath);
        If (SheetName <> '60_ETHERNET.SchDoc') And
           (SheetName <> '10_POWER_INPUT.SchDoc') Then Continue;

        SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
        If SchDoc = Nil Then Continue;
        BasePath := ExtractFilePath(Doc.DM_FullPath);
        Components := SchDoc.SchIterator_Create;
        If Components = Nil Then Continue;
        Components.SetState_IterationDepth(eIterateFirstLevel);
        Components.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Components.FirstSchObject;
            While Component <> Nil Do
            Begin
                Ref := Component.Designator.Text;
                If (Ref = 'D3') Or (Ref = 'J6') Or (Ref = 'U7') Then
                Begin
                    Pins := Component.SchIterator_Create;
                    If Pins <> Nil Then
                    Begin
                        Pins.AddFilter_ObjectSet(MkSet(ePin));
                        Try
                            Pin := Pins.FirstSchObject;
                            While Pin <> Nil Do
                            Begin
                                Report.Add(SheetName + ',' + Ref + ',' +
                                    Pin.Designator + ',' + Pin.Name + ',' +
                                    IntToStr(Ord(Pin.Electrical)));
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
    End;

    If BasePath = '' Then
        ShowMessage('No loaded target schematic documents found.')
    Else
    Begin
        Report.SaveToFile(BasePath + 'ci623_import_pin_types.csv');
        ShowMessage('Pin type audit exported: ' + IntToStr(Report.Count - 1));
    End;
    Report.Free;
End;

Function PinECOIndex(SheetName, Ref, PinNumber : String) : Integer;
Begin
    Result := -1;
    If (SheetName = '10_POWER_INPUT.SchDoc') And
       (Ref = 'U7') And (PinNumber = '6') Then Result := 0;
    If (SheetName <> '60_ETHERNET.SchDoc') Then Exit;
    If (Ref = 'D3') And (PinNumber = '6') Then Result := 1;
    If (Ref = 'D3') And (PinNumber = '7') Then Result := 2;
    If (Ref = 'D3') And (PinNumber = '9') Then Result := 3;
    If (Ref = 'D3') And (PinNumber = '10') Then Result := 4;
    If (Ref = 'J6') And (PinNumber = '7') Then Result := 5;
End;

Procedure RepairCI623ImportedPinTypes;
Var
    WS         : IWorkspace;
    Project    : IProject;
    Doc        : IDocument;
    SchDoc     : ISch_Document;
    Components : ISch_Iterator;
    Pins       : ISch_Iterator;
    Component  : ISch_Component;
    Pin        : ISch_Pin;
    I, K, Pass : Integer;
    Ref        : String;
    SheetName  : String;
    Found      : Array[0..5] Of Integer;
    BadType    : Boolean;
Begin
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Project := FindCI623ImportProject;
    If Project = Nil Then Exit;

    For K := 0 To 5 Do Found[K] := 0;
    BadType := False;

    For Pass := 0 To 1 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Project.DM_LogicalDocuments(I);
            If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
            SheetName := ExtractFileName(Doc.DM_FullPath);
            If (SheetName <> '60_ETHERNET.SchDoc') And
               (SheetName <> '10_POWER_INPUT.SchDoc') Then Continue;
            If Pos('\altium\native\', LowerCase(Doc.DM_FullPath)) = 0 Then
            Begin
                ShowMessage('ECO stopped: target is not the CI623 diagnostic project.');
                Exit;
            End;

            SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
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
                        If (Ref = 'D3') Or (Ref = 'J6') Or (Ref = 'U7') Then
                        Begin
                            Pins := Component.SchIterator_Create;
                            If Pins <> Nil Then
                            Begin
                                Pins.AddFilter_ObjectSet(MkSet(ePin));
                                Try
                                    Pin := Pins.FirstSchObject;
                                    While Pin <> Nil Do
                                    Begin
                                        K := PinECOIndex(SheetName, Ref, Pin.Designator);
                                        If K >= 0 Then
                                        Begin
                                            If Pass = 0 Then
                                            Begin
                                                Found[K] := Found[K] + 1;
                                                If K = 0 Then
                                                    BadType := BadType Or
                                                        (Pin.Electrical <> eElectricPower)
                                                Else
                                                    BadType := BadType Or
                                                        (Pin.Electrical <> eElectricInput);
                                            End
                                            Else
                                            Begin
                                                SchServer.RobotManager.SendMessage(
                                                    Pin.I_ObjectAddress, c_BroadCast,
                                                    SCHM_BeginModify, c_NoEventData);
                                                If K = 0 Then
                                                    Pin.SetState_Electrical(eElectricOutput)
                                                Else
                                                    Pin.SetState_Electrical(eElectricPassive);
                                                SchServer.RobotManager.SendMessage(
                                                    Pin.I_ObjectAddress, c_BroadCast,
                                                    SCHM_EndModify, c_NoEventData);
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
            For K := 0 To 5 Do
                If Found[K] <> 1 Then BadType := True;
            If BadType Then
            Begin
                ShowMessage('ECO stopped: pin identity or original type mismatch.');
                Exit;
            End;
        End;
    End;

    ShowMessage('Six CI623 pin electrical types corrected in memory.');
End;

Procedure ValidateCI623NativeProject;
Var
    WS      : IWorkspace;
    Project : IProject;
    Doc     : IDocument;
    I       : Integer;
    Count   : Integer;
Begin
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Project := FindCI623ImportProject;
    If Project = Nil Then Exit;

    Count := 0;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
        If Pos('\altium\native\', LowerCase(Doc.DM_FullPath)) = 0 Then
        Begin
            ShowMessage('Validate stopped: focused project is not CI623. ' +
                Doc.DM_FullPath);
            Exit;
        End;
        Count := Count + 1;
    End;

    If Count <> 8 Then
    Begin
        ShowMessage('Validate stopped: expected eight CI623 schematics, found ' +
            IntToStr(Count));
        Exit;
    End;

    Project.DM_Compile;
    ShowMessage('CI623 native compile completed. Review the Messages panel.');
End;
