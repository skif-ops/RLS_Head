Function RepairCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function FindRepairComponent(Board : IPCB_Board; Ref : String) : IPCB_Component;
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

Function PadInBox(Pad : IPCB_Pad; X1, Y1, X2, Y2 : TCoord) : Boolean;
Begin
    Result := (Pad.X >= X1) And (Pad.X <= X2) And
              (Pad.Y >= Y1) And (Pad.Y <= Y2);
End;

Function ComponentContainsPad(Comp : IPCB_Component;
                              TargetPad : IPCB_Pad) : Boolean;
Var
    Iterator  : IPCB_GroupIterator;
    Primitive : IPCB_Primitive;
Begin
    Result := False;
    Iterator := Comp.GroupIterator_Create;
    Iterator.SetState_FilterAll;
    Primitive := Iterator.FirstPCBObject;
    While Primitive <> Nil Do
    Begin
        If (Primitive.ObjectId = ePadObject) And
           (Primitive.I_ObjectAddress = TargetPad.I_ObjectAddress) Then
        Begin
            Result := True;
            Break;
        End;
        Primitive := Iterator.NextPCBObject;
    End;
    Comp.GroupIterator_Destroy(Iterator);
End;

Function ClonePadForComponent(Board : IPCB_Board;
                              Comp : IPCB_Component;
                              SourcePad : IPCB_Pad) : IPCB_Pad;
Begin
    Result := PCBServer.PCBObjectFactory(ePadObject, eNoDimension,
                                         eCreate_Default);
    If Result = Nil Then Exit;

    Result.X := SourcePad.X;
    Result.Y := SourcePad.Y;
    Result.Layer := SourcePad.Layer;
    Result.Mode := SourcePad.Mode;
    Result.TopXSize := SourcePad.TopXSize;
    Result.TopYSize := SourcePad.TopYSize;
    Result.TopShape := SourcePad.TopShape;
    Result.MidXSize := SourcePad.MidXSize;
    Result.MidYSize := SourcePad.MidYSize;
    Result.MidShape := SourcePad.MidShape;
    Result.BotXSize := SourcePad.BotXSize;
    Result.BotYSize := SourcePad.BotYSize;
    Result.BotShape := SourcePad.BotShape;
    Result.HoleSize := SourcePad.HoleSize;
    Result.Rotation := SourcePad.Rotation;
    Result.Name := SourcePad.Name;
    Result.OwnerPart_ID := SourcePad.OwnerPart_ID;
    Result.Plated := SourcePad.Plated;
    Result.DrillType := SourcePad.DrillType;
    Result.HoleType := SourcePad.HoleType;
    Result.HoleWidth := SourcePad.HoleWidth;
    Result.HoleRotation := SourcePad.HoleRotation;
    Result.Cache := SourcePad.Cache;
    Result.Net := SourcePad.Net;
    Result.SetState_Board(Board);
    Result.SetState_Component(Comp);
    Result.SetState_InComponent(True);
End;

Function CountFreePadsInBox(Board : IPCB_Board;
                            X1, Y1, X2, Y2 : TCoord) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
Begin
    Result := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If (Pad.Component = Nil) And PadInBox(Pad, X1, Y1, X2, Y2) Then
            Inc(Result);
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function AttachFreePads(Board : IPCB_Board; Ref : String;
                        X1, Y1, X2, Y2 : TCoord) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
    Pads     : Array[0..63] Of IPCB_Pad;
    NewPad   : IPCB_Pad;
    Comp     : IPCB_Component;
    I        : Integer;
    WasPrimitiveLocked : Boolean;
Begin
    Result := 0;
    Comp := FindRepairComponent(Board, Ref);
    If Comp = Nil Then Exit;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If (Pad.Component = Nil) And PadInBox(Pad, X1, Y1, X2, Y2) Then
        Begin
            If Result <= 63 Then
            Begin
                Pads[Result] := Pad;
                Inc(Result);
            End;
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                  PCBM_BeginModify, c_NoEventData);
    Comp.BeginModify;
    WasPrimitiveLocked := Comp.PrimitiveLock;
    Comp.PrimitiveLock := False;
    For I := 0 To Result - 1 Do
    Begin
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_BeginModify, c_NoEventData);
        Pads[I].BeginModify;
        NewPad := ClonePadForComponent(Board, Comp, Pads[I]);
        If NewPad <> Nil Then
        Begin
            If ComponentContainsPad(Comp, Pads[I]) Then
                Comp.RemovePCBObject(Pads[I])
            Else
                Board.RemovePCBObject(Pads[I]);

            Comp.AddPCBObject(NewPad);
            PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                          PCBM_BoardRegisteration,
                                          NewPad.I_ObjectAddress);
        End;
        Pads[I].EndModify;
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_EndModify, c_NoEventData);
    End;
    Comp.Rebuild;
    Comp.SetState_XSizeYSize;
    Comp.PrimitiveLock := WasPrimitiveLocked;
    Comp.EndModify;
    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                  PCBM_EndModify, c_NoEventData);
End;

Function ReplaceBrokenComponent(Board : IPCB_Board; Ref : String;
                                X1, Y1, X2, Y2 : TCoord) : Integer;
Var
    Iterator   : IPCB_BoardIterator;
    Pad        : IPCB_Pad;
    Pads       : Array[0..63] Of IPCB_Pad;
    NewPads    : Array[0..63] Of IPCB_Pad;
    NewPad     : IPCB_Pad;
    OldComp    : IPCB_Component;
    NewComp    : IPCB_Component;
    I          : Integer;
    PadCount   : Integer;
    WasLocked  : Boolean;
Begin
    Result := 0;
    OldComp := FindRepairComponent(Board, Ref);
    If OldComp = Nil Then Exit;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If (Pad.Component = Nil) And PadInBox(Pad, X1, Y1, X2, Y2) And
           ((UpperCase(Ref) <> 'SW1') Or
            PadInBox(Pad, RepairCoord('61.0mm'), RepairCoord('1.0mm'),
                      RepairCoord('67.5mm'), RepairCoord('3.5mm')) Or
            PadInBox(Pad, RepairCoord('61.0mm'), RepairCoord('10.5mm'),
                      RepairCoord('67.5mm'), RepairCoord('13.0mm'))) Then
        Begin
            If Result <= 63 Then
            Begin
                Pads[Result] := Pad;
                Inc(Result);
            End;
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    PadCount := Result;

    NewComp := PCBServer.PCBObjectFactory(eComponentObject, eNoDimension,
                                          eCreate_Default);
    If NewComp = Nil Then
    Begin
        Result := 0;
        Exit;
    End;

    NewComp.SetState_Board(Board);
    NewComp.Layer := OldComp.Layer;
    NewComp.X := OldComp.X;
    NewComp.Y := OldComp.Y;
    NewComp.Rotation := OldComp.Rotation;
    NewComp.ComponentKind := OldComp.ComponentKind;
    NewComp.Pattern := OldComp.Pattern;
    NewComp.SourceDesignator := OldComp.SourceDesignator;
    NewComp.SourceUniqueId := OldComp.SourceUniqueId;
    NewComp.SourceHierarchicalPath := OldComp.SourceHierarchicalPath;
    NewComp.SourceFootprintLibrary := OldComp.SourceFootprintLibrary;
    NewComp.SourceComponentLibrary := OldComp.SourceComponentLibrary;
    NewComp.SourceLibReference := OldComp.SourceLibReference;
    NewComp.SourceDescription := OldComp.SourceDescription;
    NewComp.FootprintDescription := OldComp.FootprintDescription;
    NewComp.NameOn := OldComp.NameOn;
    NewComp.CommentOn := OldComp.CommentOn;
    NewComp.NameAutoPosition := OldComp.NameAutoPosition;
    NewComp.CommentAutoPosition := OldComp.CommentAutoPosition;
    NewComp.LockStrings := OldComp.LockStrings;
    NewComp.Height := OldComp.Height;
    WasLocked := OldComp.PrimitiveLock;
    NewComp.PrimitiveLock := False;

    For I := 0 To PadCount - 1 Do
    Begin
        NewPad := ClonePadForComponent(Board, NewComp, Pads[I]);
        If NewPad <> Nil Then
        Begin
            Board.RemovePCBObject(Pads[I]);
            NewComp.AddPCBObject(NewPad);
            NewPads[I] := NewPad;
        End;
    End;

    NewComp.SetState_XSizeYSize;
    NewComp.PrimitiveLock := WasLocked;
    Board.RemovePCBObject(OldComp);
    Board.AddPCBObject(NewComp);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                  PCBM_BoardRegisteration,
                                  NewComp.I_ObjectAddress);
    For I := 0 To PadCount - 1 Do
        If NewPads[I] <> Nil Then
            PCBServer.SendMessageToRobots(NewComp.I_ObjectAddress, c_Broadcast,
                                          PCBM_BoardRegisteration,
                                          NewPads[I].I_ObjectAddress);
    Result := PadCount;
End;

Procedure WritePreflightDiagnostics(Board : IPCB_Board);
Var
    Rpt : TStringList;
Begin
    Rpt := TStringList.Create;
    Try
        Rpt.Add('C107=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('69.0mm'), RepairCoord('30.8mm'), RepairCoord('70.0mm'), RepairCoord('32.2mm'))));
        Rpt.Add('C40=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('76.5mm'), RepairCoord('24.5mm'), RepairCoord('77.5mm'), RepairCoord('26.3mm'))));
        Rpt.Add('C90=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('15.3mm'), RepairCoord('52.5mm'), RepairCoord('16.7mm'), RepairCoord('56.5mm'))));
        Rpt.Add('C91=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('20.3mm'), RepairCoord('50.5mm'), RepairCoord('21.7mm'), RepairCoord('54.8mm'))));
        Rpt.Add('C92=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('21.5mm'), RepairCoord('58.5mm'), RepairCoord('22.5mm'), RepairCoord('61.5mm'))));
        Rpt.Add('C93=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('16.5mm'), RepairCoord('58.5mm'), RepairCoord('17.5mm'), RepairCoord('61.5mm'))));
        Rpt.Add('D3=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('76.4mm'), RepairCoord('52.7mm'), RepairCoord('77.6mm'), RepairCoord('55.3mm'))));
        Rpt.Add('D4=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('74.5mm'), RepairCoord('27.5mm'), RepairCoord('78.99mm'), RepairCoord('30.5mm'))));
        Rpt.Add('D8=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('10.3mm'), RepairCoord('55.0mm'), RepairCoord('11.7mm'), RepairCoord('59.0mm'))));
        Rpt.Add('J4=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('78.99mm'), RepairCoord('25.3mm'), RepairCoord('85.5mm'), RepairCoord('34.0mm'))));
        Rpt.Add('J5=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('82.5mm'), RepairCoord('8.5mm'), RepairCoord('86.5mm'), RepairCoord('15.0mm'))));
        Rpt.Add('J6=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('78.99mm'), RepairCoord('50.3mm'), RepairCoord('85.5mm'), RepairCoord('59.0mm'))));
        Rpt.Add('J8=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('2.5mm'), RepairCoord('51.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm'))));
        Rpt.Add('L9=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('26.0mm'), RepairCoord('55.0mm'), RepairCoord('30.0mm'), RepairCoord('59.0mm'))));
        Rpt.Add('R42=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('77.0mm'), RepairCoord('36.5mm'), RepairCoord('78.0mm'), RepairCoord('39.5mm'))));
        Rpt.Add('R605=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('71.5mm'), RepairCoord('49.5mm'), RepairCoord('72.5mm'), RepairCoord('52.5mm'))));
        Rpt.Add('R90=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('24.0mm'), RepairCoord('52.5mm'), RepairCoord('25.0mm'), RepairCoord('56.5mm'))));
        Rpt.Add('SW1_LO=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('61.0mm'), RepairCoord('1.0mm'), RepairCoord('67.5mm'), RepairCoord('3.5mm'))));
        Rpt.Add('SW1_HI=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('61.0mm'), RepairCoord('10.5mm'), RepairCoord('67.5mm'), RepairCoord('13.0mm'))));
        Rpt.Add('U4=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('69.0mm'), RepairCoord('27.0mm'), RepairCoord('72.5mm'), RepairCoord('31.0mm'))));
        Rpt.Add('U9=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('18.0mm'), RepairCoord('54.5mm'), RepairCoord('21.8mm'), RepairCoord('59.5mm'))));
        Rpt.Add('R71=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('58.5mm'), RepairCoord('8.5mm'), RepairCoord('61.0mm'), RepairCoord('10.5mm'))));
        Rpt.Add('R72=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('61.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm'), RepairCoord('10.0mm'))));
        Rpt.Add('R601=' + IntToStr(CountFreePadsInBox(Board, RepairCoord('78.4mm'), RepairCoord('55.0mm'), RepairCoord('78.9mm'), RepairCoord('57.0mm'))));
        Rpt.SaveToFile(ExtractFilePath(Board.FileName) + '..\equivalence\repair_pad_box_counts.txt');
    Finally
        Rpt.Free;
    End;
End;

Procedure RepairPadOwnership;
Var
    Board       : IPCB_Board;
    Count       : Integer;
    PreflightOK : Boolean;
Begin
    Board := PCBServer.GetPCBBoardByPath(
        'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\build-cad\history_candidate_audit_20261029_2320\EVT_SYS_CARRIER.H77_REPAIR13.PcbDoc'
    );
    If Board = Nil Then Exit;
    If (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.~(77).PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_CLEAN.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR2.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR3.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR4.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR5.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR6.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR7.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR8.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR9.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR10.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR11.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR12.PCBDOC') And
       (UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.H77_REPAIR13.PCBDOC') Then
    Begin
        ShowMessage('RepairPadOwnership requires EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    PreflightOK :=
        (CountFreePadsInBox(Board, RepairCoord('69.0mm'), RepairCoord('30.8mm'), RepairCoord('70.0mm'), RepairCoord('32.2mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('76.5mm'), RepairCoord('24.5mm'), RepairCoord('77.5mm'), RepairCoord('26.3mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('15.3mm'), RepairCoord('52.5mm'), RepairCoord('16.7mm'), RepairCoord('56.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('20.3mm'), RepairCoord('50.5mm'), RepairCoord('21.7mm'), RepairCoord('54.8mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('21.5mm'), RepairCoord('58.5mm'), RepairCoord('22.5mm'), RepairCoord('61.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('16.5mm'), RepairCoord('58.5mm'), RepairCoord('17.5mm'), RepairCoord('61.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('76.4mm'), RepairCoord('52.7mm'), RepairCoord('77.6mm'), RepairCoord('55.3mm')) = 10) And
        (CountFreePadsInBox(Board, RepairCoord('74.5mm'), RepairCoord('27.5mm'), RepairCoord('78.99mm'), RepairCoord('30.5mm')) = 3) And
        (CountFreePadsInBox(Board, RepairCoord('10.3mm'), RepairCoord('55.0mm'), RepairCoord('11.7mm'), RepairCoord('59.0mm')) = 10) And
        (CountFreePadsInBox(Board, RepairCoord('78.99mm'), RepairCoord('25.3mm'), RepairCoord('85.5mm'), RepairCoord('34.0mm')) = 7) And
        (CountFreePadsInBox(Board, RepairCoord('82.5mm'), RepairCoord('8.5mm'), RepairCoord('86.5mm'), RepairCoord('15.0mm')) = 3) And
        (CountFreePadsInBox(Board, RepairCoord('78.99mm'), RepairCoord('50.3mm'), RepairCoord('85.5mm'), RepairCoord('59.0mm')) = 7) And
        (CountFreePadsInBox(Board, RepairCoord('2.5mm'), RepairCoord('51.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm')) = 8) And
        (CountFreePadsInBox(Board, RepairCoord('26.0mm'), RepairCoord('55.0mm'), RepairCoord('30.0mm'), RepairCoord('59.0mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('77.0mm'), RepairCoord('36.5mm'), RepairCoord('78.0mm'), RepairCoord('39.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('71.5mm'), RepairCoord('49.5mm'), RepairCoord('72.5mm'), RepairCoord('52.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('24.0mm'), RepairCoord('52.5mm'), RepairCoord('25.0mm'), RepairCoord('56.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('61.0mm'), RepairCoord('1.0mm'), RepairCoord('67.5mm'), RepairCoord('3.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('61.0mm'), RepairCoord('10.5mm'), RepairCoord('67.5mm'), RepairCoord('13.0mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('69.0mm'), RepairCoord('27.0mm'), RepairCoord('72.5mm'), RepairCoord('31.0mm')) = 23) And
        (CountFreePadsInBox(Board, RepairCoord('18.0mm'), RepairCoord('54.5mm'), RepairCoord('21.8mm'), RepairCoord('59.5mm')) = 21) And
        (CountFreePadsInBox(Board, RepairCoord('58.5mm'), RepairCoord('8.5mm'), RepairCoord('61.0mm'), RepairCoord('10.5mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('61.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm'), RepairCoord('10.0mm')) = 2) And
        (CountFreePadsInBox(Board, RepairCoord('78.4mm'), RepairCoord('55.0mm'), RepairCoord('78.9mm'), RepairCoord('57.0mm')) = 2);
    If Not PreflightOK Then
    Begin
        WritePreflightDiagnostics(Board);
        ShowMessage('RepairPadOwnership stopped: compact-board pad counts do not match the audited 122-pad state.');
        Exit;
    End;

    Count := 0;
    PCBServer.PreProcess;
    Try
        Count := Count + ReplaceBrokenComponent(Board, 'C107', RepairCoord('69.0mm'), RepairCoord('30.8mm'), RepairCoord('70.0mm'), RepairCoord('32.2mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'C40', RepairCoord('76.5mm'), RepairCoord('24.5mm'), RepairCoord('77.5mm'), RepairCoord('26.3mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'C90', RepairCoord('15.3mm'), RepairCoord('52.5mm'), RepairCoord('16.7mm'), RepairCoord('56.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'C91', RepairCoord('20.3mm'), RepairCoord('50.5mm'), RepairCoord('21.7mm'), RepairCoord('54.8mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'C92', RepairCoord('21.5mm'), RepairCoord('58.5mm'), RepairCoord('22.5mm'), RepairCoord('61.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'C93', RepairCoord('16.5mm'), RepairCoord('58.5mm'), RepairCoord('17.5mm'), RepairCoord('61.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'D3', RepairCoord('76.4mm'), RepairCoord('52.7mm'), RepairCoord('77.6mm'), RepairCoord('55.3mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'D4', RepairCoord('74.5mm'), RepairCoord('27.5mm'), RepairCoord('78.99mm'), RepairCoord('30.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'D8', RepairCoord('10.3mm'), RepairCoord('55.0mm'), RepairCoord('11.7mm'), RepairCoord('59.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'J4', RepairCoord('78.99mm'), RepairCoord('25.3mm'), RepairCoord('85.5mm'), RepairCoord('34.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'J5', RepairCoord('82.5mm'), RepairCoord('8.5mm'), RepairCoord('86.5mm'), RepairCoord('15.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'J6', RepairCoord('78.99mm'), RepairCoord('50.3mm'), RepairCoord('85.5mm'), RepairCoord('59.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'J8', RepairCoord('2.5mm'), RepairCoord('51.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'L9', RepairCoord('26.0mm'), RepairCoord('55.0mm'), RepairCoord('30.0mm'), RepairCoord('59.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R42', RepairCoord('77.0mm'), RepairCoord('36.5mm'), RepairCoord('78.0mm'), RepairCoord('39.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R605', RepairCoord('71.5mm'), RepairCoord('49.5mm'), RepairCoord('72.5mm'), RepairCoord('52.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R90', RepairCoord('24.0mm'), RepairCoord('52.5mm'), RepairCoord('25.0mm'), RepairCoord('56.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'SW1', RepairCoord('61.0mm'), RepairCoord('1.0mm'), RepairCoord('67.5mm'), RepairCoord('13.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'U4', RepairCoord('69.0mm'), RepairCoord('27.0mm'), RepairCoord('72.5mm'), RepairCoord('31.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'U9', RepairCoord('18.0mm'), RepairCoord('54.5mm'), RepairCoord('21.8mm'), RepairCoord('59.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R71', RepairCoord('58.5mm'), RepairCoord('8.5mm'), RepairCoord('61.0mm'), RepairCoord('10.5mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R72', RepairCoord('61.5mm'), RepairCoord('7.0mm'), RepairCoord('62.5mm'), RepairCoord('10.0mm'));
        Count := Count + ReplaceBrokenComponent(Board, 'R601', RepairCoord('78.4mm'), RepairCoord('55.0mm'), RepairCoord('78.9mm'), RepairCoord('57.0mm'));
        Board.SetState_DocumentHasChanged;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('RepairPadOwnership complete. Attached pads: ' +
        IntToStr(Count) + ' across 23 audited compact-board components.');
End;
