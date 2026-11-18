Procedure UpdateSchematicTitles;
Var
    WS            : IWorkspace;
    Project       : IProject;
    Doc           : IDocument;
    ServerDoc     : IServerDocument;
    SchDoc        : ISch_Document;
    Iterator      : ISch_Iterator;
    LabelObj      : ISch_Label;
    OldText       : String;
    NewText       : String;
    I             : Integer;
    P             : Integer;
    SheetsSeen    : Integer;
    LabelsChanged : Integer;
    SaveFailures  : Integer;
Begin
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Project := Nil;
    For P := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        If ExtractFileName(WS.DM_Projects(P).DM_ProjectFullPath) =
            'RADAR_D79_24V_R9.PrjPcb' Then
        Begin
            Project := WS.DM_Projects(P);
            Break;
        End;
    End;
    If Project = Nil Then
    Begin
        ShowMessage('R9 title update: RADAR_D79_24V_R9.PrjPcb is not open.');
        Exit;
    End;

    SheetsSeen := 0;
    LabelsChanged := 0;
    SaveFailures := 0;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
        SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
        If SchDoc = Nil Then
        Begin
            ServerDoc := Client.OpenDocument('SCH', Doc.DM_FullPath);
            If ServerDoc <> Nil Then
            Begin
                Client.ShowDocument(ServerDoc);
                Application.ProcessMessages;
                SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
            End;
        End;
        If SchDoc = Nil Then Continue;
        SheetsSeen := SheetsSeen + 1;

        SchServer.ProcessControl.PreProcess(SchDoc, '');
        Try
            Iterator := SchDoc.SchIterator_Create;
            If Iterator = Nil Then Continue;
            Iterator.SetState_IterationDepth(eIterateFirstLevel);
            Iterator.AddFilter_ObjectSet(MkSet(eLabel));
            Try
                LabelObj := Iterator.FirstSchObject;
                While LabelObj <> Nil Do
                Begin
                    OldText := LabelObj.Text;
                    NewText := OldText;
                    If Pos('RADAR D79 24V / PCB 0.7.232 /', OldText) = 1 Then
                        NewText := StringReplace(OldText, 'PCB 0.7.232',
                            'PCB v0.8.0 R9', rfReplaceAll);
                    If Pos('Engineering schematic / sheet ', OldText) = 1 Then
                        NewText := StringReplace(NewText, 'release 2.0.0-RC1',
                            'release 2.2.4-RC6', rfReplaceAll);

                    If NewText <> OldText Then
                    Begin
                        SchServer.RobotManager.SendMessage(LabelObj.I_ObjectAddress,
                            c_BroadCast, SCHM_BeginModify, c_NoEventData);
                        LabelObj.Text := NewText;
                        SchServer.RobotManager.SendMessage(LabelObj.I_ObjectAddress,
                            c_BroadCast, SCHM_EndModify, c_NoEventData);
                        LabelsChanged := LabelsChanged + 1;
                    End;
                    LabelObj := Iterator.NextSchObject;
                End;
            Finally
                SchDoc.SchIterator_Destroy(Iterator);
            End;
        Finally
            SchServer.ProcessControl.PostProcess(SchDoc, '');
        End;
        SchDoc.GraphicallyInvalidate;
        ServerDoc := Client.GetDocumentByPath(Doc.DM_FullPath);
        If ServerDoc = Nil Then
        Begin
            SaveFailures := SaveFailures + 1;
            Continue;
        End;
        ServerDoc.Modified := True;
        If Not ServerDoc.DoFileSave('Advanced Schematic binary') Then
            SaveFailures := SaveFailures + 1;
        Application.ProcessMessages;
    End;

    ShowMessage('R9 title update complete. Sheets: ' + IntToStr(SheetsSeen) +
        ', labels changed: ' + IntToStr(LabelsChanged) +
        ', save failures: ' + IntToStr(SaveFailures) + '.');
End;
