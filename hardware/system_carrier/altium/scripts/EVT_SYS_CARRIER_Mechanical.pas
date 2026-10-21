{ Apply the locked EVT outline and mounting-hole datum to the active PcbDoc.
  Run ApplyEVTMechanical once on a fresh import, then audit the resulting board.
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

Procedure EVTAddMissingHoles(Board : IPCB_Board);
Begin
    PCBServer.PreProcess;
    If Not EVTHasMountingHole(Board, '5mm', '5mm') Then
        EVTMountingHole(Board, 'H1', '5mm', '5mm');
    If Not EVTHasMountingHole(Board, '95mm', '5mm') Then
        EVTMountingHole(Board, 'H2', '95mm', '5mm');
    If Not EVTHasMountingHole(Board, '5mm', '75mm') Then
        EVTMountingHole(Board, 'H3', '5mm', '75mm');
    If Not EVTHasMountingHole(Board, '95mm', '75mm') Then
        EVTMountingHole(Board, 'H4', '95mm', '75mm');
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
    If (Abs(Rect.Right - Rect.Left - EVTMechanicalCoord('100mm')) <= 1) And
       (Abs(Rect.Top - Rect.Bottom - EVTMechanicalCoord('80mm')) <= 1) Then
    Begin
        EVTAddMissingHoles(Board);
        ShowMessage('EVT mechanical datum: existing 100x80mm outline retained; missing NPTH holes added.');
        Exit;
    End;

    PCBServer.PreProcess;
    EVTOutlineTrack(Board, '3mm', '0mm', '97mm', '0mm');
    EVTOutlineArc(Board, '97mm', '3mm', 270, 360);
    EVTOutlineTrack(Board, '100mm', '3mm', '100mm', '77mm');
    EVTOutlineArc(Board, '97mm', '77mm', 0, 90);
    EVTOutlineTrack(Board, '97mm', '80mm', '3mm', '80mm');
    EVTOutlineArc(Board, '3mm', '77mm', 90, 180);
    EVTOutlineTrack(Board, '0mm', '77mm', '0mm', '3mm');
    EVTOutlineArc(Board, '3mm', '3mm', 180, 270);
    PCBServer.PostProcess;

    ResetParameters;
    AddStringParameter('MODE', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    If (Abs(Rect.Right - Rect.Left - EVTMechanicalCoord('100mm')) > 1) Or
       (Abs(Rect.Top - Rect.Bottom - EVTMechanicalCoord('80mm')) > 1) Then
    Begin
        ShowMessage('EVT mechanical datum: board outline did not match 100x80mm. No mounting holes added.');
        Exit;
    End;

    EVTAddMissingHoles(Board);

    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('EVT mechanical datum placed. Save and audit outline, corners and NPTH holes.');
End;
