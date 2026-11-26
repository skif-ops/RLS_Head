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
            If UpperCase(ExtractFileExt(Doc.DM_FullPath)) <> '.PCBDOC' Then Continue;
            If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;
            Result := Candidate;
            Exit;
        End;
    End;
End;

Function ResolveNativeBoard : IPCB_Board;
Var
    Project : IProject;
    Doc     : IDocument;
    PcbDoc  : IServerDocument;
    I       : Integer;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If Result <> Nil Then
        If IsCanonicalNativePath(Result.FileName) Then Exit;
    Result := Nil;

    Project := FindCarrierProject;
    If Project = Nil Then Exit;

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then Continue;
        If UpperCase(ExtractFileExt(Doc.DM_FullPath)) <> '.PCBDOC' Then Continue;
        If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;

        Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
        If Result <> Nil Then Exit;

        PcbDoc := Client.OpenDocument('PCB', Doc.DM_FullPath);
        If PcbDoc = Nil Then Continue;
        Client.ShowDocument(PcbDoc);
        Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
        Exit;
    End;
End;

Procedure ClearU9FSWNet;
Var
    Board    : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
    Count    : Integer;
Begin
    Board := ResolveNativeBoard;
    If Board = Nil Then Exit;
    If UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.PCBDOC' Then
    Begin
        ShowMessage('ClearU9FSWNet requires EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    Count := 0;
    PCBServer.PreProcess;
    Try
        Iterator := Board.BoardIterator_Create;
        Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
        Iterator.AddFilter_LayerSet(AllLayers);
        Iterator.AddFilter_Method(eProcessAll);

        Pad := Iterator.FirstPCBObject;
        While Pad <> Nil Do
        Begin
            If (Pad.Component <> Nil) And
               (UpperCase(Pad.Component.SourceDesignator) = 'U9') And
               (UpperCase(Pad.Name) = '7') Then
            Begin
                PCBServer.SendMessageToRobots(
                    Pad.I_ObjectAddress, c_Broadcast,
                    PCBM_BeginModify, c_NoEventData
                );
                Pad.Net := Nil;
                PCBServer.SendMessageToRobots(
                    Pad.I_ObjectAddress, c_Broadcast,
                    PCBM_EndModify, c_NoEventData
                );
                Inc(Count);
            End;
            Pad := Iterator.NextPCBObject;
        End;
        Board.BoardIterator_Destroy(Iterator);
        Board.SetState_DocumentHasChanged;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ShowMessage('U9 FSW ECO complete. Cleared pad 7 net on ' +
        IntToStr(Count) + ' pad(s).');
End;
