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
    If Project = Nil Then
    Begin
        ShowMessage('EVT System Carrier hierarchy audit: no focused project.');
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

        If Doc.DM_DocumentKind <> 'SCH' Then
            Continue;

        SheetName := ContractSheetName(Doc.DM_FullPath);
        If SheetName = '' Then
            Continue;

        If BasePath = '' Then
            BasePath := ExtractFilePath(Doc.DM_FullPath) + '..\equivalence\';

        SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
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
