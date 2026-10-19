{ EVT System Carrier native Altium hierarchy audit.
  Read-only: enumerates native SchDoc ports and sheet entries only.

  Run procedure: ExportNativeHierarchyAudit
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function PortIOToString(AIOType : TPortIO) : String;
Begin
    Result := 'unspecified';

    Case AIOType Of
        ePortInput         : Result := 'input';
        ePortOutput        : Result := 'output';
        ePortBidirectional : Result := 'bidirectional';
        ePortUnspecified   : Result := 'unspecified';
    End;
End;

Procedure ExportPorts(
    SchDoc : ISch_Document;
    DocumentFile : String;
    Rpt : TStringList
);
Var
    Iterator : ISch_Iterator;
    PortObj  : ISch_Port;
Begin
    Iterator := SchDoc.SchIterator_Create;
    If Iterator = Nil Then Exit;

    Iterator.AddFilter_ObjectSet(MkSet(ePort));
    Iterator.AddFilter_IterateMethod(eIterateAllLevels);

    PortObj := Iterator.FirstSchObject;
    While PortObj <> Nil Do
    Begin
        Rpt.Add(
            CsvQuote(DocumentFile) + ',' +
            CsvQuote(PortObj.Name) + ',' +
            CsvQuote(PortIOToString(PortObj.IOType))
        );
        PortObj := Iterator.NextSchObject;
    End;

    SchDoc.SchIterator_Destroy(Iterator);
End;

Procedure ExportSheetEntries(
    SchDoc : ISch_Document;
    DocumentFile : String;
    Rpt : TStringList
);
Var
    Iterator    : ISch_Iterator;
    EntryObj    : ISch_SheetEntry;
    OwnerSymbol : ISch_SheetSymbol;
    ChildFile   : String;
Begin
    Iterator := SchDoc.SchIterator_Create;
    If Iterator = Nil Then Exit;

    Iterator.AddFilter_ObjectSet(MkSet(eSheetEntry));
    Iterator.AddFilter_IterateMethod(eIterateAllLevels);

    EntryObj := Iterator.FirstSchObject;
    While EntryObj <> Nil Do
    Begin
        ChildFile := '';
        OwnerSymbol := EntryObj.GetState_SchOwnerSheetSymbol;
        If OwnerSymbol <> Nil Then
        Begin
            If OwnerSymbol.SheetFileName <> Nil Then
                ChildFile := OwnerSymbol.SheetFileName.Text;
        End;

        Rpt.Add(
            CsvQuote(DocumentFile) + ',' +
            CsvQuote(ExtractFileName(ChildFile)) + ',' +
            CsvQuote(EntryObj.Name) + ',' +
            CsvQuote(PortIOToString(EntryObj.IOType))
        );

        EntryObj := Iterator.NextSchObject;
    End;

    SchDoc.SchIterator_Destroy(Iterator);
End;

Procedure ExportNativeHierarchyAudit;
Var
    Workspace    : IWorkspace;
    Project      : IProject;
    Doc          : IDocument;
    SchDoc       : ISch_Document;
    PortsRpt     : TStringList;
    EntriesRpt   : TStringList;
    BasePath     : String;
    DocumentFile : String;
    I            : Integer;
Begin
    Workspace := GetWorkspace;
    If Workspace = Nil Then
    Begin
        ShowMessage('EVT System Carrier hierarchy audit: no workspace.');
        Exit;
    End;

    Project := Workspace.DM_FocusedProject;
    If Project = Nil Then
    Begin
        ShowMessage('EVT System Carrier hierarchy audit: no focused project.');
        Exit;
    End;

    BasePath := ExtractFilePath(Project.DM_ProjectFullPath) + 'equivalence\';
    ForceDirectories(BasePath);

    PortsRpt := TStringList.Create;
    EntriesRpt := TStringList.Create;
    PortsRpt.Add('document_file,port_name,io_type');
    EntriesRpt.Add(
        'parent_document_file,child_document_file,entry_name,io_type'
    );

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then Continue;

        If UpperCase(Doc.DM_DocumentKind) <> 'SCH' Then Continue;

        SchDoc := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
        If SchDoc = Nil Then Continue;

        DocumentFile := ExtractFileName(Doc.DM_FullPath);
        ExportPorts(SchDoc, DocumentFile, PortsRpt);
        ExportSheetEntries(SchDoc, DocumentFile, EntriesRpt);
    End;

    PortsRpt.SaveToFile(BasePath + 'hierarchy_port_inventory.csv');
    EntriesRpt.SaveToFile(BasePath + 'hierarchy_sheet_entry_inventory.csv');

    PortsRpt.Free;
    EntriesRpt.Free;

    ShowMessage(
        'EVT System Carrier native hierarchy audit exported to:' + #13#10 +
        BasePath
    );
End;
