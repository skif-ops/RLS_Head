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

Function AttachFreePads(Board : IPCB_Board; Ref : String;
                        X1, Y1, X2, Y2 : TCoord) : Integer;
Var
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
    Pads     : Array[0..63] Of IPCB_Pad;
    Comp     : IPCB_Component;
    I        : Integer;
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
        If (Not Pad.InComponent) And PadInBox(Pad, X1, Y1, X2, Y2) Then
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
    For I := 0 To Result - 1 Do
    Begin
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_BeginModify, c_NoEventData);
        If Not ComponentContainsPad(Comp, Pads[I]) Then
            Comp.AddPCBObject(Pads[I]);
        Pads[I].SetState_Component(Comp);
        Pads[I].SetState_InComponent(True);
        PCBServer.SendMessageToRobots(Pads[I].I_ObjectAddress, c_Broadcast,
                                      PCBM_EndModify, c_NoEventData);
    End;
    Comp.Rebuild;
    Comp.SetState_XSizeYSize;
    PCBServer.SendMessageToRobots(Comp.I_ObjectAddress, c_Broadcast,
                                  PCBM_EndModify, c_NoEventData);
End;

Procedure RepairPadOwnership;
Var
    Board  : IPCB_Board;
    Count  : Integer;
    SW1Cnt : Integer;
    D4Cnt  : Integer;
    J4Cnt  : Integer;
    J5Cnt  : Integer;
    J6Cnt  : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If UpperCase(ExtractFileName(Board.FileName)) <> 'EVT_SYS_CARRIER.PCBDOC' Then
    Begin
        ShowMessage('RepairPadOwnership requires EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        SW1Cnt := AttachFreePads(Board, 'SW1', RepairCoord('67.0mm'),
            RepairCoord('5.0mm'), RepairCoord('73.0mm'), RepairCoord('16.0mm'));
        D4Cnt := AttachFreePads(Board, 'D4', RepairCoord('85.0mm'),
            RepairCoord('28.0mm'), RepairCoord('88.0mm'), RepairCoord('31.0mm'));
        J4Cnt := AttachFreePads(Board, 'J4', RepairCoord('88.0mm'),
            RepairCoord('24.0mm'), RepairCoord('96.0mm'), RepairCoord('34.0mm'));
        J5Cnt := AttachFreePads(Board, 'J5', RepairCoord('91.0mm'),
            RepairCoord('8.0mm'), RepairCoord('96.0mm'), RepairCoord('16.0mm'));
        J6Cnt := AttachFreePads(Board, 'J6', RepairCoord('82.0mm'),
            RepairCoord('56.0mm'), RepairCoord('100.0mm'), RepairCoord('72.0mm'));
        Count := SW1Cnt + D4Cnt + J4Cnt + J5Cnt + J6Cnt;
        Board.SetState_DocumentHasChanged;
    Finally
        PCBServer.PostProcess;
    End;

    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('RepairPadOwnership complete. Attached pads: ' +
        IntToStr(Count) + ' (SW1=' + IntToStr(SW1Cnt) +
        ', D4=' + IntToStr(D4Cnt) + ', J4=' + IntToStr(J4Cnt) +
        ', J5=' + IntToStr(J5Cnt) + ', J6=' + IntToStr(J6Cnt) + ').');
End;
