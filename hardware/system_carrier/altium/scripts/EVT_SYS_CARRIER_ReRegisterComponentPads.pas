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

Function FindRecoveryComponent(Board : IPCB_Board;
                               Ref : String) : IPCB_Component;
Var
    Iterator : IPCB_BoardIterator;
    Comp     : IPCB_Component;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Comp := Iterator.FirstPCBObject;
    While Comp <> Nil Do
    Begin
        If UpperCase(Comp.SourceDesignator) = UpperCase(Ref) Then
        Begin
            Result := Comp;
            Break;
        End;
        Comp := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function BoardContainsRecoveryPad(Board : IPCB_Board;
                                  TargetPad : IPCB_Pad) : Boolean;
Var
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
Begin
    Result := False;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If Pad.I_ObjectAddress = TargetPad.I_ObjectAddress Then
        Begin
            Result := True;
            Break;
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function RegisterMissingPadsForComponent(Board : IPCB_Board;
                                         Ref : String) : Integer;
Var
    Comp      : IPCB_Component;
    Iterator  : IPCB_GroupIterator;
    Primitive : IPCB_Primitive;
    Pad       : IPCB_Pad;
    Pads      : Array[0..63] Of IPCB_Pad;
    Count     : Integer;
    I         : Integer;
Begin
    Result := 0;
    Comp := FindRecoveryComponent(Board, Ref);
    If Comp = Nil Then Exit;

    Count := 0;
    Iterator := Comp.GroupIterator_Create;
    Iterator.SetState_FilterAll;
    Primitive := Iterator.FirstPCBObject;
    While Primitive <> Nil Do
    Begin
        If Primitive.ObjectId = ePadObject Then
        Begin
            Pad := Primitive;
            If Count <= 63 Then
            Begin
                Pads[Count] := Pad;
                Inc(Count);
            End;
        End;
        Primitive := Iterator.NextPCBObject;
    End;
    Comp.GroupIterator_Destroy(Iterator);

    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                  PCBM_BeginModify, c_NoEventData);
    Comp.BeginModify;
    For I := 0 To Count - 1 Do
    Begin
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_BeginModify, c_NoEventData);
        Pads[I].BeginModify;
        Pads[I].SetState_Board(Board);
        Pads[I].SetState_Component(Comp);
        Pads[I].SetState_InComponent(True);
        If Not BoardContainsRecoveryPad(Board, Pads[I]) Then
            Board.AddPCBObject(Pads[I]);
        PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                      PCBM_BoardRegisteration,
                                      Pads[I].I_ObjectAddress);
        Pads[I].EndModify;
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_EndModify, c_NoEventData);
        Inc(Result);
    End;
    Comp.Rebuild;
    Comp.SetState_XSizeYSize;
    Comp.EndModify;
    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                  PCBM_EndModify, c_NoEventData);
    Result := Count;
End;

Procedure ReRegisterComponentPads;
Var
    Board : IPCB_Board;
    Count : Integer;
Begin
    Board := ResolveNativeBoard;
    If Board = Nil Then
    Begin
        ShowMessage('ReRegisterComponentPads could not resolve the canonical EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;
    If UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.PCBDOC' Then
    Begin
        ShowMessage('ReRegisterComponentPads requires EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    Count := 0;
    PCBServer.PreProcess;
    Try
        Count := Count + RegisterMissingPadsForComponent(Board, 'C107');
        Count := Count + RegisterMissingPadsForComponent(Board, 'C40');
        Count := Count + RegisterMissingPadsForComponent(Board, 'C90');
        Count := Count + RegisterMissingPadsForComponent(Board, 'C91');
        Count := Count + RegisterMissingPadsForComponent(Board, 'C92');
        Count := Count + RegisterMissingPadsForComponent(Board, 'C93');
        Count := Count + RegisterMissingPadsForComponent(Board, 'D3');
        Count := Count + RegisterMissingPadsForComponent(Board, 'D4');
        Count := Count + RegisterMissingPadsForComponent(Board, 'D8');
        Count := Count + RegisterMissingPadsForComponent(Board, 'J4');
        Count := Count + RegisterMissingPadsForComponent(Board, 'J5');
        Count := Count + RegisterMissingPadsForComponent(Board, 'J6');
        Count := Count + RegisterMissingPadsForComponent(Board, 'J8');
        Count := Count + RegisterMissingPadsForComponent(Board, 'L9');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R42');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R605');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R90');
        Count := Count + RegisterMissingPadsForComponent(Board, 'SW1');
        Count := Count + RegisterMissingPadsForComponent(Board, 'U4');
        Count := Count + RegisterMissingPadsForComponent(Board, 'U9');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R71');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R72');
        Count := Count + RegisterMissingPadsForComponent(Board, 'R601');
        Board.SetState_DocumentHasChanged;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('ReRegisterComponentPads complete. Normalized component pads: ' +
                IntToStr(Count) + '.');
End;
