{ Apply the 90x70 mm ECO candidate outline and mounting-hole datum.
  Lock the datum only after native placement, routing and DRC validation.
}

Function EVTMechanicalCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Procedure EVTOutlineTrack(Board : IPCB_Board; X1, Y1, X2, Y2 : String);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1 := EVTMechanicalCoord(X1);
    Track.Y1 := EVTMechanicalCoord(Y1);
    Track.X2 := EVTMechanicalCoord(X2);
    Track.Y2 := EVTMechanicalCoord(Y2);
    Track.Layer := eMechanical1;
    Track.Width := EVTMechanicalCoord('0.10mm');
    Board.AddPCBObject(Track);
    Track.Selected := True;
End;

Procedure EVTOutlineArc(Board : IPCB_Board; X, Y : String;
                        StartAngle, EndAngle : Double);
Var
    Arc : IPCB_Arc;
Begin
    Arc := PCBServer.PCBObjectFactory(eArcObject, eNoDimension, eCreate_Default);
    Arc.XCenter := EVTMechanicalCoord(X);
    Arc.YCenter := EVTMechanicalCoord(Y);
    Arc.Radius := EVTMechanicalCoord('3mm');
    Arc.LineWidth := EVTMechanicalCoord('0.10mm');
    Arc.StartAngle := StartAngle;
    Arc.EndAngle := EndAngle;
    Arc.Layer := eMechanical1;
    Board.AddPCBObject(Arc);
    Arc.Selected := True;
End;

Procedure EVTMountingHole(Board : IPCB_Board; NameText, X, Y : String);
Var
    Pad : IPCB_Pad;
Begin
    Pad := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    Pad.Name := NameText;
    Pad.X := EVTMechanicalCoord(X);
    Pad.Y := EVTMechanicalCoord(Y);
    Pad.Layer := eMultiLayer;
    Pad.HoleSize := EVTMechanicalCoord('3.2mm');
    Pad.TopXSize := EVTMechanicalCoord('3.2mm');
    Pad.TopYSize := EVTMechanicalCoord('3.2mm');
    Pad.MidXSize := EVTMechanicalCoord('3.2mm');
    Pad.MidYSize := EVTMechanicalCoord('3.2mm');
    Pad.BotXSize := EVTMechanicalCoord('3.2mm');
    Pad.BotYSize := EVTMechanicalCoord('3.2mm');
    Pad.Plated := False;
    Board.AddPCBObject(Pad);
End;

Function EVTHasMountingHole(Board : IPCB_Board; X, Y : String) : Boolean;
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
        If (Pad.Component = Nil) And (Not Pad.Plated) And
           (Abs(Pad.X - EVTMechanicalCoord(X)) <= 1) And
           (Abs(Pad.Y - EVTMechanicalCoord(Y)) <= 1) And
           (Abs(Pad.HoleSize - EVTMechanicalCoord('3.2mm')) <= 1) Then
            Result := True;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function EVTIsExpectedMountingHole(Pad : IPCB_Pad) : Boolean;
Begin
    Result := False;
    If UpperCase(Pad.Name) = 'H1' Then
        Result := (Abs(Pad.X - EVTMechanicalCoord('5mm')) <= 1) And
                  (Abs(Pad.Y - EVTMechanicalCoord('5mm')) <= 1)
    Else If UpperCase(Pad.Name) = 'H2' Then
        Result := (Abs(Pad.X - EVTMechanicalCoord('85mm')) <= 1) And
                  (Abs(Pad.Y - EVTMechanicalCoord('5mm')) <= 1)
    Else If UpperCase(Pad.Name) = 'H3' Then
        Result := (Abs(Pad.X - EVTMechanicalCoord('5mm')) <= 1) And
                  (Abs(Pad.Y - EVTMechanicalCoord('65mm')) <= 1)
    Else If UpperCase(Pad.Name) = 'H4' Then
        Result := (Abs(Pad.X - EVTMechanicalCoord('85mm')) <= 1) And
                  (Abs(Pad.Y - EVTMechanicalCoord('65mm')) <= 1);
End;

Procedure EVTRemoveObsoleteMountingHoles(Board : IPCB_Board);
Var
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
    NextPad  : IPCB_Pad;
    IsNamedMountingHole : Boolean;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        NextPad := Iterator.NextPCBObject;
        IsNamedMountingHole :=
            (UpperCase(Pad.Name) = 'H1') Or
            (UpperCase(Pad.Name) = 'H2') Or
            (UpperCase(Pad.Name) = 'H3') Or
            (UpperCase(Pad.Name) = 'H4');
        If (Pad.Component = Nil) And (Not Pad.Plated) And
           IsNamedMountingHole And
           (Not EVTIsExpectedMountingHole(Pad)) Then
            Board.RemovePCBObject(Pad);
        Pad := NextPad;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure EVTAddMissingHoles(Board : IPCB_Board);
Begin
    PCBServer.PreProcess;
    EVTRemoveObsoleteMountingHoles(Board);
    If Not EVTHasMountingHole(Board, '5mm', '5mm') Then
        EVTMountingHole(Board, 'H1', '5mm', '5mm');
    If Not EVTHasMountingHole(Board, '85mm', '5mm') Then
        EVTMountingHole(Board, 'H2', '85mm', '5mm');
    If Not EVTHasMountingHole(Board, '5mm', '65mm') Then
        EVTMountingHole(Board, 'H3', '5mm', '65mm');
    If Not EVTHasMountingHole(Board, '85mm', '65mm') Then
        EVTMountingHole(Board, 'H4', '85mm', '65mm');
    PCBServer.PostProcess;
End;

Procedure ApplyEVTMechanical;
Var
    Board : IPCB_Board;
    Rect  : TCoordRect;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If UpperCase(ExtractFileExt(Board.FileName)) <> '.PCBDOC' Then Exit;

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    If (Abs(Rect.Right - Rect.Left - EVTMechanicalCoord('90mm')) <= 1) And
       (Abs(Rect.Top - Rect.Bottom - EVTMechanicalCoord('70mm')) <= 1) Then
    Begin
        EVTAddMissingHoles(Board);
        ShowMessage('EVT mechanical datum: existing 90x70mm candidate retained; missing NPTH holes added.');
        Exit;
    End;

    PCBServer.PreProcess;
    EVTOutlineTrack(Board, '3mm', '0mm', '87mm', '0mm');
    EVTOutlineArc(Board, '87mm', '3mm', 270, 360);
    EVTOutlineTrack(Board, '90mm', '3mm', '90mm', '67mm');
    EVTOutlineArc(Board, '87mm', '67mm', 0, 90);
    EVTOutlineTrack(Board, '87mm', '70mm', '3mm', '70mm');
    EVTOutlineArc(Board, '3mm', '67mm', 90, 180);
    EVTOutlineTrack(Board, '0mm', '67mm', '0mm', '3mm');
    EVTOutlineArc(Board, '3mm', '3mm', 180, 270);
    PCBServer.PostProcess;

    ResetParameters;
    AddStringParameter('MODE', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    If (Abs(Rect.Right - Rect.Left - EVTMechanicalCoord('90mm')) > 1) Or
       (Abs(Rect.Top - Rect.Bottom - EVTMechanicalCoord('70mm')) > 1) Then
    Begin
        ShowMessage('EVT mechanical datum: board outline did not match 90x70mm. No mounting holes added.');
        Exit;
    End;

    EVTAddMissingHoles(Board);

    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('EVT mechanical datum placed. Save and audit outline, corners and NPTH holes.');
End;
