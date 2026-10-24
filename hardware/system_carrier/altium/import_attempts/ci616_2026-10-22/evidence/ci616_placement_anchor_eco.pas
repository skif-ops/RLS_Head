Function FindCI616Anchor(Ref : String) : Integer;
Begin
    Result := -1;
    If Ref = 'J1' Then Result := 0;
    If Ref = 'D1' Then Result := 1;
    If Ref = 'U6' Then Result := 2;
    If Ref = 'U5' Then Result := 3;
    If Ref = 'L1' Then Result := 4;
    If Ref = 'U7' Then Result := 5;
    If Ref = 'J5' Then Result := 6;
    If Ref = 'J4' Then Result := 7;
    If Ref = 'D4' Then Result := 8;
    If Ref = 'U4' Then Result := 9;
    If Ref = 'U1' Then Result := 10;
    If Ref = 'Y1' Then Result := 11;
    If Ref = 'FB1' Then Result := 12;
    If Ref = 'U2' Then Result := 13;
    If Ref = 'U8' Then Result := 14;
    If Ref = 'J8' Then Result := 15;
    If Ref = 'D8' Then Result := 16;
    If Ref = 'U3' Then Result := 17;
    If Ref = 'Y2' Then Result := 18;
    If Ref = 'D3' Then Result := 19;
    If Ref = 'J6' Then Result := 20;
    If Ref = 'J10' Then Result := 21;
End;

Function CI616AnchorX(Index : Integer) : String;
Begin
    Result := '';
    Case Index Of
        0: Result := '5mm';
        1: Result := '13mm';
        2: Result := '22mm';
        3: Result := '34mm';
        4: Result := '42mm';
        5: Result := '62mm';
        6: Result := '95mm';
        7: Result := '95mm';
        8: Result := '87mm';
        9: Result := '80mm';
        10: Result := '52mm';
        11: Result := '36mm';
        12: Result := '65mm';
        13: Result := '52mm';
        14: Result := '24mm';
        15: Result := '5mm';
        16: Result := '11mm';
        17: Result := '72mm';
        18: Result := '65mm';
        19: Result := '84mm';
        20: Result := '96mm';
        21: Result := '50mm';
    End;
End;

Function CI616AnchorY(Index : Integer) : String;
Begin
    Result := '';
    Case Index Of
        0..6: Result := '14mm';
        7..9: Result := '30mm';
        10..12: Result := '40mm';
        13: Result := '58mm';
        14: Result := '62mm';
        15..16: Result := '66mm';
        17: Result := '58mm';
        18: Result := '50mm';
        19..20: Result := '60mm';
        21: Result := '5mm';
    End;
End;

Function CI616AnchorCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Procedure PlaceCI616HardAnchors;
Var
    Board : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Component : IPCB_Component;
    Rect : TCoordRect;
    Found : Array[0..21] Of Integer;
    I, Index, ComponentCount : Integer;
    Bad : Boolean;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('CI616 anchor ECO stopped: no active PCB.');
        Exit;
    End;
    If (ExtractFileName(Board.FileName) <> 'EVT_SYS_CARRIER.PcbDoc') Or
       (Pos('ci616-qualified', LowerCase(Board.FileName)) = 0) Then
    Begin
        ShowMessage('CI616 anchor ECO stopped: wrong PCB path.');
        Exit;
    End;

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    If (Abs(Rect.Left) > 1) Or (Abs(Rect.Bottom) > 1) Or
       (Abs(Rect.Right - CI616AnchorCoord('100mm')) > 1) Or
       (Abs(Rect.Top - CI616AnchorCoord('80mm')) > 1) Then
    Begin
        ShowMessage('CI616 anchor ECO stopped: board outline is not 0..100mm by 0..80mm.');
        Exit;
    End;

    For I := 0 To 21 Do Found[I] := 0;
    ComponentCount := 0;
    Bad := False;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        ComponentCount := ComponentCount + 1;
        Index := FindCI616Anchor(Component.SourceDesignator);
        If Index >= 0 Then
        Begin
            Found[Index] := Found[Index] + 1;
            If Component.Layer <> eTopLayer Then Bad := True;
            If Component.X <= Rect.Right Then Bad := True;
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    For I := 0 To 21 Do If Found[I] <> 1 Then Bad := True;
    If (ComponentCount <> 92) Or Bad Then
    Begin
        ShowMessage('CI616 anchor ECO stopped: expected 92 components and 22 unique top-layer unplaced anchors.');
        Exit;
    End;

    PCBServer.PreProcess;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        Index := FindCI616Anchor(Component.SourceDesignator);
        If Index >= 0 Then
        Begin
            Component.X := CI616AnchorCoord(CI616AnchorX(Index));
            Component.Y := CI616AnchorCoord(CI616AnchorY(Index));
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    PCBServer.PostProcess;
    ShowMessage('CI616 anchor ECO changed 22 component origins in memory. Save and audit the PCB.');
End;
