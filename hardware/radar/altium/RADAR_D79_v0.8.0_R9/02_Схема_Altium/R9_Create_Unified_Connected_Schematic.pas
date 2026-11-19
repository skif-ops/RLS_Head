Var
    GSourceDocs : Array[1..31] Of ISch_Document;
    GOffsetXs   : Array[1..31] Of TCoord;
    GOffsetYs   : Array[1..31] Of TCoord;

Function Mm(ValueMm : Double) : TCoord;
Begin
    Result := MMsToCoord(ValueMm);
End;

Function UnMm(ValueCoord : TCoord) : Double;
Begin
    Result := CoordToMMs(ValueCoord);
End;

Function SnapCoordToMils(ValueCoord : TCoord; GridMils : Integer) : TCoord;
Begin
    Result := MilsToCoord(Round(CoordToMils(ValueCoord) / GridMils) *
        GridMils);
End;

Function CsvFloat(Value : Double) : String;
Begin
    Result := StringReplace(FormatFloat('0.000', Value), ',', '.',
        rfReplaceAll);
End;

Function FindR9Project : IProject;
Var
    WS : IWorkspace;
    I  : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    For I := 0 To WS.DM_ProjectCount - 1 Do
        If ExtractFileName(WS.DM_Projects(I).DM_ProjectFullPath) =
            'RADAR_D79_24V_R9.PrjPcb' Then
        Begin
            Result := WS.DM_Projects(I);
            Exit;
        End;
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

Procedure AddVerticalLabel(Doc : ISch_Document; S : WideString;
    Xmm, Ymm : Double; FontSize : Integer; Bold : Boolean;
    TextColor : TColor);
Var
    L : ISch_Label;
Begin
    L := SchServer.SchObjectFactory(eLabel, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(Xmm), Mm(Ymm));
    L.Text := S;
    L.Color := TextColor;
    L.Orientation := eRotate90;
    L.FontID := SchServer.FontManager.GetFontID(FontSize, 0, Bold, False,
        False, False, 'Arial');
    RegisterObject(Doc, L);
End;

Procedure AddLine(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    LineColor : TColor; LineWidth : TSize);
Var
    L : ISch_Line;
Begin
    L := SchServer.SchObjectFactory(eLine, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(X1), Mm(Y1));
    L.Corner := Point(Mm(X2), Mm(Y2));
    L.Color := LineColor;
    L.LineWidth := LineWidth;
    RegisterObject(Doc, L);
End;

Procedure AddWire(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    WireColor : TColor; WireWidth : TSize);
Var
    W : ISch_Wire;
Begin
    W := SchServer.SchObjectFactory(eWire, eCreate_GlobalCopy);
    If W = Nil Then Exit;
    W.SetState_VerticesCount(2);
    W.SetState_Vertex(1, Point(Mm(X1), Mm(Y1)));
    W.SetState_Vertex(2, Point(Mm(X2), Mm(Y2)));
    W.Color := WireColor;
    W.LineWidth := WireWidth;
    RegisterObject(Doc, W);
End;

Procedure AddNetLabel(Doc : ISch_Document; S : WideString; Xmm, Ymm : Double;
    FontSize : Integer; TextColor : TColor);
Var
    L : ISch_NetLabel;
Begin
    L := SchServer.SchObjectFactory(eNetLabel, eCreate_GlobalCopy);
    If L = Nil Then Exit;
    L.Location := Point(Mm(Xmm), Mm(Ymm));
    L.Text := S;
    L.Color := TextColor;
    L.Orientation := eRotate0;
    L.FontID := SchServer.FontManager.GetFontID(FontSize, 0, False, False,
        False, False, 'Arial');
    RegisterObject(Doc, L);
End;

Procedure AddRectangle(Doc : ISch_Document; X1, Y1, X2, Y2 : Double;
    LineColor, FillColor : TColor; Filled : Boolean; LineWidth : TSize);
Var
    R : ISch_Rectangle;
Begin
    R := SchServer.SchObjectFactory(eRectangle, eCreate_GlobalCopy);
    If R = Nil Then Exit;
    R.Location := Point(Mm(X1), Mm(Y1));
    R.Corner := Point(Mm(X2), Mm(Y2));
    R.Color := LineColor;
    R.AreaColor := FillColor;
    R.IsSolid := Filled;
    R.LineWidth := LineWidth;
    RegisterObject(Doc, R);
End;

Procedure ClearCurrentSheet(Doc : ISch_Document);
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
    NextObj  : ISch_BasicContainer;
    Removed  : Integer;
Begin
    Removed := 0;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Try
        Obj := Iterator.FirstSchObject;
        While (Obj <> Nil) And (Removed < 50000) Do
        Begin
            { Cache the next primitive before removing the current one. This
              keeps the iterator valid and avoids rebuilding it for every
              object on the large unified sheet. }
            NextObj := Iterator.NextSchObject;
            Doc.RemoveSchObject(Obj);
            SchServer.RobotManager.SendMessage(Doc.I_ObjectAddress, c_BroadCast,
                SCHM_PrimitiveRegistration, Obj.I_ObjectAddress);
            Removed := Removed + 1;
            Obj := NextObj;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure AddPatchArray(Doc : ISch_Document; Xmm, Ymm : Double;
    ChannelName, PinName : String; ChannelColor : TColor);
Var
    I : Integer;
Begin
    AddLabel(Doc, ChannelName + '  ' + PinName, Xmm, Ymm + 3.0,
        10, True, ChannelColor);
    AddLine(Doc, Xmm + 55.0, Ymm + 1.0, Xmm + 75.0, Ymm + 1.0,
        ChannelColor, eSmall);
    For I := 0 To 7 Do
        AddRectangle(Doc,
            Xmm + 78.0 + I * 8.5, Ymm - 3.0,
            Xmm + 84.0 + I * 8.5, Ymm + 5.0,
            ChannelColor, ChannelColor, True, eSmall);
End;

Procedure AddRfAntennaTile(Doc : ISch_Document; X0, Y0 : Double);
Var
    RedColor  : TColor;
    BlueColor : TColor;
    DarkColor : TColor;
Begin
    RedColor := $000000C0;
    BlueColor := $00C00000;
    DarkColor := $00303030;

    AddLabel(Doc, 'RF TRACT AND PRINTED ANTENNA ARRAYS', X0 + 12.0,
        Y0 + 285.0, 13, True, DarkColor);
    AddLabel(Doc, '76 to 81 GHz / 4 TX + 4 coherent RX / eight patches per channel',
        X0 + 12.0, Y0 + 270.0, 9, False, DarkColor);
    AddRectangle(Doc, X0 + 12.0, Y0 + 35.0, X0 + 110.0, Y0 + 248.0,
        DarkColor, $00F0F0F0, True, eMedium);
    AddLabel(Doc, 'RAD_U29', X0 + 34.0, Y0 + 220.0, 12, True, DarkColor);
    AddLabel(Doc, 'AWR2944P', X0 + 28.0, Y0 + 204.0, 12, True, DarkColor);
    AddLabel(Doc, 'FMCW RF front end', X0 + 21.0, Y0 + 180.0,
        9, False, DarkColor);
    AddLabel(Doc, 'coherent TX/RX', X0 + 24.0, Y0 + 164.0,
        9, False, DarkColor);
    AddLabel(Doc, 'phase angle inputs', X0 + 22.0, Y0 + 148.0,
        9, False, DarkColor);

    AddPatchArray(Doc, X0 + 124.0, Y0 + 230.0, 'TX1', 'TI_TX1 / B3', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 204.0, 'TX2', 'TI_TX2 / B5', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 178.0, 'TX3', 'TI_TX3 / B7', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 152.0, 'TX4', 'TI_TX4 / B9', RedColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 118.0, 'RX1', 'TI_RX1 / M2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 92.0, 'RX2', 'TI_RX2 / K2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 66.0, 'RX3', 'TI_RX3 / H2', BlueColor);
    AddPatchArray(Doc, X0 + 124.0, Y0 + 40.0, 'RX4', 'TI_RX4 / F2', BlueColor);

    AddLabel(Doc,
        'Controlled-impedance feeds and matching geometry are implemented in PCB copper.',
        X0 + 12.0, Y0 + 18.0, 8, False, DarkColor);
End;

Procedure AddCompactPatchArray(Doc : ISch_Document; Xmm, Ymm : Double;
    ChannelName, PinName, NetName : String; ChannelColor : TColor);
Var
    I       : Integer;
    WireX0  : Double;
    WireX1  : Double;
    WireY   : Double;
Begin
    AddLabel(Doc, ChannelName, Xmm, Ymm + 0.5, 6, True, ChannelColor);
    AddLabel(Doc, PinName, Xmm + 12.0, Ymm + 0.5, 5, False, ChannelColor);
    WireX0 := UnMm(SnapCoordToMils(Mm(Xmm + 31.0), 10));
    WireX1 := UnMm(SnapCoordToMils(Mm(Xmm + 39.0), 10));
    WireY := UnMm(SnapCoordToMils(Mm(Ymm), 10));
    AddWire(Doc, WireX0, WireY, WireX1, WireY,
        ChannelColor, eSmall);
    AddNetLabel(Doc, NetName, WireX0, WireY, 5, ChannelColor);
    For I := 0 To 7 Do
        AddRectangle(Doc,
            Xmm + 41.0 + I * 4.6, Ymm - 1.5,
            Xmm + 44.2 + I * 4.6, Ymm + 1.5,
            ChannelColor, ChannelColor, True, eZeroSize);
End;

Procedure AddCompactRfAntennaTile(Doc : ISch_Document; X0, Y0 : Double);
Var
    RedColor  : TColor;
    BlueColor : TColor;
    DarkColor : TColor;
Begin
    RedColor := $000000C0;
    BlueColor := $00C00000;
    DarkColor := $00303030;

    AddLabel(Doc, 'RF FRONT END AND PRINTED ANTENNA', X0 + 5.0,
        Y0 + 134.0, 8, True, DarkColor);
    AddLabel(Doc, 'AWR2944P / coherent 4 TX + 4 RX / 8 patches per channel',
        X0 + 5.0, Y0 + 126.0, 5, False, DarkColor);
    AddRectangle(Doc, X0 + 5.0, Y0 + 26.0, X0 + 37.0, Y0 + 116.0,
        DarkColor, $00F0F0F0, True, eSmall);
    AddLabel(Doc, 'RAD_U29', X0 + 10.0, Y0 + 96.0, 7, True, DarkColor);
    AddLabel(Doc, 'AWR2944P', X0 + 8.0, Y0 + 86.0, 7, True, DarkColor);
    AddLabel(Doc, 'FMCW', X0 + 13.0, Y0 + 70.0, 6, False, DarkColor);
    AddLabel(Doc, 'RF', X0 + 16.0, Y0 + 61.0, 6, False, DarkColor);

    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 113.0,
        'TX1', 'B3', 'TI_TX1', RedColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 101.0,
        'TX2', 'B5', 'TI_TX2', RedColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 89.0,
        'TX3', 'B7', 'TI_TX3', RedColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 77.0,
        'TX4', 'B9', 'TI_TX4', RedColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 61.0,
        'RX1', 'M2', 'TI_RX1', BlueColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 49.0,
        'RX2', 'K2', 'TI_RX2', BlueColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 37.0,
        'RX3', 'H2', 'TI_RX3', BlueColor);
    AddCompactPatchArray(Doc, X0 + 43.0, Y0 + 25.0,
        'RX4', 'F2', 'TI_RX4', BlueColor);

    AddLabel(Doc, '50 ohm RF feeds and matching geometry are defined by PCB rules.',
        X0 + 5.0, Y0 + 10.0, 5, False, DarkColor);
End;

Function NormalizeNetName(NetName : String) : String;
Begin
    Result := NetName;
    If NetName = 'TI_NetR3_2' Then
        Result := 'TI_MSS_I2CA_SCL'
    Else If NetName = 'TI_NetR31_2' Then
        Result := 'TI_MSS_I2CA_SDA'
    Else If NetName = 'TI_NetR380_2' Then
        Result := 'TI_PMIC_SPI_CLK'
    Else If NetName = 'TI_NetR381_2' Then
        Result := 'TI_PMIC_SPI_MOSI'
    Else If NetName = 'TI_MSS_SPIB_MISO' Then
        Result := 'TI_PMIC_SPI_MISO'
    Else If NetName = 'TI_MSS_SPIB_CS0' Then
        Result := 'TI_PMIC_SPI_CS0'
    Else If NetName = 'TI_PMIC_CLK' Then
        Result := 'TI_SOP2_PMIC_CLK';
End;

Function IsDetailSheet(FileName : String) : Boolean;
Var
    N : Integer;
Begin
    Result := False;
    If Length(FileName) < 3 Then Exit;
    If FileName[3] <> '_' Then Exit;
    N := StrToIntDef(Copy(FileName, 1, 2), 0);
    Result := (N >= 1) And (N <= 31) And
        (LowerCase(ExtractFileExt(FileName)) = '.schdoc');
End;

Function LoadSchDocument(Path : String) : ISch_Document;
Var
    ServerDoc : IServerDocument;
Begin
    Result := SchServer.GetSchDocumentByPath(Path);
    If Result <> Nil Then Exit;
    ServerDoc := Client.OpenDocument('SCH', Path);
    If ServerDoc = Nil Then Exit;
    Client.ShowDocument(ServerDoc);
    Application.ProcessMessages;
    Result := SchServer.GetSchDocumentByPath(Path);
End;

Function FindNetAnchorAt(Doc : ISch_Document; NetName : String;
    MatchIndex : Integer; Var AnchorX, AnchorY : TCoord) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
    LabelObj : ISch_NetLabel;
    CurrentIndex : Integer;
Begin
    Result := False;
    CurrentIndex := 0;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNetLabel));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            LabelObj := Obj;
            If SameText(Trim(LabelObj.Text), Trim(NetName)) Then
            Begin
                If CurrentIndex = MatchIndex Then
                Begin
                    AnchorX := LabelObj.Location.X;
                    AnchorY := LabelObj.Location.Y;
                    Result := True;
                    Exit;
                End;
                CurrentIndex := CurrentIndex + 1;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function FindNetAnchor(Doc : ISch_Document; NetName : String;
    Var AnchorX, AnchorY : TCoord) : Boolean;
Begin
    Result := FindNetAnchorAt(Doc, NetName, 0, AnchorX, AnchorY);
End;

Function CollectBounds(Doc : ISch_Document;
    Var MinX, MinY, MaxX, MaxY : TCoord) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
    R        : TCoordRect;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            R := Obj.BoundingRectangle_Full;
            If Not Result Then
            Begin
                MinX := R.Left;
                MinY := R.Bottom;
                MaxX := R.Right;
                MaxY := R.Top;
                Result := True;
            End
            Else
            Begin
                If R.Left < MinX Then MinX := R.Left;
                If R.Bottom < MinY Then MinY := R.Bottom;
                If R.Right > MaxX Then MaxX := R.Right;
                If R.Top > MaxY Then MaxY := R.Top;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function ReplicateSheet(SourceDoc, TargetDoc : ISch_Document;
    OffsetX, OffsetY, SourceCenterX : TCoord) : Integer;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_BasicContainer;
    NewObj   : ISch_BasicContainer;
    NewGraph : ISch_GraphicalObject;
    NewNetLabel : ISch_NetLabel;
Begin
    Result := 0;
    Iterator := SourceDoc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            { No ERC directives are recreated from the audited disposition
              manifest. Copying source directives can leave stale floating
              markers after the sheet is moved into the master drawing. }
            If Obj.ObjectID <> eNoERC Then
            Begin
                NewObj := Obj.Replicate;
                If NewObj <> Nil Then
                Begin
                    If NewObj.ObjectID = eNetLabel Then
                    Begin
                        NewNetLabel := NewObj;
                        NewNetLabel.Text := NormalizeNetName(NewNetLabel.Text);
                        { Keep labels horizontal and place the text on the
                          component side of the anchor. }
                        NewNetLabel.Orientation := eRotate0;
                        If NewNetLabel.Location.X > SourceCenterX Then
                            NewNetLabel.Justification := eJustify_BottomRight
                        Else
                            NewNetLabel.Justification := eJustify_BottomLeft;
                    End;
                    NewGraph := NewObj;
                    NewGraph.MoveByXY(OffsetX, OffsetY);
                    RegisterObject(TargetDoc, NewObj);
                    Result := Result + 1;
                End;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        SourceDoc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure ApplyKnownPinDirections(Doc : ISch_Document;
    Var CorrectedCount : Integer);
Var
    Components : ISch_Iterator;
    Pins       : ISch_Iterator;
    Component  : ISch_Component;
    Pin        : ISch_Pin;
Begin
    CorrectedCount := 0;
    Components := Doc.SchIterator_Create;
    If Components = Nil Then Exit;
    Components.SetState_IterationDepth(eIterateFirstLevel);
    Components.AddFilter_ObjectSet(MkSet(eSchComponent));
    Try
        Component := Components.FirstSchObject;
        While Component <> Nil Do
        Begin
            If UpperCase(Component.Designator.Text) = 'U_USB' Then
            Begin
                Pins := Component.SchIterator_Create;
                If Pins <> Nil Then
                Begin
                    Pins.AddFilter_ObjectSet(MkSet(ePin));
                    Try
                        Pin := Pins.FirstSchObject;
                        While Pin <> Nil Do
                        Begin
                            { CP2102N QFN20 pin 17 is TXD, so it is the active
                              source for TI_XDSET_UARTA_TX. }
                            If (Pin.Designator = '17') And
                               (Pin.Electrical <> eElectricOutput) Then
                            Begin
                                SchServer.RobotManager.SendMessage(
                                    Pin.I_ObjectAddress, c_BroadCast,
                                    SCHM_BeginModify, c_NoEventData);
                                Pin.SetState_Electrical(eElectricOutput);
                                SchServer.RobotManager.SendMessage(
                                    Pin.I_ObjectAddress, c_BroadCast,
                                    SCHM_EndModify, c_NoEventData);
                                Pin.GraphicallyInvalidate;
                                CorrectedCount := CorrectedCount + 1;
                            End;
                            Pin := Pins.NextSchObject;
                        End;
                    Finally
                        Component.SchIterator_Destroy(Pins);
                    End;
                End;
            End;
            Component := Components.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Components);
    End;
End;

Function CsvField(Line : String; FieldIndex : Integer) : String;
Var
    I          : Integer;
    Current    : Integer;
    StartPos   : Integer;
    InQuotes   : Boolean;
    Ch         : Char;
Begin
    Result := '';
    Current := 0;
    StartPos := 1;
    InQuotes := False;
    For I := 1 To Length(Line) + 1 Do
    Begin
        If I <= Length(Line) Then Ch := Line[I] Else Ch := ',';
        If Ch = '"' Then InQuotes := Not InQuotes;
        If (Ch = ',') And (Not InQuotes) Then
        Begin
            If Current = FieldIndex Then
            Begin
                Result := Copy(Line, StartPos, I - StartPos);
                Result := StringReplace(Result, '"', '', rfReplaceAll);
                Exit;
            End;
            Current := Current + 1;
            StartPos := I + 1;
        End;
    End;
End;

Function HasNoERCAt(Doc : ISch_Document; P : TLocation) : Boolean;
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
Begin
    Result := False;
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNoERC));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            If (Abs(Obj.Location.X - P.X) <= MilsToCoord(1)) And
               (Abs(Obj.Location.Y - P.Y) <= MilsToCoord(1)) Then
            Begin
                Result := True;
                Exit;
            End;
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure AddNoERC(Doc : ISch_Document; P : TLocation);
Var
    Directive : ISch_GraphicalObject;
Begin
    Directive := SchServer.SchObjectFactory(eNoERC, eCreate_GlobalCopy);
    If Directive = Nil Then Exit;
    Directive.Location := P;
    Directive.Color := $000000FF;
    RegisterObject(Doc, Directive);
End;

Function FindTranslatedSinglePinAnchor(NetName, Ref, PinNumber : String;
    Var AnchorPoint : TLocation) : Boolean;
Var
    SheetNo    : Integer;
    Components : ISch_Iterator;
    Pins       : ISch_Iterator;
    Component  : ISch_Component;
    Pin        : ISch_Pin;
    AnchorX    : TCoord;
    AnchorY    : TCoord;
Begin
    Result := False;
    For SheetNo := 1 To 31 Do
    Begin
        If GSourceDocs[SheetNo] = Nil Then Continue;
        Components := GSourceDocs[SheetNo].SchIterator_Create;
        If Components = Nil Then Continue;
        Components.SetState_IterationDepth(eIterateFirstLevel);
        Components.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Components.FirstSchObject;
            While Component <> Nil Do
            Begin
                If Component.Designator.Text = Ref Then
                Begin
                    Pins := Component.SchIterator_Create;
                    If Pins <> Nil Then
                    Begin
                        Pins.AddFilter_ObjectSet(MkSet(ePin));
                        Try
                            Pin := Pins.FirstSchObject;
                            While Pin <> Nil Do
                            Begin
                                If Pin.Designator = PinNumber Then
                                Begin
                                    { ERC attaches a named single-pin-net
                                      violation to the net-label/wire anchor,
                                      not necessarily to the symbol pin body.
                                      Use that source anchor and the exact sheet
                                      translation used by the primitive copier. }
                                    If FindNetAnchor(GSourceDocs[SheetNo],
                                        NetName, AnchorX, AnchorY) Then
                                        AnchorPoint := Point(
                                            AnchorX + GOffsetXs[SheetNo],
                                            AnchorY + GOffsetYs[SheetNo])
                                    Else
                                        AnchorPoint := Point(
                                            Pin.Location.X +
                                                GOffsetXs[SheetNo],
                                            Pin.Location.Y +
                                                GOffsetYs[SheetNo]);
                                    Result := True;
                                    Exit;
                                End;
                                Pin := Pins.NextSchObject;
                            End;
                        Finally
                            Component.SchIterator_Destroy(Pins);
                        End;
                    End;
                End;
                Component := Components.NextSchObject;
            End;
        Finally
            GSourceDocs[SheetNo].SchIterator_Destroy(Components);
        End;
    End;
End;

Function ApplyNoERCToNet(Doc : ISch_Document; NetName, Ref,
    PinNumber : String; Var WasExisting : Boolean;
    Var AppliedPoint : TLocation) : Boolean;
Begin
    Result := False;
    WasExisting := False;
    If Not FindTranslatedSinglePinAnchor(NetName, Ref, PinNumber,
        AppliedPoint) Then Exit;
    WasExisting := HasNoERCAt(Doc, AppliedPoint);
    If Not WasExisting Then AddNoERC(Doc, AppliedPoint);
    Result := True;
End;

Procedure ApplySinglePinDispositions(Doc : ISch_Document; BasePath : String;
    Var AppliedCount, ExistingCount, MissingCount : Integer);
Var
    Rows        : TStringList;
    Audit       : TStringList;
    FilePath    : String;
    AuditPath   : String;
    I           : Integer;
    NetName     : String;
    Ref         : String;
    PinNumber   : String;
    Disposition : String;
    Suppress    : String;
    WasExisting : Boolean;
    PinPoint    : TLocation;
    CoordinateText : String;
Begin
    AppliedCount := 0;
    ExistingCount := 0;
    MissingCount := 0;
    FilePath := BasePath + 'R9_single_pin_dispositions.csv';
    AuditPath := BasePath + 'R9_unified_flat_nc_application.csv';
    Audit := TStringList.Create;
    Audit.Add('Net,Ref,Pin,Disposition,Application,NoERC_X_mil,NoERC_Y_mil');
    If Not FileExists(FilePath) Then
    Begin
        Audit.Add('MANIFEST_MISSING,,,,FAIL');
        Audit.SaveToFile(AuditPath);
        Audit.Free;
        MissingCount := 1;
        Exit;
    End;

    Rows := TStringList.Create;
    Rows.LoadFromFile(FilePath);
    For I := 1 To Rows.Count - 1 Do
    Begin
        NetName := CsvField(Rows[I], 0);
        Ref := CsvField(Rows[I], 1);
        PinNumber := CsvField(Rows[I], 2);
        Disposition := CsvField(Rows[I], 3);
        Suppress := UpperCase(CsvField(Rows[I], 4));
        If Suppress <> 'YES' Then Continue;
        CoordinateText := ',,';
        If ApplyNoERCToNet(Doc, NetName, Ref, PinNumber, WasExisting,
            PinPoint) Then
        Begin
            CoordinateText := ',' +
                StringReplace(FormatFloat('0.001', CoordToMils(PinPoint.X)),
                    ',', '.', rfReplaceAll) + ',' +
                StringReplace(FormatFloat('0.001', CoordToMils(PinPoint.Y)),
                    ',', '.', rfReplaceAll);
            If WasExisting Then
            Begin
                ExistingCount := ExistingCount + 1;
                Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                    Disposition + ',EXISTING' + CoordinateText)
            End
            Else
            Begin
                AppliedCount := AppliedCount + 1;
                Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                    Disposition + ',APPLIED' + CoordinateText);
            End;
        End
        Else
        Begin
            MissingCount := MissingCount + 1;
            Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                Disposition + ',PIN_NOT_FOUND' + CoordinateText);
        End;
    End;
    Rows.Free;
    Audit.SaveToFile(AuditPath);
    Audit.Free;
End;

Procedure ApplyNoDriverDispositions(Doc : ISch_Document; BasePath : String;
    Var AppliedCount, ExistingCount, MissingCount : Integer);
Var
    Rows        : TStringList;
    Audit       : TStringList;
    FilePath    : String;
    AuditPath   : String;
    I           : Integer;
    NetName     : String;
    Ref         : String;
    PinNumber   : String;
    Reason      : String;
    Suppress    : String;
    WasExisting : Boolean;
    PinPoint    : TLocation;
    CoordinateText : String;
Begin
    AppliedCount := 0;
    ExistingCount := 0;
    MissingCount := 0;
    FilePath := BasePath + 'R9_no_driver_dispositions.csv';
    AuditPath := BasePath + 'R9_unified_flat_no_driver_application.csv';
    Audit := TStringList.Create;
    Audit.Add('Net,Ref,Pin,Reason,Application,NoERC_X_mil,NoERC_Y_mil');
    If Not FileExists(FilePath) Then
    Begin
        Audit.Add('MANIFEST_MISSING,,,,FAIL');
        Audit.SaveToFile(AuditPath);
        Audit.Free;
        MissingCount := 1;
        Exit;
    End;

    Rows := TStringList.Create;
    Rows.LoadFromFile(FilePath);
    For I := 1 To Rows.Count - 1 Do
    Begin
        NetName := CsvField(Rows[I], 0);
        Ref := CsvField(Rows[I], 1);
        PinNumber := CsvField(Rows[I], 2);
        Reason := CsvField(Rows[I], 3);
        Suppress := UpperCase(CsvField(Rows[I], 4));
        If Suppress <> 'YES' Then Continue;
        CoordinateText := ',,';
        If ApplyNoERCToNet(Doc, NetName, Ref, PinNumber, WasExisting,
            PinPoint) Then
        Begin
            CoordinateText := ',' +
                StringReplace(FormatFloat('0.001', CoordToMils(PinPoint.X)),
                    ',', '.', rfReplaceAll) + ',' +
                StringReplace(FormatFloat('0.001', CoordToMils(PinPoint.Y)),
                    ',', '.', rfReplaceAll);
            If WasExisting Then
            Begin
                ExistingCount := ExistingCount + 1;
                Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                    Reason + ',EXISTING' + CoordinateText)
            End
            Else
            Begin
                AppliedCount := AppliedCount + 1;
                Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                    Reason + ',APPLIED' + CoordinateText);
            End;
        End
        Else
        Begin
            MissingCount := MissingCount + 1;
            Audit.Add(NetName + ',' + Ref + ',' + PinNumber + ',' +
                Reason + ',PIN_NOT_FOUND' + CoordinateText);
        End;
    End;
    Rows.Free;
    Audit.SaveToFile(AuditPath);
    Audit.Free;
End;

Function SheetListContains(SheetList : String; SheetNumber : Integer) : Boolean;
Var
    Token : String;
Begin
    If SheetNumber < 10 Then
        Token := '0' + IntToStr(SheetNumber)
    Else
        Token := IntToStr(SheetNumber);
    Result := Pos(';' + Token + ';', ';' + SheetList + ';') > 0;
End;

Function NetColor(NetName : String) : TColor;
Var
    U : String;
Begin
    U := UpperCase(NetName);
    If U = 'GND' Then
        Result := $00303030
    Else If U = 'TI_AGND' Then
        Result := $00008000
    Else If (Pos('24V', U) > 0) Or (Pos('12V', U) > 0) Or
            (Pos('5V', U) > 0) Or (Pos('3V3', U) > 0) Or
            (Pos('1V', U) > 0) Then
        Result := $000000C0
    Else If (Pos('UART', U) > 0) Or (Pos('CAN', U) > 0) Or
            (Pos('USB', U) > 0) Or (Pos('GNSS', U) > 0) Or
            (Pos('IMU', U) > 0) Or (Pos('SWD', U) > 0) Then
        Result := $00C00000
    Else If Pos('TI_', U) = 1 Then
        Result := $00800080
    Else
        Result := $00606060;
End;

Function ConnectivityContainsNet(Rows : TStringList;
    NetName : String) : Boolean;
Var
    I : Integer;
Begin
    Result := False;
    For I := 1 To Rows.Count - 1 Do
        If SameText(Trim(CsvField(Rows[I], 0)), Trim(NetName)) Then
        Begin
            Result := True;
            Exit;
        End;
End;

Procedure RouteLocalExplicitNets(SourceDoc, TargetDoc : ISch_Document;
    OffsetX, OffsetY : TCoord; GroupMinX, GroupMinY, GroupMaxX,
    GroupMaxY : Double; SheetNumber : Integer; Connectivity,
    Audit : TStringList; Var RoutedNetCount, RoutedAnchorCount : Integer);
Var
    Iterator       : ISch_Iterator;
    Obj            : ISch_BasicContainer;
    LabelObj       : ISch_NetLabel;
    Names          : TStringList;
    NetName        : String;
    AnchorXs       : Array[0..255] Of Double;
    AnchorYs       : Array[0..255] Of Double;
    AnchorX        : TCoord;
    AnchorY        : TCoord;
    AnchorIndex    : Integer;
    AnchorCount    : Integer;
    LocalNetIndex  : Integer;
    I              : Integer;
    LeftCount      : Integer;
    RightCount     : Integer;
    CellCenter     : Double;
    LaneOffset     : Double;
    LeftLaneX      : Double;
    RightLaneX     : Double;
    RailY          : Double;
    EscapeX        : Double;
    MinEscapeX     : Double;
    MaxEscapeX     : Double;
    MinAnchorY     : Double;
    MaxAnchorY     : Double;
    C              : TColor;
    ModeText       : String;
Begin
    Names := TStringList.Create;
    Names.Sorted := True;
    Names.Duplicates := dupIgnore;
    Iterator := SourceDoc.SchIterator_Create;
    If Iterator = Nil Then
    Begin
        Names.Free;
        Exit;
    End;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eNetLabel));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            LabelObj := Obj;
            NetName := NormalizeNetName(Trim(LabelObj.Text));
            If NetName <> '' Then Names.Add(NetName);
            Obj := Iterator.NextSchObject;
        End;
    Finally
        SourceDoc.SchIterator_Destroy(Iterator);
    End;

    CellCenter := (GroupMinX + GroupMaxX) / 2.0;
    LocalNetIndex := 0;
    For I := 0 To Names.Count - 1 Do
    Begin
        NetName := Names[I];
        If ConnectivityContainsNet(Connectivity, NetName) Then Continue;

        AnchorCount := 0;
        AnchorIndex := 0;
        While (AnchorCount < 256) And
              FindNetAnchorAt(SourceDoc, NetName, AnchorIndex,
                  AnchorX, AnchorY) Do
        Begin
            AnchorXs[AnchorCount] := UnMm(AnchorX + OffsetX);
            AnchorYs[AnchorCount] := UnMm(AnchorY + OffsetY);
            AnchorCount := AnchorCount + 1;
            AnchorIndex := AnchorIndex + 1;
        End;
        If AnchorCount < 2 Then Continue;

        LocalNetIndex := LocalNetIndex + 1;
        LaneOffset := 18.0 + LocalNetIndex * 2.2;
        LeftLaneX := UnMm(SnapCoordToMils(
            Mm(GroupMinX - LaneOffset), 10));
        RightLaneX := UnMm(SnapCoordToMils(
            Mm(GroupMaxX + LaneOffset), 10));
        RailY := UnMm(SnapCoordToMils(
            Mm(GroupMaxY + LaneOffset), 10));
        LeftCount := 0;
        RightCount := 0;
        MinAnchorY := AnchorYs[0];
        MaxAnchorY := AnchorYs[0];
        For AnchorIndex := 0 To AnchorCount - 1 Do
        Begin
            If AnchorXs[AnchorIndex] <= CellCenter Then
                LeftCount := LeftCount + 1
            Else
                RightCount := RightCount + 1;
            If AnchorYs[AnchorIndex] < MinAnchorY Then
                MinAnchorY := AnchorYs[AnchorIndex];
            If AnchorYs[AnchorIndex] > MaxAnchorY Then
                MaxAnchorY := AnchorYs[AnchorIndex];
        End;
        C := NetColor(NetName);

        { The replicated net labels provide the electrical connection. These
          overview routes must remain graphical primitives: Altium joins wire
          primitives at every crossing and would otherwise short unrelated
          nets on a dense single-sheet drawing. }

        If RightCount = 0 Then
        Begin
            ModeText := 'LEFT_LANE';
            For AnchorIndex := 0 To AnchorCount - 1 Do
                AddLine(TargetDoc, AnchorXs[AnchorIndex],
                    AnchorYs[AnchorIndex], LeftLaneX,
                    AnchorYs[AnchorIndex], C, eSmall);
            AddLine(TargetDoc, LeftLaneX, MinAnchorY,
                LeftLaneX, MaxAnchorY, C, eSmall);
        End
        Else If LeftCount = 0 Then
        Begin
            ModeText := 'RIGHT_LANE';
            For AnchorIndex := 0 To AnchorCount - 1 Do
                AddLine(TargetDoc, AnchorXs[AnchorIndex],
                    AnchorYs[AnchorIndex], RightLaneX,
                    AnchorYs[AnchorIndex], C, eSmall);
            AddLine(TargetDoc, RightLaneX, MinAnchorY,
                RightLaneX, MaxAnchorY, C, eSmall);
        End
        Else
        Begin
            ModeText := 'SPLIT_TOP_RAIL';
            MinEscapeX := RightLaneX;
            MaxEscapeX := LeftLaneX;
            For AnchorIndex := 0 To AnchorCount - 1 Do
            Begin
                If AnchorXs[AnchorIndex] <= CellCenter Then
                    EscapeX := LeftLaneX
                Else
                    EscapeX := RightLaneX;
                AddLine(TargetDoc, AnchorXs[AnchorIndex],
                    AnchorYs[AnchorIndex], EscapeX,
                    AnchorYs[AnchorIndex], C, eSmall);
                AddLine(TargetDoc, EscapeX, AnchorYs[AnchorIndex],
                    EscapeX, RailY, C, eSmall);
                If EscapeX < MinEscapeX Then MinEscapeX := EscapeX;
                If EscapeX > MaxEscapeX Then MaxEscapeX := EscapeX;
            End;
            AddLine(TargetDoc, MinEscapeX, RailY,
                MaxEscapeX, RailY, C, eSmall);
        End;

        RoutedNetCount := RoutedNetCount + 1;
        RoutedAnchorCount := RoutedAnchorCount + AnchorCount;
        Audit.Add(IntToStr(SheetNumber) + ',' + NetName + ',' +
            IntToStr(AnchorCount) + ',' + ModeText + ',PASS');
    End;
    Names.Free;
End;

Procedure AddConnectivityMatrix(Doc : ISch_Document; Rows : TStringList);
Var
    I, S           : Integer;
    NetName        : String;
    SheetList      : String;
    Y              : Double;
    RowHeight      : Double;
    SheetX         : Double;
    C              : TColor;
Begin
    AddRectangle(Doc, 20.0, 20.0, 3580.0, 625.0,
        $00404040, $00FFFFFF, False, eMedium);
    AddLabel(Doc, 'INTER-SHEET ELECTRICAL CONNECTIONS / EXACT NET NAMES',
        35.0, 601.0, 13, True, $00202020);
    AddLabel(Doc,
        'Each row is an actual Altium wire with a net label. Identical labels electrically join the row to all matching endpoints in the 31 flattened sheets.',
        35.0, 584.0, 8, False, $00404040);
    AddLabel(Doc,
        'Full component-pad-to-net binding for PCB rerouting: R9_pad_binding.csv in the release verification folder.',
        35.0, 571.0, 8, False, $00404040);

    AddLabel(Doc, 'NET', 35.0, 552.0, 7, True, $00202020);
    For S := 1 To 31 Do
    Begin
        SheetX := 650.0 + (S - 1) * 94.0;
        If S < 10 Then
            AddLabel(Doc, '0' + IntToStr(S), SheetX - 2.0, 552.0,
                5, True, $00303030)
        Else
            AddLabel(Doc, IntToStr(S), SheetX - 2.0, 552.0,
                5, True, $00303030);
        AddLine(Doc, SheetX, 45.0, SheetX, 546.0,
            $00E0E0E0, eZeroSize);
    End;

    If Rows.Count <= 1 Then Exit;
    RowHeight := 500.0 / (Rows.Count - 1);
    If RowHeight > 6.0 Then RowHeight := 6.0;
    For I := 1 To Rows.Count - 1 Do
    Begin
        NetName := CsvField(Rows[I], 0);
        SheetList := CsvField(Rows[I], 1);
        If (NetName = '') Or (SheetList = '') Then Continue;
        Y := 542.0 - (I - 1) * RowHeight;
        C := NetColor(NetName);
        AddWire(Doc, 350.0, Y, 3550.0, Y, C, eSmall);
        AddNetLabel(Doc, NetName, 350.0, Y, 4, C);
        AddLabel(Doc, NetName, 35.0, Y - 1.0, 4, False, C);
        For S := 1 To 31 Do
            If SheetListContains(SheetList, S) Then
            Begin
                SheetX := 650.0 + (S - 1) * 94.0;
                AddRectangle(Doc, SheetX - 1.3, Y - 1.3,
                    SheetX + 1.3, Y + 1.3, C, C, True, eZeroSize);
            End;
    End;

    AddLabel(Doc, 'Power', 35.0, 31.0, 6, True, $000000C0);
    AddLabel(Doc, 'Interfaces', 100.0, 31.0, 6, True, $00C00000);
    AddLabel(Doc, 'AWR2944P', 190.0, 31.0, 6, True, $00800080);
    AddLabel(Doc, 'GND and other nets', 285.0, 31.0, 6, True, $00303030);
End;

Procedure AddSheetConnectionPorts(Doc : ISch_Document; Rows : TStringList;
    SheetNumber : Integer; X0, Y0, X1, Y1 : Double);
Var
    I              : Integer;
    NetName        : String;
    SheetList      : String;
    Y              : Double;
    C              : TColor;
Begin
    AddLine(Doc, X0 + 310.0, Y0 + 5.0, X0 + 310.0, Y1 - 5.0,
        $00B0B0B0, eZeroSize);
    AddLabel(Doc, 'INTER-SHEET ELECTRICAL PORTS', X0 + 315.0,
        Y1 - 11.0, 6, True, $00303030);
    Y := Y1 - 19.0;
    For I := 1 To Rows.Count - 1 Do
    Begin
        NetName := CsvField(Rows[I], 0);
        SheetList := CsvField(Rows[I], 1);
        If (NetName = '') Or (SheetList = '') Then Continue;
        If Not SheetListContains(SheetList, SheetNumber) Then Continue;
        C := NetColor(NetName);
        AddWire(Doc, X0 + 315.0, Y, X1 - 5.0, Y, C, eSmall);
        AddNetLabel(Doc, NetName, X0 + 316.0, Y, 5, C);
        Y := Y - 2.7;
    End;
    AddLabel(Doc,
        'Identical net names are electrically common; no decorative links.',
        X0 + 315.0, Y0 + 4.0, 4, False, $00606060);
End;

Procedure PrepareFullElementSheet;
Var
    Project        : IProject;
    LogicalDoc     : IDocument;
    TargetServer   : IServerDocument;
    TargetDoc      : ISch_Document;
    SourceDoc      : ISch_Document;
    SourceDocs     : Array[1..31] Of ISch_Document;
    OffsetXs       : Array[1..31] Of TCoord;
    OffsetYs       : Array[1..31] Of TCoord;
    GroupMinXs     : Array[1..31] Of Double;
    GroupMaxXs     : Array[1..31] Of Double;
    GroupMinYs     : Array[1..31] Of Double;
    GroupMaxYs     : Array[1..31] Of Double;
    RowBottomYs    : Array[0..6] Of Double;
    RowTopYs       : Array[0..6] Of Double;
    RowSlots       : Array[1..500, 0..3] Of Integer;
    RowNetCounts   : Array[0..3] Of Integer;
    RowPresent     : Array[0..3] Of Boolean;
    RowAnchorCount : Array[0..3] Of Integer;
    RowRailYs      : Array[0..3] Of Double;
    RowMinRailXs   : Array[0..3] Of Double;
    RowMaxRailXs   : Array[0..3] Of Double;
    NetCrossRows   : Array[1..500] Of Boolean;
    NetTrunkXs     : Array[1..500] Of Double;
    SourcePaths    : TStringList;
    Verification   : TStringList;
    LayoutAudit    : TStringList;
    LocalAudit     : TStringList;
    BasePath       : String;
    TargetPath     : String;
    SourcePath     : String;
    SourceName     : String;
    VerificationPath : String;
    LayoutAuditPath : String;
    LocalAuditPath : String;
    I              : Integer;
    NetIndex       : Integer;
    SheetNo        : Integer;
    RowIndex       : Integer;
    ColIndex       : Integer;
    X0, Y0         : Double;
    MinX, MinY     : TCoord;
    MaxX, MaxY     : TCoord;
    OffsetX        : TCoord;
    OffsetY        : TCoord;
    AnchorX        : TCoord;
    AnchorY        : TCoord;
    AnchorXmm      : Double;
    AnchorYmm      : Double;
    EscapeX        : Double;
    RowRailY       : Double;
    TopRailY       : Double;
    LowerRailY     : Double;
    TrunkX         : Double;
    TrunkMinY      : Double;
    TrunkMaxY      : Double;
    MinRailX       : Double;
    MaxRailX       : Double;
    CellCenter     : Double;
    CorridorBottom : Double;
    CorridorTop    : Double;
    NetName        : String;
    SheetList      : String;
    ExpectedCount  : Integer;
    FoundCount     : Integer;
    NetAnchorCount : Integer;
    AnchorIndex    : Integer;
    MissingAnchors : Integer;
    RowHasAnchor   : Boolean;
    HasTopAnchor   : Boolean;
    HasLowerAnchor : Boolean;
    C              : TColor;
    PrimitiveCount : Integer;
    Connectivity   : TStringList;
    ConnectivityPath : String;
    CrossNetCount  : Integer;
    NcApplied      : Integer;
    NcExisting     : Integer;
    NcMissing      : Integer;
    NoDriverApplied : Integer;
    NoDriverExisting : Integer;
    NoDriverMissing : Integer;
    PinTypeCorrected : Integer;
    CrossCounter   : Integer;
    RowPresentCount : Integer;
    TrunkGapIndex  : Integer;
    TrunkSlotIndex : Integer;
    DirectDrop     : Boolean;
    FoundOnSheet   : Boolean;
    LocalRoutedNets : Integer;
    LocalRoutedAnchors : Integer;
Begin
    If SchServer = Nil Then Exit;
    Project := FindR9Project;
    If Project = Nil Then
    Begin
        ShowMessage('Open RADAR_D79_24V_R9.PrjPcb before running this script.');
        Exit;
    End;

    BasePath := ExtractFilePath(Project.DM_ProjectFullPath);
    TargetPath := BasePath + '00_UNIFIED_CONNECTED_SCHEMATIC.SchDoc';
    TargetDoc := LoadSchDocument(TargetPath);
    If TargetDoc = Nil Then
    Begin
        ShowMessage('Cannot open 00_UNIFIED_CONNECTED_SCHEMATIC.SchDoc.');
        Exit;
    End;

    SourcePaths := TStringList.Create;
    SourcePaths.Sorted := True;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        LogicalDoc := Project.DM_LogicalDocuments(I);
        If (LogicalDoc <> Nil) And
           (LogicalDoc.DM_DocumentKind = 'SCH') And
           IsDetailSheet(ExtractFileName(LogicalDoc.DM_FullPath)) Then
            SourcePaths.Add(LogicalDoc.DM_FullPath);
    End;
    If SourcePaths.Count <> 31 Then
    Begin
        ShowMessage('Expected 31 detail sheets, found ' +
            IntToStr(SourcePaths.Count) + '. Master sheet was not changed.');
        SourcePaths.Free;
        Exit;
    End;

    ConnectivityPath := BasePath +
        'R9_master_inter_sheet_connectivity.csv';
    If Not FileExists(ConnectivityPath) Then
    Begin
        ShowMessage('Missing connectivity file: ' + ConnectivityPath +
            '. Master sheet was not changed.');
        SourcePaths.Free;
        Exit;
    End;
    Connectivity := TStringList.Create;
    Connectivity.LoadFromFile(ConnectivityPath);
    If Connectivity.Count <= 1 Then
    Begin
        ShowMessage('Connectivity file has no data. Master sheet was not changed.');
        Connectivity.Free;
        SourcePaths.Free;
        Exit;
    End;
    CrossNetCount := Connectivity.Count - 1;
    Verification := TStringList.Create;
    Verification.Add('Net,ExpectedSheets,SheetsFound,Status,AnchorsRouted');
    LayoutAudit := TStringList.Create;
    LayoutAudit.Add('Sheet,MinXmm,MinYmm,MaxXmm,MaxYmm,WidthMm,HeightMm');
    LocalAudit := TStringList.Create;
    LocalAudit.Add('Sheet,Net,Anchors,RouteMode,Status');
    LocalRoutedNets := 0;
    LocalRoutedAnchors := 0;
    MissingAnchors := 0;

    SchServer.ProcessControl.PreProcess(TargetDoc, '');
    Try
        ClearCurrentSheet(TargetDoc);
        TargetDoc.UseCustomSheet := True;
        TargetDoc.CustomSheetStyle := 'R9 Flat Connected Element 2400 x 2300 mm';
        TargetDoc.CustomX := Mm(2400);
        TargetDoc.CustomY := Mm(2300);
        TargetDoc.CustomMarginWidth := Mm(10);
        TargetDoc.BorderOn := True;
        TargetDoc.ReferenceZonesOn := False;
        TargetDoc.TitleBlockOn := False;
        TargetDoc.UpdateDocumentProperties;
        TargetDoc.SnapGridOn := True;
        TargetDoc.SnapGridSize := Mm(1);
        TargetDoc.VisibleGridOn := True;
        TargetDoc.VisibleGridSize := Mm(10);

        AddLabel(TargetDoc,
            'RADAR D79 24 V / FLAT CONNECTED ELEMENT SCHEMATIC / PCB v0.8.0 R9',
            10, 2275, 18, True, $00202020);
        AddLabel(TargetDoc,
            'All source elements are placed on one electrical sheet. Inter-block nets use short Manhattan paths in distributed row and column corridors.',
            10, 2261, 10, False, $00404040);
        AddLabel(TargetDoc,
            'Civil drone tracking system. Measurement and object-state output only. Production authority: NOT_AUTHORIZED.',
            10, 2249, 9, False, $00404040);
        AddLabel(TargetDoc,
            'GOST ESKD ROUTING: orthogonal conductors; every electrical junction has a filled dot; a crossing without a dot is not a connection.',
            10, 2237, 8, False, $00404040);
        AddLabel(TargetDoc,
            'TI_AGND joins GND only through RAD_NT1, RAD_NT2, RAD_NT3 and RAD_NT4 net-tie components.',
            10, 2227, 8, False, $00008000);
        AddLabel(TargetDoc,
            'DISTRIBUTED INTER-BLOCK ROUTING',
            1980, 2275, 8, True, $00303030);
        AddLabel(TargetDoc,
            'Cross-row nets are spread across seven clear inter-column corridors.',
            1980, 2265, 6, False, $00505050);
        AddLabel(TargetDoc,
            'Crossings without a junction are not electrical connections.',
            1980, 2256, 6, False, $00505050);

        PrimitiveCount := 0;
        For SheetNo := 1 To 31 Do
        Begin
            GSourceDocs[SheetNo] := Nil;
            GOffsetXs[SheetNo] := 0;
            GOffsetYs[SheetNo] := 0;
        End;
        For RowIndex := 0 To 6 Do
        Begin
            RowBottomYs[RowIndex] := 100000.0;
            RowTopYs[RowIndex] := -100000.0;
        End;
        For I := 0 To SourcePaths.Count - 1 Do
        Begin
            SourcePath := SourcePaths[I];
            SourceName := ExtractFileName(SourcePath);
            SourceDoc := LoadSchDocument(SourcePath);
            If SourceDoc = Nil Then Continue;
            If Not CollectBounds(SourceDoc, MinX, MinY, MaxX, MaxY) Then Continue;

            SheetNo := I + 1;
            ColIndex := I Mod 8;
            RowIndex := I Div 8;
            X0 := 10.0 + ColIndex * 245.0;
            If RowIndex = 0 Then
                Y0 := 1770.0
            Else If RowIndex = 1 Then
                Y0 := 1095.0
            Else If RowIndex = 2 Then
                Y0 := 590.0
            Else
                Y0 := 90.0;

            OffsetX := Mm(X0 + 20.0) - MinX;
            OffsetY := Mm(Y0 + 30.0) - MinY;
            { A whole-sheet translation must preserve the source electrical
              grid. Millimetre layout targets are rounded to the 10 mil
              schematic grid before every primitive is copied. }
            OffsetX := SnapCoordToMils(OffsetX, 10);
            OffsetY := SnapCoordToMils(OffsetY, 10);
            SourceDocs[SheetNo] := SourceDoc;
            OffsetXs[SheetNo] := OffsetX;
            OffsetYs[SheetNo] := OffsetY;
            GSourceDocs[SheetNo] := SourceDoc;
            GOffsetXs[SheetNo] := OffsetX;
            GOffsetYs[SheetNo] := OffsetY;
            GroupMinXs[SheetNo] := UnMm(MinX + OffsetX);
            GroupMaxXs[SheetNo] := UnMm(MaxX + OffsetX);
            GroupMinYs[SheetNo] := UnMm(MinY + OffsetY);
            GroupMaxYs[SheetNo] := UnMm(MaxY + OffsetY);
            AddLabel(TargetDoc,
                StringReplace(ChangeFileExt(SourceName, ''), '_', ' ',
                    rfReplaceAll),
                GroupMinXs[SheetNo], GroupMaxYs[SheetNo] + 10.0,
                7, True, $00303030);
            LayoutAudit.Add(SourceName + ',' +
                CsvFloat(GroupMinXs[SheetNo]) + ',' +
                CsvFloat(GroupMinYs[SheetNo]) + ',' +
                CsvFloat(GroupMaxXs[SheetNo]) + ',' +
                CsvFloat(GroupMaxYs[SheetNo]) + ',' +
                CsvFloat(GroupMaxXs[SheetNo] - GroupMinXs[SheetNo]) + ',' +
                CsvFloat(GroupMaxYs[SheetNo] - GroupMinYs[SheetNo]));
            If GroupMinYs[SheetNo] < RowBottomYs[RowIndex] Then
                RowBottomYs[RowIndex] := GroupMinYs[SheetNo];
            If GroupMaxYs[SheetNo] > RowTopYs[RowIndex] Then
                RowTopYs[RowIndex] := GroupMaxYs[SheetNo];
            PrimitiveCount := PrimitiveCount +
                ReplicateSheet(SourceDoc, TargetDoc, OffsetX, OffsetY,
                    (MinX + MaxX) Div 2);
        End;

        AddCompactRfAntennaTile(TargetDoc, 2180.0, 30.0);
        ApplyKnownPinDirections(TargetDoc, PinTypeCorrected);

        { Add a visible overview route for every repeated same-sheet label.
          Electrical identity remains defined by the replicated net labels;
          graphical lines avoid accidental junctions at dense crossings. }
        For SheetNo := 1 To 31 Do
            If SourceDocs[SheetNo] <> Nil Then
                RouteLocalExplicitNets(SourceDocs[SheetNo], TargetDoc,
                    OffsetXs[SheetNo], OffsetYs[SheetNo],
                    GroupMinXs[SheetNo], GroupMinYs[SheetNo],
                    GroupMaxXs[SheetNo], GroupMaxYs[SheetNo], SheetNo,
                    Connectivity, LocalAudit, LocalRoutedNets,
                    LocalRoutedAnchors);

        { Allocate only the row lanes that are actually used. Cross-row
          trunks are distributed through the seven clear gaps between the
          eight functional columns. This prevents a single central bundle. }
        For RowIndex := 0 To 3 Do
            RowNetCounts[RowIndex] := 0;
        CrossCounter := 0;
        For NetIndex := 1 To Connectivity.Count - 1 Do
        Begin
            SheetList := CsvField(Connectivity[NetIndex], 1);
            For RowIndex := 0 To 3 Do
            Begin
                RowPresent[RowIndex] := False;
                RowSlots[NetIndex, RowIndex] := 0;
            End;
            For SheetNo := 1 To 31 Do
                If SheetListContains(SheetList, SheetNo) Then
                Begin
                    RowIndex := (SheetNo - 1) Div 8;
                    RowPresent[RowIndex] := True;
                End;
            RowPresentCount := 0;
            For RowIndex := 0 To 3 Do
                If RowPresent[RowIndex] Then
                Begin
                    RowNetCounts[RowIndex] := RowNetCounts[RowIndex] + 1;
                    RowSlots[NetIndex, RowIndex] := RowNetCounts[RowIndex];
                    RowPresentCount := RowPresentCount + 1;
                End;
            NetCrossRows[NetIndex] := RowPresentCount > 1;
            If NetCrossRows[NetIndex] Then
            Begin
                CrossCounter := CrossCounter + 1;
                TrunkGapIndex := (CrossCounter - 1) Mod 7;
                TrunkSlotIndex := (CrossCounter - 1) Div 7;
                NetTrunkXs[NetIndex] := 247.0 +
                    TrunkGapIndex * 245.0 + TrunkSlotIndex * 2.6;
            End
            Else
                NetTrunkXs[NetIndex] := -1.0;
        End;

        For NetIndex := 1 To Connectivity.Count - 1 Do
        Begin
            NetName := CsvField(Connectivity[NetIndex], 0);
            SheetList := CsvField(Connectivity[NetIndex], 1);
            If (NetName = '') Or (SheetList = '') Then Continue;
            C := NetColor(NetName);

            ExpectedCount := 0;
            FoundCount := 0;
            NetAnchorCount := 0;
            HasTopAnchor := False;
            HasLowerAnchor := False;
            TrunkMinY := 100000.0;
            TrunkMaxY := -100000.0;
            For RowIndex := 0 To 3 Do
            Begin
                RowAnchorCount[RowIndex] := 0;
                RowRailYs[RowIndex] := 0.0;
                RowMinRailXs[RowIndex] := 100000.0;
                RowMaxRailXs[RowIndex] := -100000.0;
            End;
            TrunkX := NetTrunkXs[NetIndex];

            For SheetNo := 1 To 31 Do
                If SheetListContains(SheetList, SheetNo) Then
                    ExpectedCount := ExpectedCount + 1;

            For SheetNo := 1 To 31 Do
            Begin
                If Not SheetListContains(SheetList, SheetNo) Then Continue;
                If SourceDocs[SheetNo] = Nil Then Continue;
                AnchorIndex := 0;
                FoundOnSheet := False;
                While FindNetAnchorAt(SourceDocs[SheetNo], NetName,
                    AnchorIndex, AnchorX, AnchorY) Do
                Begin
                    AnchorXmm := UnMm(AnchorX + OffsetXs[SheetNo]);
                    AnchorYmm := UnMm(AnchorY + OffsetYs[SheetNo]);
                    CellCenter := (GroupMinXs[SheetNo] +
                        GroupMaxXs[SheetNo]) / 2.0;
                    { A label already placed at the lower boundary has a clear
                      route to the row corridor. Keep that connection straight.
                      Interior and side labels retain an outside escape so their
                      conductors do not pass through symbols or annotations. }
                    DirectDrop := AnchorYmm <= GroupMinYs[SheetNo] + 5.0;
                    If DirectDrop Then
                        EscapeX := AnchorXmm
                    Else If AnchorXmm <= CellCenter Then
                        EscapeX := GroupMinXs[SheetNo] -
                            (3.0 + ((NetIndex - 1) Mod 10) * 1.2 +
                            AnchorIndex * 0.8)
                    Else
                        EscapeX := GroupMaxXs[SheetNo] +
                            (3.0 + ((NetIndex - 1) Mod 10) * 1.2 +
                            AnchorIndex * 0.8);
                    EscapeX := UnMm(SnapCoordToMils(Mm(EscapeX), 10));

                    RowIndex := (SheetNo - 1) Div 8;
                    If RowIndex = 0 Then
                    Begin
                        CorridorBottom := 1698.0;
                        CorridorTop := 1797.0;
                    End
                    Else If RowIndex = 1 Then
                    Begin
                        CorridorBottom := 1020.0;
                        CorridorTop := 1121.0;
                    End
                    Else If RowIndex = 2 Then
                    Begin
                        CorridorBottom := 515.0;
                        CorridorTop := 618.0;
                    End
                    Else
                    Begin
                        CorridorBottom := 12.0;
                        CorridorTop := 117.0;
                    End;
                    RowRailY := CorridorBottom +
                        RowSlots[NetIndex, RowIndex] *
                        (CorridorTop - CorridorBottom) /
                        (RowNetCounts[RowIndex] + 1);
                    RowRailYs[RowIndex] := RowRailY;
                    If RowRailY < TrunkMinY Then TrunkMinY := RowRailY;
                    If RowRailY > TrunkMaxY Then TrunkMaxY := RowRailY;

                    If (UpperCase(NetName) = 'GND') Or
                       (UpperCase(NetName) = 'TI_AGND') Then
                    Begin
                        If Not DirectDrop Then
                            AddLine(TargetDoc, AnchorXmm, AnchorYmm,
                                EscapeX, AnchorYmm, C, eMedium);
                        AddLine(TargetDoc, EscapeX, AnchorYmm,
                            EscapeX, RowRailY, C, eMedium);
                    End
                    Else
                    Begin
                        If Not DirectDrop Then
                            AddLine(TargetDoc, AnchorXmm, AnchorYmm,
                                EscapeX, AnchorYmm, C, eSmall);
                        AddLine(TargetDoc, EscapeX, AnchorYmm,
                            EscapeX, RowRailY, C, eSmall);
                    End;
                    AddRectangle(TargetDoc,
                        EscapeX - 0.45, RowRailY - 0.45,
                        EscapeX + 0.45, RowRailY + 0.45,
                        C, C, True, eZeroSize);
                    RowAnchorCount[RowIndex] :=
                        RowAnchorCount[RowIndex] + 1;
                    If EscapeX < RowMinRailXs[RowIndex] Then
                        RowMinRailXs[RowIndex] := EscapeX;
                    If EscapeX > RowMaxRailXs[RowIndex] Then
                        RowMaxRailXs[RowIndex] := EscapeX;
                    FoundOnSheet := True;
                    NetAnchorCount := NetAnchorCount + 1;
                    AnchorIndex := AnchorIndex + 1;
                End;
                If FoundOnSheet Then
                    FoundCount := FoundCount + 1;
            End;

            { Draw only the span required by the participating blocks. A net
              that stays in one row never reaches a vertical trunk. }
            For RowIndex := 0 To 3 Do
                If RowAnchorCount[RowIndex] > 0 Then
                Begin
                    If NetCrossRows[NetIndex] Then
                    Begin
                        If TrunkX < RowMinRailXs[RowIndex] Then
                            RowMinRailXs[RowIndex] := TrunkX;
                        If TrunkX > RowMaxRailXs[RowIndex] Then
                            RowMaxRailXs[RowIndex] := TrunkX;
                    End;
                    If RowMaxRailXs[RowIndex] > RowMinRailXs[RowIndex] Then
                    Begin
                        If (UpperCase(NetName) = 'GND') Or
                           (UpperCase(NetName) = 'TI_AGND') Then
                            AddLine(TargetDoc,
                                RowMinRailXs[RowIndex],
                                RowRailYs[RowIndex],
                                RowMaxRailXs[RowIndex],
                                RowRailYs[RowIndex], C, eMedium)
                        Else
                            AddLine(TargetDoc,
                                RowMinRailXs[RowIndex],
                                RowRailYs[RowIndex],
                                RowMaxRailXs[RowIndex],
                                RowRailYs[RowIndex], C, eSmall);
                    End;
                    { The filled dot marks the intended visual rail-to-trunk
                      continuation. Electrical identity is defined by the net
                      labels at every source anchor; unrelated graphical route
                      crossings remain unconnected. }
                    If NetCrossRows[NetIndex] Then
                        AddRectangle(TargetDoc,
                            TrunkX - 0.55, RowRailYs[RowIndex] - 0.55,
                            TrunkX + 0.55, RowRailYs[RowIndex] + 0.55,
                            C, C, True, eZeroSize);
                End;

            If NetCrossRows[NetIndex] And (FoundCount > 1) And
               (TrunkMaxY > TrunkMinY) Then
            Begin
                If (UpperCase(NetName) = 'GND') Or
                   (UpperCase(NetName) = 'TI_AGND') Then
                    AddLine(TargetDoc, TrunkX, TrunkMinY,
                        TrunkX, TrunkMaxY, C, eMedium)
                Else
                    AddLine(TargetDoc, TrunkX, TrunkMinY,
                        TrunkX, TrunkMaxY, C, eSmall);
                AddRectangle(TargetDoc,
                    TrunkX - 0.55, TrunkMaxY - 0.55,
                    TrunkX + 0.55, TrunkMaxY + 0.55,
                    C, C, True, eZeroSize);
                AddRectangle(TargetDoc,
                    TrunkX - 0.55, TrunkMinY - 0.55,
                    TrunkX + 0.55, TrunkMinY + 0.55,
                    C, C, True, eZeroSize);
                AddVerticalLabel(TargetDoc, NetName, TrunkX + 0.9,
                    TrunkMaxY + 2.0, 4, False, C);
            End;

            If FoundCount = ExpectedCount Then
                Verification.Add(NetName + ',' + IntToStr(ExpectedCount) +
                    ',' + IntToStr(FoundCount) + ',PASS,' +
                    IntToStr(NetAnchorCount))
            Else
            Begin
                Verification.Add(NetName + ',' + IntToStr(ExpectedCount) +
                    ',' + IntToStr(FoundCount) + ',FAIL,' +
                    IntToStr(NetAnchorCount));
                MissingAnchors := MissingAnchors +
                    (ExpectedCount - FoundCount);
            End;
        End;

        ApplySinglePinDispositions(TargetDoc, BasePath,
            NcApplied, NcExisting, NcMissing);
        ApplyNoDriverDispositions(TargetDoc, BasePath,
            NoDriverApplied, NoDriverExisting, NoDriverMissing);
    Finally
        SchServer.ProcessControl.PostProcess(TargetDoc, '');
    End;

    VerificationPath := BasePath +
        'R9_unified_flat_connectivity_verification.csv';
    Verification.SaveToFile(VerificationPath);
    LayoutAuditPath := BasePath + 'R9_unified_flat_layout_bounds.csv';
    LayoutAudit.SaveToFile(LayoutAuditPath);
    LocalAuditPath := BasePath +
        'R9_local_explicit_connectivity_verification.csv';
    LocalAudit.SaveToFile(LocalAuditPath);
    LocalAudit.Free;
    LayoutAudit.Free;
    Verification.Free;
    Connectivity.Free;
    SourcePaths.Free;

    TargetDoc.GraphicallyInvalidate;
    TargetServer := Client.GetDocumentByPath(TargetPath);
    If TargetServer <> Nil Then
    Begin
        TargetServer.Modified := True;
        TargetServer.DoFileSave('Advanced Schematic binary');
        Client.ShowDocument(TargetServer);
    End;
    If (MissingAnchors = 0) And (NcMissing = 0) And
       (NoDriverMissing = 0) Then
        ShowMessage('Flat connected schematic saved. Replicated primitives: ' +
            IntToStr(PrimitiveCount) + '. Cross-source nets: ' +
            IntToStr(CrossNetCount) + '. Missing anchors: 0. ' +
            'Audited NC directives: ' + IntToStr(NcApplied + NcExisting) +
            '. Audited passive-input directives: ' +
            IntToStr(NoDriverApplied + NoDriverExisting) +
            '. Corrected pin directions: ' + IntToStr(PinTypeCorrected) +
            '. Explicit local nets: ' + IntToStr(LocalRoutedNets) +
            ' using ' + IntToStr(LocalRoutedAnchors) + ' anchors.')
    Else
        ShowMessage('Flat schematic generated but NOT accepted. Missing net anchors: ' +
            IntToStr(MissingAnchors) + '. Missing NC pins: ' +
            IntToStr(NcMissing) + '. Missing passive-input anchors: ' +
            IntToStr(NoDriverMissing) + '. See verification CSV.');
End;
