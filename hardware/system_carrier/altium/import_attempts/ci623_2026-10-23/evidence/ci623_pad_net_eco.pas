{ Remove two stale PCB pad-net assignments after the approved U8 pin-contract
  corrections made D_SEL and EXTINT intentionally unconnected. }

Function IsCanonicalCI623Board(Board : IPCB_Board) : Boolean;
Var
    P : String;
Begin
    Result := False;
    If Board = Nil Then Exit;
    P := LowerCase(Board.FileName);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0) And
        (ExtractFileName(Board.FileName) = 'EVT_SYS_CARRIER.PcbDoc');
End;

Procedure RepairCI623U8UnconnectedPads;
Var
    Board       : IPCB_Board;
    Iterator    : IPCB_BoardIterator;
    Pad         : IPCB_Pad;
    OldNet      : IPCB_Net;
    Ref         : String;
    Found2      : Integer;
    Found4      : Integer;
    Valid       : Boolean;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Not IsCanonicalCI623Board(Board) Then
    Begin
        ShowMessage('CI623 pad-net ECO stopped: select the canonical native EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    Found2 := 0;
    Found4 := 0;
    Valid := True;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If Pad.Component <> Nil Then
            Ref := Pad.Component.SourceDesignator
        Else
            Ref := '';

        If Ref = 'U8' Then
        Begin
            If Pad.Name = '2' Then
            Begin
                Inc(Found2);
                Valid := Valid And (Pad.Net <> Nil) And (Pad.Net.Name = 'GND');
            End;
            If Pad.Name = '4' Then
            Begin
                Inc(Found4);
                Valid := Valid And (Pad.Net <> Nil) And (Pad.Net.Name = '3V3');
            End;
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    If (Found2 <> 1) Or (Found4 <> 1) Or (Not Valid) Then
    Begin
        ShowMessage('CI623 pad-net ECO stopped: U8.2/U8.4 identity or original net mismatch.');
        Exit;
    End;

    PCBServer.PreProcess;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If Pad.Component <> Nil Then
            Ref := Pad.Component.SourceDesignator
        Else
            Ref := '';

        If (Ref = 'U8') And ((Pad.Name = '2') Or (Pad.Name = '4')) Then
        Begin
            OldNet := Pad.Net;
            If OldNet <> Nil Then
            Begin
                OldNet.RemovePCBObject(Pad);
                Pad.SetState_Net(Nil);
                OldNet.ConnectivelyInValidate;
            End;
            Pad.GraphicallyInvalidate;
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    PCBServer.PostProcess;

    ShowMessage('CI623 pad-net ECO complete: U8.2 and U8.4 set to No Net. Save and re-audit the PCB.');
End;
