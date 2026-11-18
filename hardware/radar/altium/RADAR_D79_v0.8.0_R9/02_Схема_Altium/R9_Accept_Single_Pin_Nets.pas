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

Function IsAcceptedSinglePin(Ref, PinNumber : String) : Boolean;
Begin
    Result :=
        ((Ref = 'RAD_U29') And
            ((PinNumber = 'B12') Or
             (PinNumber = 'M16') Or
             (PinNumber = 'N18') Or
             (PinNumber = 'N17') Or
             (PinNumber = 'M18') Or
             (PinNumber = 'M17') Or
             (PinNumber = 'L18') Or
             (PinNumber = 'L17') Or
             (PinNumber = 'B14') Or
             (PinNumber = 'A15'))) Or
        ((Ref = 'RAD_R13') And (PinNumber = '1')) Or
        ((Ref = 'RAD_R17') And (PinNumber = '1'));
End;

Function HasNoERCAt(Doc : ISch_Document; P : TLocation) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNoERC));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            If (Abs(Obj.Location.X - P.X) <= MilsToCoord(1)) And
               (Abs(Obj.Location.Y - P.Y) <= MilsToCoord(1)) Then
            Begin
                Obj.GraphicallyInvalidate;
                Result := True;
                Exit;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure AddNoERC(Doc : ISch_Document; P : TLocation);
Var
    Directive : ISch_GraphicalObject;
Begin
    Directive := SchServer.SchObjectFactory(eNoERC, eCreate_GlobalCopy);
    If Directive = Nil Then Exit;
    Directive.Location := P;
    Directive.Color := $000000FF;
    Doc.RegisterSchObjectInContainer(Directive);
    SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
        SCHM_PrimitiveRegistration, Directive.I_ObjectAddress);
End;

Procedure AcceptR9SinglePinNets;
Var
    Project       : IProject;
    LogicalDoc    : IDocument;
    ServerDoc     : IServerDocument;
    SchDoc        : ISch_Document;
    Components    : ISch_Iterator;
    Pins          : ISch_Iterator;
    Component     : ISch_Component;
    Pin           : ISch_Pin;
    I, Pass       : Integer;
    FoundCount    : Integer;
    AddedCount    : Integer;
    ExistingCount : Integer;
    SaveFailures  : Integer;
    Ref           : String;
Begin
    Project := FindR9Project;
    If Project = Nil Then
    Begin
        ShowMessage('R9 NC update stopped: RADAR_D79_24V_R9.PrjPcb is not open.');
        Exit;
    End;

    FoundCount := 0;
    AddedCount := 0;
    ExistingCount := 0;
    SaveFailures := 0;

    For Pass := 0 To 1 Do
    Begin
        For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
        Begin
            LogicalDoc := Project.DM_LogicalDocuments(I);
            If (LogicalDoc = Nil) Or
               (LogicalDoc.DM_DocumentKind <> 'SCH') Then Continue;
            If ExtractFileName(LogicalDoc.DM_FullPath) =
                '00_SYSTEM_OVERVIEW.SchDoc' Then Continue;

            SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
            If SchDoc = Nil Then
            Begin
                ServerDoc := Client.OpenDocument('SCH', LogicalDoc.DM_FullPath);
                If ServerDoc <> Nil Then
                Begin
                    Client.ShowDocument(ServerDoc);
                    Application.ProcessMessages;
                    SchDoc := SchServer.GetSchDocumentByPath(LogicalDoc.DM_FullPath);
                End;
            End;
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
                        If (Ref = 'RAD_U29') Or (Ref = 'RAD_R13') Or
                           (Ref = 'RAD_R17') Then
                        Begin
                            Pins := Component.SchIterator_Create;
                            If Pins <> Nil Then
                            Begin
                                Pins.AddFilter_ObjectSet(MkSet(ePin));
                                Try
                                    Pin := Pins.FirstSchObject;
                                    While Pin <> Nil Do
                                    Begin
                                        If IsAcceptedSinglePin(Ref, Pin.Designator) Then
                                        Begin
                                            If Pass = 0 Then
                                                FoundCount := FoundCount + 1
                                            Else If HasNoERCAt(SchDoc, Pin.Location) Then
                                                ExistingCount := ExistingCount + 1
                                            Else
                                            Begin
                                                AddNoERC(SchDoc, Pin.Location);
                                                AddedCount := AddedCount + 1;
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

            If Pass = 1 Then
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

        If (Pass = 0) And (FoundCount <> 12) Then
        Begin
            ShowMessage('R9 NC update stopped: expected 12 target pins, found ' +
                IntToStr(FoundCount) + '. No changes were made.');
            Exit;
        End;
    End;

    ShowMessage('R9 NC update complete. Target pins: ' + IntToStr(FoundCount) +
        ', directives added: ' + IntToStr(AddedCount) +
        ', already present: ' + IntToStr(ExistingCount) +
        ', save failures: ' + IntToStr(SaveFailures) + '.');
End;

