Function Mm(ValueMm : Double) : TCoord;
Begin
    Result := MMsToCoord(ValueMm);
End;

Procedure RegisterObject(Doc : ISch_Document; Obj : ISch_BasicContainer);
Begin
    Doc.RegisterSchObjectInContainer(Obj);
    SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
        SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
End;

Procedure AddLabel(Doc : ISch_Document; S : WideString; Xmm, Ymm : Double;
    FontSize : Integer; Bold : Boolean; TextColor : TColor);
Var
    L : ISch_Label;
Begin
    L := SchServer.SchObjectFactory(eLabel, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(Xmm), Mm(Ymm));
    L.Text := S;
    L.Color := TextColor;
    L.Orientation := eRotate0;
    L.FontID := SchServer.FontManager.GetFontID(FontSize, 0, Bold, False,
        False, False, 'Arial');
    RegisterObject(Doc, L);
End;

Procedure AddLine(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    LineColor : TColor; Width : TSize);
Var
    L : ISch_Line;
Begin
    L := SchServer.SchObjectFactory(eLine, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(X1), Mm(Y1));
    L.Corner := Point(Mm(X2), Mm(Y2));
    L.LineWidth := Width;
    L.LineStyle := eLineStyleSolid;
    L.Color := LineColor;
    RegisterObject(Doc, L);
End;

Procedure AddArrow(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    Caption : WideString);
Var
    MidX, MidY, CaptionX : Double;
Begin
    AddLine(Doc, X1, Y1, X2, Y2, $00808080, eMedium);
    If Abs(X2 - X1) >= Abs(Y2 - Y1) Then
    Begin
        If X2 >= X1 Then
        Begin
            AddLine(Doc, X2, Y2, X2 - 5, Y2 + 3, $00808080, eSmall);
            AddLine(Doc, X2, Y2, X2 - 5, Y2 - 3, $00808080, eSmall);
        End
        Else
        Begin
            AddLine(Doc, X2, Y2, X2 + 5, Y2 + 3, $00808080, eSmall);
            AddLine(Doc, X2, Y2, X2 + 5, Y2 - 3, $00808080, eSmall);
        End;
    End
    Else
    Begin
        If Y2 >= Y1 Then
        Begin
            AddLine(Doc, X2, Y2, X2 - 3, Y2 - 5, $00808080, eSmall);
            AddLine(Doc, X2, Y2, X2 + 3, Y2 - 5, $00808080, eSmall);
        End
        Else
        Begin
            AddLine(Doc, X2, Y2, X2 - 3, Y2 + 5, $00808080, eSmall);
            AddLine(Doc, X2, Y2, X2 + 3, Y2 + 5, $00808080, eSmall);
        End;
    End;
    MidX := (X1 + X2) / 2;
    MidY := (Y1 + Y2) / 2;
    If Caption = '' Then Exit;
    If Abs(X2 - X1) >= Abs(Y2 - Y1) Then
    Begin
        CaptionX := MidX - Length(Caption) * 1.7;
        AddLabel(Doc, Caption, CaptionX, MidY + 5, 18, True, $00404040);
    End
    Else
        AddLabel(Doc, Caption, MidX + 6, MidY - 3, 18, True, $00404040);
End;

Procedure AddBlock(Doc : ISch_Document; Xmm, Ymm, Wmm, Hmm : Double;
    Title, Line1, Line2, Line3, SheetRef : WideString; FillColor : TColor);
Var
    R : ISch_Rectangle;
Begin
    R := SchServer.SchObjectFactory(eRectangle, eCreate_GlobalCopy);
    If R = Nil Then Exit;
    R.Location := Point(Mm(Xmm), Mm(Ymm));
    R.Corner := Point(Mm(Xmm + Wmm), Mm(Ymm + Hmm));
    R.LineWidth := eMedium;
    R.IsSolid := True;
    R.Transparent := False;
    R.Color := $00404040;
    R.AreaColor := FillColor;
    RegisterObject(Doc, R);

    AddLabel(Doc, Title, Xmm + 8, Ymm + Hmm - 20, 24, True, $00202020);
    AddLine(Doc, Xmm + 8, Ymm + Hmm - 27, Xmm + Wmm - 8,
        Ymm + Hmm - 27, $00808080, eSmall);
    AddLabel(Doc, Line1, Xmm + 8, Ymm + Hmm - 48, 20, False, $00303030);
    AddLabel(Doc, Line2, Xmm + 8, Ymm + Hmm - 67, 20, False, $00303030);
    AddLabel(Doc, Line3, Xmm + 8, Ymm + Hmm - 86, 20, False, $00303030);
    AddLabel(Doc, SheetRef, Xmm + 8, Ymm + 9, 17, True, $00606060);
End;

Procedure ClearOverview(Doc : ISch_Document);
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
Begin
    While True Do
    Begin
        Obj := Nil;
        Iterator := Doc.SchIterator_Create;
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(eLabel, eLine, eRectangle));
        Try
            Obj := Iterator.FirstSchObject;
        Finally
            Doc.SchIterator_Destroy(Iterator);
        End;
        If Obj = Nil Then Break;
        Doc.RemoveSchObject(Obj);
        SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
            SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
    End;
End;

Procedure CreateSystemOverview;
Var
    Doc       : ISch_Document;
    ServerDoc : IServerDocument;
Begin
    If SchServer = Nil Then Exit;
    Doc := SchServer.GetCurrentSchDocument;
    If Doc = Nil Then
    Begin
        ShowMessage('Open 00_SYSTEM_OVERVIEW.SchDoc before running this script.');
        Exit;
    End;

    If ExtractFileName(Doc.DocumentName) <> '00_SYSTEM_OVERVIEW.SchDoc' Then
    Begin
        ShowMessage('The active document is not 00_SYSTEM_OVERVIEW.SchDoc.');
        Exit;
    End;

    SchServer.ProcessControl.PreProcess(Doc, '');
    Try
        ClearOverview(Doc);
        Doc.UseCustomSheet := True;
        Doc.CustomSheetStyle := 'A1 Landscape';
        Doc.CustomX := Mm(841);
        Doc.CustomY := Mm(594);
        Doc.CustomMarginWidth := Mm(10);
        Doc.BorderOn := True;
        Doc.ReferenceZonesOn := True;
        Doc.TitleBlockOn := False;
        Doc.SnapGridOn := True;
        Doc.SnapGridSize := Mm(1);
        Doc.VisibleGridOn := True;
        Doc.VisibleGridSize := Mm(10);

        AddLabel(Doc, 'RADAR D79 24V / SYSTEM OVERVIEW / PCB v0.8.0 R9',
            25, 570, 36, True, $00202020);
        AddLabel(Doc, 'Civil drone tracking system. Measurement and target-state output only. No motion-control commands.',
            25, 548, 22, False, $00404040);
        AddLabel(Doc, 'Overview sheet 00 / detailed electrical design: sheets 01-31',
            25, 528, 20, False, $00606060);

        AddBlock(Doc, 25, 395, 160, 115,
            '24 V INPUT',
            'Reverse and surge protection',
            'eFuse, UVLO/OVP, current limit',
            'Protected 24 V system rail',
            'DETAIL: sheets 01-04', $00EAF4FF);

        AddBlock(Doc, 225, 395, 160, 115,
            'POWER RAILS',
            '24 V to 12 V conversion',
            '3.3 / 1.8 / 1.2 / 1.0 V rails',
            'Sequencing, filters, test points',
            'DETAIL: sheets 19-31', $00FFF3E0);

        AddBlock(Doc, 445, 395, 160, 115,
            'AWR2944P RADAR',
            'FMCW chirps, four coherent RX',
            'Range, Doppler and phase angles',
            'Detection and target tracking only',
            'DETAIL: sheets 13-15 and 21-31', $00E8F7EE);

        AddBlock(Doc, 645, 395, 160, 115,
            '76-81 GHz ARRAY',
            '4 TX and 4 coherent RX channels',
            'Eight patches in each antenna',
            'Wide elevation, phase angle estimate',
            'DETAIL: PCB RF layout and antenna report', $00F1ECFF);

        AddBlock(Doc, 445, 220, 160, 125,
            'STM32 HOST MCU',
            'Power control and radar start-up',
            'IMU/GNSS time and attitude fusion',
            'Target-state output and diagnostics',
            'DETAIL: sheets 09-11', $00F2F2F2);

        AddBlock(Doc, 225, 220, 160, 125,
            'IMU',
            'Angular rate and acceleration',
            'Carrier attitude correction',
            'Bias and drift calibration',
            'DETAIL: sheet 12', $00FFFCE6);

        AddBlock(Doc, 25, 220, 160, 125,
            'EXTERNAL GNSS',
            'Connector, no soldering required',
            'Time mark and navigation status',
            'Optional for radar-only tracking',
            'DETAIL: sheet 08', $00E6FAFF);

        AddBlock(Doc, 645, 220, 160, 125,
            '2 x UART 3.3 V',
            'Independent protected TX/RX',
            'Target state and diagnostics',
            'USB-UART bench adapter supported',
            'DETAIL: sheet 05', $00F5F5F5);

        AddBlock(Doc, 445, 45, 160, 125,
            'SERVICE USB',
            'Host and radar service access',
            'Logs, configuration, calibration',
            'ESD protection and VBUS sensing',
            'DETAIL: sheets 16-18', $00F5F5F5);

        AddBlock(Doc, 225, 45, 160, 125,
            'CAN FD',
            'Host and bench diagnostics',
            'Sequence, CRC and timeout checks',
            'No motion-control commands',
            'DETAIL: sheet 06', $00F5F5F5);

        AddBlock(Doc, 25, 45, 160, 125,
            'BOOT AND DEBUG',
            'SWD, reset and boot settings',
            'First-power-up test points',
            'Firmware recovery access',
            'DETAIL: sheet 07', $00F5F5F5);

        AddBlock(Doc, 645, 45, 160, 125,
            'FUNCTIONAL FLOW',
            'Echo to range, speed and angles',
            'Detections to filtered target track',
            'Track to target-state output only',
            'DETAIL: algorithms and interface docs', $00FFF8E7);

        AddArrow(Doc, 185, 452, 225, 452, 'PROTECTED 24 V');
        AddArrow(Doc, 385, 452, 445, 452, '12 V + AUX');
        AddArrow(Doc, 605, 452, 645, 452, 'COHERENT RF');
        AddArrow(Doc, 525, 395, 525, 345, 'CONTROL + DATA');
        AddArrow(Doc, 385, 282, 445, 282, 'SPI + INT');
        AddArrow(Doc, 605, 282, 645, 282, 'UART 1 / 2');
        AddLine(Doc, 105, 345, 105, 370, $00808080, eMedium);
        AddLine(Doc, 105, 370, 485, 370, $00808080, eMedium);
        AddArrow(Doc, 485, 370, 485, 345, '');
        AddLabel(Doc, 'GNSS UART + PPS', 245, 376, 18, True, $00404040);
        AddArrow(Doc, 525, 220, 525, 170, 'USB SERVICE');
        AddLine(Doc, 105, 170, 105, 210, $00808080, eMedium);
        AddLine(Doc, 105, 210, 465, 210, $00808080, eMedium);
        AddArrow(Doc, 465, 210, 465, 220, '');
        AddLabel(Doc, 'SWD / RESET / BOOT', 145, 216, 18, True, $00404040);
        AddLine(Doc, 305, 170, 305, 190, $00808080, eMedium);
        AddLine(Doc, 305, 190, 495, 190, $00808080, eMedium);
        AddArrow(Doc, 495, 190, 495, 220, '');
        AddLabel(Doc, 'CAN FD', 350, 196, 18, True, $00404040);
        AddArrow(Doc, 605, 107, 645, 107, 'TARGET STATE');
    Finally
        SchServer.ProcessControl.PostProcess(Doc, '');
    End;

    Doc.GraphicallyInvalidate;
    ServerDoc := Client.GetDocumentByPath(Doc.DocumentName);
    If ServerDoc = Nil Then
        ServerDoc := Client.GetDocumentByPath(Doc.DocumentName);
    If ServerDoc <> Nil Then
    Begin
        ServerDoc.Modified := True;
        ServerDoc.DoFileSave('Advanced Schematic binary');
    End;
    ShowMessage('R9 system overview created and saved.');
End;
