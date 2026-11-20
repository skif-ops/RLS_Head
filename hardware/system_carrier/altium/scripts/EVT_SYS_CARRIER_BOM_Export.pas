{ Native BOM exporter for the canonical EVT System Carrier project.
  It reads placed schematic components and their MPN parameters without
  modifying the design.

  Run procedure: ExportNativeBOM
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function IsCanonicalNativePath(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0);
End;

Function FindCarrierProject : IProject;
Var
    WS        : IWorkspace;
    Candidate : IProject;
    Doc       : IDocument;
    I         : Integer;
    J         : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;

    Candidate := WS.DM_FocusedProject;
    If Candidate <> Nil Then
        If ExtractFileName(Candidate.DM_ProjectFullPath) = 'EVT_SYS_CARRIER.PrjPcb' Then
            If IsCanonicalNativePath(Candidate.DM_ProjectFullPath) Then
                For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
                Begin
                    Doc := Candidate.DM_LogicalDocuments(J);
                    If Doc = Nil Then Continue;
                    If Doc.DM_DocumentKind <> 'SCH' Then Continue;
                    If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;
                    Result := Candidate;
                    Exit;
                End;

    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Candidate := WS.DM_Projects(I);
        If Candidate = Nil Then Continue;
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        If Not IsCanonicalNativePath(Candidate.DM_ProjectFullPath) Then Continue;

        For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Candidate.DM_LogicalDocuments(J);
            If Doc = Nil Then Continue;
            If Doc.DM_DocumentKind <> 'SCH' Then Continue;
            If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;
            Result := Candidate;
            Exit;
        End;
    End;
End;

Function ComponentMPN(Component : ISch_Component) : String;
Var
    Iterator  : ISch_Iterator;
    Parameter : ISch_Parameter;
Begin
    Result := '';
    Iterator := Component.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eParameter));
    Try
        Parameter := Iterator.FirstSchObject;
        While Parameter <> Nil Do
        Begin
            If UpperCase(Trim(Parameter.Name)) = 'MPN' Then
            Begin
                Result := Trim(Parameter.Text);
                Exit;
            End;
            Parameter := Iterator.NextSchObject;
        End;
    Finally
        Component.SchIterator_Destroy(Iterator);
    End;
End;

Procedure ExportNativeBOM;
Var
    Project      : IProject;
    Doc          : IDocument;
    ServerDoc    : IServerDocument;
    SchDoc       : ISch_Document;
    Components   : ISch_Iterator;
    Component    : ISch_Component;
    Report       : TStringList;
    I            : Integer;
    Count        : Integer;
    MissingMPN   : Integer;
    Designator   : String;
    MPN          : String;
    BasePath     : String;
    OutputPath   : String;
Begin
    Project := FindCarrierProject;
    If Project = Nil Then
    Begin
        ShowMessage('EVT System Carrier BOM export: canonical native project not found.');
        Exit;
    End;

    If Project.DM_NeedsCompile Then
        Project.DM_Compile;

    Report := TStringList.Create;
    Report.Add('Designator,MPN');
    Count := 0;
    MissingMPN := 0;
    BasePath := '';

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then Continue;
        If Doc.DM_DocumentKind <> 'SCH' Then Continue;
        If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;

        If BasePath = '' Then
            BasePath := ExtractFilePath(Doc.DM_FullPath) + '..\equivalence\';

        SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
        If SchDoc = Nil Then
        Begin
            ServerDoc := Client.OpenDocument('SCH', Doc.DM_FullPath);
            If ServerDoc <> Nil Then
            Begin
                Client.ShowDocument(ServerDoc);
                SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
            End;
        End;
        If SchDoc = Nil Then Continue;

        Components := SchDoc.SchIterator_Create;
        If Components = Nil Then Continue;
        Components.SetState_IterationDepth(eIterateFirstLevel);
        Components.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Components.FirstSchObject;
            While Component <> Nil Do
            Begin
                Designator := Trim(Component.Designator.Text);
                If (Designator <> '') And (Designator[1] <> '#') Then
                Begin
                    MPN := ComponentMPN(Component);
                    If MPN = '' Then MissingMPN := MissingMPN + 1;
                    Report.Add(CsvQuote(Designator) + ',' + CsvQuote(MPN));
                    Count := Count + 1;
                End;
                Component := Components.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Components);
        End;
    End;

    If BasePath = '' Then
        ShowMessage('EVT System Carrier BOM export: no canonical schematic documents found.')
    Else
    Begin
        OutputPath := BasePath + 'bom_export.csv';
        Report.SaveToFile(OutputPath);
        ShowMessage(
            'EVT System Carrier BOM exported: ' + IntToStr(Count) +
            ' components, missing MPN: ' + IntToStr(MissingMPN) +
            '. File: ' + OutputPath);
    End;
    Report.Free;
End;
