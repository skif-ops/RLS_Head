Function PlacementIndex(Ref : String) : Integer;
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
    If Ref = 'SW1' Then Result := 22;
    If Ref = 'TP1' Then Result := 23;
    If Ref = 'TP2' Then Result := 24;
    If Ref = 'R70' Then Result := 25;
    If Ref = 'R61' Then Result := 26;
    If Ref = 'R62' Then Result := 27;
    If Ref = 'R63' Then Result := 28;
    If Ref = 'C6D' Then Result := 29;
    If Ref = 'R1' Then Result := 30;
    If Ref = 'R6F' Then Result := 31;
    If Ref = 'C1' Then Result := 32;
    If Ref = 'C4' Then Result := 33;
    If Ref = 'C3' Then Result := 34;
    If Ref = 'R5P' Then Result := 35;
    If Ref = 'C2' Then Result := 36;
    If Ref = 'R71' Then Result := 37;
    If Ref = 'R72' Then Result := 38;
    If Ref = 'R73' Then Result := 39;
    If Ref = 'C7D' Then Result := 40;
    If Ref = 'R2' Then Result := 41;
    If Ref = 'R7F' Then Result := 42;
    If Ref = 'C100' Then Result := 43;
    If Ref = 'C101' Then Result := 44;
    If Ref = 'C102' Then Result := 45;
    If Ref = 'C103' Then Result := 46;
    If Ref = 'C104' Then Result := 47;
    If Ref = 'C105' Then Result := 48;
    If Ref = 'C106' Then Result := 49;
    If Ref = 'C107' Then Result := 50;
    If Ref = 'C108' Then Result := 51;
    If Ref = 'C109' Then Result := 52;
    If Ref = 'C110' Then Result := 53;
    If Ref = 'C111' Then Result := 54;
    If Ref = 'C112' Then Result := 55;
    If Ref = 'C113' Then Result := 56;
    If Ref = 'C114' Then Result := 57;
    If Ref = 'C115' Then Result := 58;
    If Ref = 'C10' Then Result := 59;
    If Ref = 'C11' Then Result := 60;
    If Ref = 'C12' Then Result := 61;
    If Ref = 'C13' Then Result := 62;
    If Ref = 'C14' Then Result := 63;
    If Ref = 'C15' Then Result := 64;
    If Ref = 'R10' Then Result := 65;
    If Ref = 'C20' Then Result := 66;
    If Ref = 'C21' Then Result := 67;
    If Ref = 'C22' Then Result := 68;
    If Ref = 'L80' Then Result := 69;
    If Ref = 'C82' Then Result := 70;
    If Ref = 'R80' Then Result := 71;
    If Ref = 'R81' Then Result := 72;
    If Ref = 'C80' Then Result := 73;
    If Ref = 'C81' Then Result := 74;
    If Ref = 'R82' Then Result := 75;
    If Ref = 'C64' Then Result := 76;
    If Ref = 'C65' Then Result := 77;
    If Ref = 'R600' Then Result := 78;
    If Ref = 'R601' Then Result := 79;
    If Ref = 'R602' Then Result := 80;
    If Ref = 'R603' Then Result := 81;
    If Ref = 'R604' Then Result := 82;
    If Ref = 'R605' Then Result := 83;
    If Ref = 'C60' Then Result := 84;
    If Ref = 'C61' Then Result := 85;
    If Ref = 'C62' Then Result := 86;
    If Ref = 'C63' Then Result := 87;
    If Ref = 'C40' Then Result := 88;
    If Ref = 'R40' Then Result := 89;
    If Ref = 'R41' Then Result := 90;
    If Ref = 'R42' Then Result := 91;
End;

Function PlacementX(Index : Integer) : String;
Begin
    Result := '';
    Case Index Of
        0: Result := '5mm'; 1: Result := '13mm'; 2: Result := '22mm';
        3: Result := '34mm'; 4: Result := '42mm'; 5: Result := '62mm';
        6: Result := '95mm'; 7: Result := '95mm'; 8: Result := '87mm';
        9: Result := '80mm'; 10: Result := '52mm'; 11: Result := '36mm';
        12: Result := '69mm'; 13: Result := '52mm'; 14: Result := '24mm';
        15: Result := '5mm'; 16: Result := '11mm'; 17: Result := '72mm';
        18: Result := '67mm'; 19: Result := '84mm'; 20: Result := '94.75mm';
        21: Result := '50mm'; 22: Result := '70mm'; 23: Result := '57mm';
        24: Result := '60mm'; 25: Result := '64mm'; 26: Result := '20mm';
        27: Result := '22mm'; 28: Result := '24mm'; 29: Result := '22mm';
        30: Result := '19mm'; 31: Result := '25mm'; 32: Result := '30mm';
        33: Result := '30.5mm'; 34: Result := '34mm'; 35: Result := '37mm';
        36: Result := '38.5mm'; 37: Result := '60mm'; 38: Result := '62mm';
        39: Result := '64mm'; 40: Result := '62mm'; 41: Result := '59mm';
        42: Result := '65mm'; 43: Result := '37.5mm'; 44: Result := '37.5mm';
        45: Result := '37.5mm'; 46: Result := '43mm'; 47: Result := '49mm';
        48: Result := '55mm'; 49: Result := '61mm'; 50: Result := '66.5mm';
        51: Result := '66.5mm'; 52: Result := '66.5mm'; 53: Result := '68mm';
        54: Result := '61mm'; 55: Result := '55mm'; 56: Result := '49mm';
        57: Result := '67.5mm'; 58: Result := '37.5mm'; 59: Result := '58.5mm';
        60: Result := '67.5mm'; 61: Result := '52mm'; 62: Result := '67.5mm';
        63: Result := '68.5mm'; 64: Result := '43mm'; 65: Result := '46mm';
        66: Result := '49mm'; 67: Result := '52mm'; 68: Result := '55mm';
        69: Result := '14.5mm'; 70: Result := '16mm'; 71: Result := '15mm';
        72: Result := '12mm'; 73: Result := '31mm'; 74: Result := '32mm';
        75: Result := '32mm'; 76: Result := '70mm'; 77: Result := '69mm';
        78: Result := '72mm'; 79: Result := '76mm'; 80: Result := '76mm';
        81: Result := '76mm'; 82: Result := '76mm'; 83: Result := '69.5mm';
        84: Result := '68.5mm'; 85: Result := '67.5mm'; 86: Result := '73.5mm';
        87: Result := '80mm'; 88: Result := '80mm'; 89: Result := '87mm';
        90: Result := '78mm'; 91: Result := '81mm';
    End;
End;

Function PlacementY(Index : Integer) : String;
Begin
    Result := '';
    Case Index Of
        0..6: Result := '14mm'; 7..9: Result := '30mm';
        10..12: Result := '40mm'; 13: Result := '58mm'; 14: Result := '62mm';
        15..16: Result := '66mm'; 17: Result := '58mm'; 18: Result := '50mm';
        19..20: Result := '60mm'; 21: Result := '5mm'; 22: Result := '8mm';
        23..25: Result := '5.5mm';
        26..28: Result := '10.5mm'; 29..31: Result := '17.5mm';
        32: Result := '10.5mm'; 33..35: Result := '17.5mm';
        36..39: Result := '10.5mm'; 40..42: Result := '17.5mm';
        43: Result := '45mm'; 44: Result := '42mm'; 45: Result := '35mm';
        46..49: Result := '25.5mm'; 50: Result := '31mm'; 51: Result := '35mm';
        52: Result := '43mm'; 53: Result := '48mm'; 54..56: Result := '54.5mm';
        57: Result := '41mm'; 58: Result := '37.5mm'; 59: Result := '24.5mm';
        60: Result := '46mm'; 61: Result := '24.5mm'; 62: Result := '38.5mm';
        63: Result := '35.5mm'; 64: Result := '54.5mm'; 65: Result := '55.5mm';
        66: Result := '61.5mm'; 67: Result := '62mm'; 68: Result := '61.5mm';
        69: Result := '63.5mm'; 70: Result := '61.5mm'; 71: Result := '59.5mm';
        72: Result := '57mm'; 73: Result := '66mm'; 74: Result := '63mm';
        75: Result := '60mm'; 76: Result := '55mm'; 77: Result := '61mm';
        78: Result := '54mm'; 79: Result := '56mm'; 80: Result := '58mm';
        81: Result := '60mm'; 82: Result := '62mm'; 83: Result := '52.5mm';
        84: Result := '57mm'; 85: Result := '59mm'; 86: Result := '63mm';
        87: Result := '57mm'; 88..89: Result := '26.5mm'; 90..91: Result := '34mm';
    End;
End;

Function PlacementRotation(PlanIdx : Integer) : Double;
Begin
    If (PlanIdx = 3) Or (PlanIdx = 6) Or (PlanIdx = 7) Or
       (PlanIdx = 20) Then
    Begin
        Result := 180;
        Exit;
    End;
    Case PlanIdx Of
        1, 12, 18, 21..22, 25, 27..29, 31..32, 35..36, 38..40,
        42..59, 62..66, 68..70, 73, 75..89, 91: Result := 90;
    Else
        Result := 0;
    End;
End;

Function PlacementAngle(Value : Double) : Double;
Begin
    Result := Value;
    While Result >= 360 Do Result := Result - 360;
    While Result < 0 Do Result := Result + 360;
End;

Function PlacementTransformCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function FindPlacementComponent(Board : IPCB_Board; Ref : String) : IPCB_Component;
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        If UpperCase(Component.SourceDesignator) = UpperCase(Ref) Then
        Begin
            Result := Component;
            Break;
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure RotatePlacementPrimitive180(Primitive : IPCB_Primitive;
                                      OldX, OldY, NewX, NewY : TCoord);
Var
    Track                         : IPCB_Track;
    Pad                           : IPCB_Pad;
    ViaObj                        : IPCB_Via;
    ArcObj                        : IPCB_Arc;
    TextObj                       : IPCB_Text;
    FillObj                       : IPCB_Fill;
    R                             : TCoordRect;
    CenterX, CenterY              : TCoord;
    TargetX, TargetY              : TCoord;
    X1, Y1, X2, Y2                : TCoord;
Begin
    Primitive.BeginModify;
    Case Primitive.ObjectId Of
        eTrackObject:
        Begin
            Track := Primitive;
            Track.X1 := OldX + NewX - Track.X1;
            Track.Y1 := OldY + NewY - Track.Y1;
            Track.X2 := OldX + NewX - Track.X2;
            Track.Y2 := OldY + NewY - Track.Y2;
        End;
        ePadObject:
        Begin
            Pad := Primitive;
            Pad.X := OldX + NewX - Pad.X;
            Pad.Y := OldY + NewY - Pad.Y;
            Pad.Rotation := PlacementAngle(Pad.Rotation + 180);
        End;
        eViaObject:
        Begin
            ViaObj := Primitive;
            ViaObj.X := OldX + NewX - ViaObj.X;
            ViaObj.Y := OldY + NewY - ViaObj.Y;
        End;
        eArcObject:
        Begin
            ArcObj := Primitive;
            ArcObj.XCenter := OldX + NewX - ArcObj.XCenter;
            ArcObj.YCenter := OldY + NewY - ArcObj.YCenter;
            ArcObj.StartAngle := PlacementAngle(ArcObj.StartAngle + 180);
            ArcObj.EndAngle := PlacementAngle(ArcObj.EndAngle + 180);
        End;
        eTextObject:
        Begin
            TextObj := Primitive;
            TextObj.XLocation := OldX + NewX - TextObj.XLocation;
            TextObj.YLocation := OldY + NewY - TextObj.YLocation;
            TextObj.Rotation := PlacementAngle(TextObj.Rotation + 180);
        End;
        eFillObject:
        Begin
            FillObj := Primitive;
            X1 := FillObj.X1Location;
            Y1 := FillObj.Y1Location;
            X2 := FillObj.X2Location;
            Y2 := FillObj.Y2Location;
            FillObj.X1Location := OldX + NewX - X2;
            FillObj.Y1Location := OldY + NewY - Y2;
            FillObj.X2Location := OldX + NewX - X1;
            FillObj.Y2Location := OldY + NewY - Y1;
        End;
        Else
        Begin
            R := Primitive.BoundingRectangle;
            CenterX := (R.Left + R.Right) Div 2;
            CenterY := (R.Bottom + R.Top) Div 2;
            TargetX := OldX + NewX - CenterX;
            TargetY := OldY + NewY - CenterY;
            Primitive.RotateBy(180);
            Primitive.MoveByXY(TargetX - CenterX, TargetY - CenterY);
        End;
    End;
    Primitive.EndModify;
End;

Procedure TransformPlacementPrimitiveGroup(Board : IPCB_Board;
                                           Component : IPCB_Component;
                                           OldXText, OldYText : String;
                                           NewXText, NewYText : String;
                                           NewRotation : Double;
                                           Rotate180 : Boolean);
Var
    Iterator                    : IPCB_BoardIterator;
    Primitive                   : IPCB_Primitive;
    OldX, OldY, NewX, NewY      : TCoord;
    NameAddress, CommentAddress : TPCBObjectHandle;
Begin
    OldX := PlacementTransformCoord(OldXText);
    OldY := PlacementTransformCoord(OldYText);
    NewX := PlacementTransformCoord(NewXText);
    NewY := PlacementTransformCoord(NewYText);
    If (Abs(Component.X - NewX) <= 1) And
       (Abs(Component.Y - NewY) <= 1) And
       (Abs(PlacementAngle(Component.Rotation) -
            PlacementAngle(NewRotation)) <= 0.001) Then
        Exit;
    NameAddress := Component.Name.I_ObjectAddress;
    CommentAddress := Component.Comment.I_ObjectAddress;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(AllObjects);
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Primitive := Iterator.FirstPCBObject;
    While Primitive <> Nil Do
    Begin
        If Primitive.Component <> Nil Then
            If (UpperCase(Primitive.Component.SourceDesignator) =
                UpperCase(Component.SourceDesignator)) And
               (Primitive.I_ObjectAddress <> NameAddress) And
               (Primitive.I_ObjectAddress <> CommentAddress) Then
            Begin
                If Rotate180 Then
                    RotatePlacementPrimitive180(Primitive, OldX, OldY, NewX, NewY)
                Else
                Begin
                    Primitive.BeginModify;
                    Primitive.MoveByXY(NewX - OldX, NewY - OldY);
                    Primitive.EndModify;
                End;
            End;
        Primitive := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);

    Component.BeginModify;
    Component.X := NewX;
    Component.Y := NewY;
    Component.Rotation := NewRotation;
    Component.Rebuild;
    Component.SetState_XSizeYSize;
    Component.EndModify;
End;

Function PlacementCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function InvariantFloat(Value : Double) : String;
Begin
    Result := StringReplace(FloatToStr(Value), ',', '.', rfReplaceAll);
End;

Function IsPreRefinementTarget(PlanIdx : Integer; XCoord, YCoord : TCoord) : Boolean;
Begin
    Result := False;
    Case PlanIdx Of
        43..45, 58: Result := (Abs(XCoord - PlacementCoord('38.5mm')) <= 1);
        46..49: Result := (Abs(YCoord - PlacementCoord('26.5mm')) <= 1);
        50..52: Result := (Abs(XCoord - PlacementCoord('65.5mm')) <= 1);
        54..56, 64: Result := (Abs(YCoord - PlacementCoord('53.5mm')) <= 1);
        63: Result := (Abs(YCoord - PlacementCoord('36.5mm')) <= 1) Or
                      ((Abs(XCoord - PlacementCoord('67.5mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('35.5mm')) <= 1));
        76: Result := ((Abs(XCoord - PlacementCoord('69mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('55mm')) <= 1)) Or
                      ((Abs(XCoord - PlacementCoord('70mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('54mm')) <= 1)) Or
                      ((Abs(XCoord - PlacementCoord('71mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('54mm')) <= 1));
        83: Result := (Abs(XCoord - PlacementCoord('68mm')) <= 1);
        85: Result := ((Abs(XCoord - PlacementCoord('68.5mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('59mm')) <= 1)) Or
                      ((Abs(XCoord - PlacementCoord('68.5mm')) <= 1) And
                       (Abs(YCoord - PlacementCoord('59.5mm')) <= 1));
    End;
End;

Function IsCanonicalBoardPath(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (ExtractFileName(APath) = 'EVT_SYS_CARRIER.PcbDoc') And
        (Pos('\hardware\system_carrier\altium\native\', P) > 0);
End;

Function FindCarrierPCBProject : IProject;
Var
    WS        : IWorkspace;
    Candidate : IProject;
    Doc       : IDocument;
    P         : String;
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
        P := LowerCase(Candidate.DM_ProjectFullPath);
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        If Pos('\hardware\system_carrier\altium\native\', P) = 0 Then Continue;

        For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Candidate.DM_LogicalDocuments(J);
            If Doc = Nil Then Continue;
            If UpperCase(ExtractFileExt(Doc.DM_FullPath)) <> '.PCBDOC' Then Continue;
            If Not IsCanonicalBoardPath(Doc.DM_FullPath) Then Continue;
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
        If IsCanonicalBoardPath(Result.FileName) Then Exit;
    Result := Nil;

    Project := FindCarrierPCBProject;
    If Project = Nil Then Exit;

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If Doc = Nil Then Continue;
        If UpperCase(ExtractFileExt(Doc.DM_FullPath)) <> '.PCBDOC' Then Continue;
        If Not IsCanonicalBoardPath(Doc.DM_FullPath) Then Continue;

        PcbDoc := Client.OpenDocument('PCB', Doc.DM_FullPath);
        If PcbDoc = Nil Then Continue;
        Client.ShowDocument(PcbDoc);
        Result := PCBServer.GetPCBBoardByPath(Doc.DM_FullPath);
        Exit;
    End;
End;

Procedure WritePlacementInventory(Board : IPCB_Board; FileName : String);
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
    Rpt       : TStringList;
    PlanIdx   : Integer;
    CBox      : TCoordRect;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pattern,x_mil,y_mil,rotation_deg,layer,plan_index,left_mil,bottom_mil,right_mil,top_mil');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        PlanIdx := PlacementIndex(Component.SourceDesignator);
        CBox := Component.BoundingRectangle;
        Rpt.Add(
            '"' + Component.SourceDesignator + '","' + Component.Pattern + '",' +
            InvariantFloat(CoordToMils(Component.X)) + ',' +
            InvariantFloat(CoordToMils(Component.Y)) + ',' +
            InvariantFloat(Component.Rotation) + ',' +
            IntToStr(Ord(Component.Layer)) + ',' + IntToStr(PlanIdx) + ',' +
            InvariantFloat(CoordToMils(CBox.Left)) + ',' +
            InvariantFloat(CoordToMils(CBox.Bottom)) + ',' +
            InvariantFloat(CoordToMils(CBox.Right)) + ',' +
            InvariantFloat(CoordToMils(CBox.Top))
        );
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(FileName);
    Rpt.Free;
End;

Procedure ApplyEVTPlacement;
Var
    Board          : IPCB_Board;
    Iterator       : IPCB_BoardIterator;
    Component      : IPCB_Component;
    Rect           : TCoordRect;
    Found          : Array[0..91] Of Integer;
    I              : Integer;
    PlanIdx        : Integer;
    ComponentCount : Integer;
    BaselineOK     : Boolean;
    AtTarget       : Boolean;
    OutsideBoard   : Boolean;
    OutputPath     : String;
    J4             : IPCB_Component;
    J5             : IPCB_Component;
    J6             : IPCB_Component;
    SW1            : IPCB_Component;
Begin
    Board := ResolveNativeBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT placement stopped: no active PCB.');
        Exit;
    End;
    If Not IsCanonicalBoardPath(Board.FileName) Then
    Begin
        ShowMessage('EVT placement stopped: the active PCB is not the canonical native EVT_SYS_CARRIER.PcbDoc.');
        Exit;
    End;

    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    If (Abs(Rect.Left) > 1) Or (Abs(Rect.Bottom) > 1) Or
       (Abs(Rect.Right - PlacementCoord('100mm')) > 1) Or
       (Abs(Rect.Top - PlacementCoord('80mm')) > 1) Then
    Begin
        ShowMessage('EVT placement stopped: board outline is not the locked 0..100mm by 0..80mm datum.');
        Exit;
    End;

    For I := 0 To 91 Do Found[I] := 0;
    ComponentCount := 0;
    BaselineOK := True;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        ComponentCount := ComponentCount + 1;
        PlanIdx := PlacementIndex(Component.SourceDesignator);
        If PlanIdx < 0 Then
            BaselineOK := False
        Else
        Begin
            Found[PlanIdx] := Found[PlanIdx] + 1;
            If Component.Layer <> eTopLayer Then BaselineOK := False;
            AtTarget :=
                (Abs(Component.X - PlacementCoord(PlacementX(PlanIdx))) <= 1) And
                (Abs(Component.Y - PlacementCoord(PlacementY(PlanIdx))) <= 1);
            OutsideBoard := Component.X > Rect.Right;
            If (PlanIdx = 12) And Not AtTarget And
               ((Abs(Component.X - PlacementCoord('65mm')) <= 1) Or
                (Abs(Component.X - PlacementCoord('67mm')) <= 1)) And
               (Abs(Component.Y - PlacementCoord('40mm')) <= 1) Then
            Begin
            End
            Else If (PlanIdx = 18) And Not AtTarget And
                    (Abs(Component.X - PlacementCoord('65mm')) <= 1) And
                    (Abs(Component.Y - PlacementCoord('50mm')) <= 1) Then
            Begin
            End
            Else If PlanIdx <= 21 Then
            Begin
                If Not AtTarget And
                   Not ((((PlanIdx = 6) Or (PlanIdx = 7)) And
                         (Abs(Component.X - TargetX) <= 1) And
                         (Abs(Component.Y - TargetY) <= 1) And
                         (Abs(Component.Rotation) <= 0.001)) Or
                        ((PlanIdx = 20) And
                         (Abs(Component.X - PlacementCoord('96mm')) <= 1) And
                         (Abs(Component.Y - PlacementCoord('60mm')) <= 1) And
                         (Abs(Component.Rotation) <= 0.001))) Then
                    BaselineOK := False;
            End
            Else If Not (AtTarget Or OutsideBoard Or
                ((PlanIdx = 22) And
                 (Abs(Component.X - PlacementCoord('70mm')) <= 1) And
                 (Abs(Component.Y - PlacementCoord('5.5mm')) <= 1)) Or
                IsPreRefinementTarget(PlanIdx, Component.X, Component.Y) Or
                ((PlanIdx = 53) And
                 (Abs(Component.X - PlacementCoord('65.5mm')) <= 1) And
                 (Abs(Component.Y - PlacementCoord('48mm')) <= 1))) Then
                BaselineOK := False;
        End;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    For I := 0 To 91 Do If Found[I] <> 1 Then BaselineOK := False;
    If (ComponentCount <> 92) Or Not BaselineOK Then
    Begin
        ShowMessage('EVT placement stopped: component inventory or pre-placement coordinates do not match the approved 92-component baseline.');
        Exit;
    End;

    J4 := FindPlacementComponent(Board, 'J4');
    J5 := FindPlacementComponent(Board, 'J5');
    J6 := FindPlacementComponent(Board, 'J6');
    SW1 := FindPlacementComponent(Board, 'SW1');
    If (J4 = Nil) Or (J5 = Nil) Or (J6 = Nil) Or (SW1 = Nil) Then
    Begin
        ShowMessage('EVT placement stopped: J4, J5, J6 or SW1 is missing.');
        Exit;
    End;

    PCBServer.PreProcess;
    TransformPlacementPrimitiveGroup(Board, J4, '95mm', '30mm',
        '95mm', '30mm', 180, True);
    TransformPlacementPrimitiveGroup(Board, J5, '95mm', '14mm',
        '95mm', '14mm', 180, True);
    TransformPlacementPrimitiveGroup(Board, J6, '96mm', '60mm',
        '94.75mm', '60mm', 180, True);
    TransformPlacementPrimitiveGroup(Board, SW1, '70mm', '5.5mm',
        '70mm', '8mm', 90, False);
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        PlanIdx := PlacementIndex(Component.SourceDesignator);
        Component.X := PlacementCoord(PlacementX(PlanIdx));
        Component.Y := PlacementCoord(PlacementY(PlanIdx));
        Component.Rotation := PlacementRotation(PlanIdx);
        Component.LockStrings := False;
        Component.CommentOn := False;
        Component.NameOn := True;
        Component.Name.UseTTFonts := False;
        Component.Name.Size := PlacementCoord('0.8mm');
        Component.Name.Width := PlacementCoord('0.15mm');
        Component.Name.Layer := eTopOverlay;
        Component.Name.Rotation := 0;
        Component.NameAutoPosition := eAutoPos_TopCenter;
        Component.AutoPosition_NameComment;
        Component.Selected := False;
        Component := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    PCBServer.PostProcess;

    OutputPath := ExtractFilePath(Board.FileName) + '..\placement\placement_runtime_inventory.csv';
    WritePlacementInventory(Board, OutputPath);
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('EVT placement applied to all 92 components. Save the PCB and complete the placement review.');
End;
