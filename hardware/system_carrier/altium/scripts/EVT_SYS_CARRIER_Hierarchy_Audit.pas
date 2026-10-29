{ EVT System Carrier native Altium read-only hierarchy exporter.
  This script reads the compiled focused project and exports schematic
  ports from numbered child sheets. It does not modify schematic objects.

  Run procedure: ExportNativeHierarchy
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function IsCanonicalNativePath(APath : String) : Boolean; Forward;
Function FindCarrierProject : IProject; Forward;

Function BomComponentMPN(Component : ISch_Component) : String;
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
                    MPN := BomComponentMPN(Component);
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

Function PortIOToString(AIO : TPortIO) : String;
Begin
    Case AIO Of
        ePortOutput        : Result := 'output';
        ePortInput         : Result := 'input';
        ePortBidirectional : Result := 'bidirectional';
    Else
        Result := 'passive';
    End;
End;

Function ContractSheetName(APath : String) : String;
Var
    N : String;
Begin
    N := ChangeFileExt(ExtractFileName(APath), '');

    { Numbered child sheets use NN_NAME. Ignore the root/top sheet. }
    If (Length(N) >= 4)
       And (N[1] >= '0') And (N[1] <= '9')
       And (N[2] >= '0') And (N[2] <= '9')
       And (N[3] = '_') Then
        Result := Copy(N, 4, Length(N) - 3)
    Else
        Result := '';
End;

Procedure ExportNativeHierarchy;
Var
    WS         : IWorkspace;
    Project    : IProject;
    Doc        : IDocument;
    ServerDoc  : IServerDocument;
    SchDoc     : ISch_Document;
    Iterator   : ISch_Iterator;
    Port       : ISch_Port;
    Rpt        : TStringList;
    I          : Integer;
    SheetName  : String;
    BasePath   : String;
    OutputPath : String;
Begin
    WS := GetWorkspace;
    If WS = Nil Then
    Begin
        ShowMessage('EVT System Carrier hierarchy audit: no workspace.');
        Exit;
    End;

    Project := WS.DM_FocusedProject;
    Project := FindCarrierProject;
    If Project = Nil Then
    Begin
        ShowMessage('EVT System Carrier hierarchy audit: canonical native project not found.');
        Exit;
    End;

    If Project.DM_NeedsCompile Then
        Project.DM_Compile;

    Rpt := TStringList.Create;
    Rpt.Add('sheet,net_name,pin_type');

    BasePath := '';

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then
            Continue;

        If Not IsCanonicalNativePath(Doc.DM_FullPath) Then
            Continue;

        If Doc.DM_DocumentKind <> 'SCH' Then
            Continue;

        SheetName := ContractSheetName(Doc.DM_FullPath);
        If SheetName = '' Then
            Continue;

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
        If SchDoc = Nil Then
            Continue;

        Iterator := SchDoc.SchIterator_Create;
        If Iterator = Nil Then
            Continue;

        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(ePort));

        Try
            Port := Iterator.FirstSchObject;
            While Port <> Nil Do
            Begin
                Rpt.Add(
                    CsvQuote(SheetName) + ',' +
                    CsvQuote(Port.Name) + ',' +
                    CsvQuote(PortIOToString(Port.IOType))
                );
                Port := Iterator.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Iterator);
        End;
    End;

    If BasePath = '' Then
    Begin
        Rpt.Free;
        ShowMessage(
            'EVT System Carrier hierarchy audit: no numbered child SchDoc found.'
        );
        Exit;
    End;

    ForceDirectories(BasePath);
    OutputPath := BasePath + 'hierarchy_export.csv';
    Rpt.SaveToFile(OutputPath);
    Rpt.Free;

    ShowMessage(
        'EVT System Carrier hierarchy exported to:' + #13#10 +
        OutputPath
    );
End;
