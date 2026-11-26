Function R9PointKey(P : TLocation) : String;
Begin
    Result := IntToStr(Round(CoordToMils(P.X))) + ':' +
        IntToStr(Round(CoordToMils(P.Y)));
End;

Function R9CsvText(S : String) : String;
Begin
    Result := '"' + StringReplace(S, '"', '""', rfReplaceAll) + '"';
End;

Procedure R9AddPoint(List : TStringList; P : TLocation);
Var
    K : String;
Begin
    K := R9PointKey(P);
    If List.IndexOf(K) < 0 Then List.Add(K);
End;

Function R9HasPoint(List : TStringList; P : TLocation) : Boolean;
Begin
    Result := List.IndexOf(R9PointKey(P)) >= 0;
End;

Function R9PinHotspot(Pin : ISch_Pin) : TLocation;
Begin
    Result := Pin.Location;
    Case Pin.Orientation Of
        0 : Result.X := Result.X + Pin.PinLength;
        1 : Result.Y := Result.Y + Pin.PinLength;
        2 : Result.X := Result.X - Pin.PinLength;
        3 : Result.Y := Result.Y - Pin.PinLength;
    End;
End;

Procedure R9CollectWires(Doc : ISch_Document; Points : TStringList);
Var
    Iterator : ISch_Iterator;
    Wire     : ISch_Wire;
    I        : Integer;
Begin
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(eWire));
    Try
        Wire := Iterator.FirstSchObject;
        While Wire <> Nil Do
        Begin
            For I := 1 To Wire.GetState_VerticesCount Do
                R9AddPoint(Points, Wire.GetState_Vertex(I));
            Wire := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Procedure R9CollectObjectPoints(Doc : ISch_Document; ObjectID : Integer;
    Points : TStringList);
Var
    Iterator : ISch_Iterator;
    Obj      : ISch_GraphicalObject;
Begin
    Iterator := Doc.SchIterator_Create;
    If Iterator = Nil Then Exit;
    Iterator.SetState_IterationDepth(eIterateFirstLevel);
    Iterator.AddFilter_ObjectSet(MkSet(ObjectID));
    Try
        Obj := Iterator.FirstSchObject;
        While Obj <> Nil Do
        Begin
            R9AddPoint(Points, Obj.Location);
            Obj := Iterator.NextSchObject;
        End;
    Finally
        Doc.SchIterator_Destroy(Iterator);
    End;
End;

Function R9FindUnifiedDocument(Var TargetPath : String) : ISch_Document;
Var
    WS      : IWorkspace;
    Project : IProject;
    I       : Integer;
Begin
    Result := SchServer.GetCurrentSchDocument;
    If Result <> Nil Then
    Begin
        If ExtractFileName(Result.DocumentName) =
            '00_UNIFIED_CONNECTED_SCHEMATIC.SchDoc' Then
        Begin
            TargetPath := Result.DocumentName;
            Exit;
        End;
        Result := Nil;
    End;

    WS := GetWorkspace;
    If WS = Nil Then Exit;
    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Project := WS.DM_Projects(I);
        If Project = Nil Then Continue;
        TargetPath := ExtractFilePath(Project.DM_ProjectFullPath) +
            '00_UNIFIED_CONNECTED_SCHEMATIC.SchDoc';
        Result := SchServer.GetSchDocumentByPath(TargetPath);
        If Result <> Nil Then Exit;
    End;
    TargetPath := '';
End;

Procedure AuditUnifiedPinsV2;
Var
    Doc             : ISch_Document;
    Components      : ISch_Iterator;
    Pins            : ISch_Iterator;
    Component       : ISch_Component;
    Pin             : ISch_Pin;
    WirePoints      : TStringList;
    LabelPoints     : TStringList;
    PortPoints      : TStringList;
    NoERCPoints     : TStringList;
    Rows            : TStringList;
    Summary         : TStringList;
    Ref             : String;
    PinNo           : String;
    PinName         : String;
    Evidence        : String;
    Status          : String;
    Hotspot         : TLocation;
    OutputFolder    : String;
    CsvPath         : String;
    SummaryPath     : String;
    TargetPath      : String;
    TotalPins       : Integer;
    ConnectedPins   : Integer;
    MarkedPins      : Integer;
    UnmarkedPins    : Integer;
Begin
    TargetPath := '';
    Doc := R9FindUnifiedDocument(TargetPath);
    If Doc = Nil Then
    Begin
        ShowMessage('Pin audit stopped: open the unified schematic first.');
        Exit;
    End;

    OutputFolder := ExtractFilePath(TargetPath);
    CsvPath := OutputFolder + 'R9_unified_master_full_pin_audit_2026-11-19.csv';
    SummaryPath := OutputFolder + 'R9_unified_master_full_pin_audit_2026-11-19.txt';

    WirePoints := TStringList.Create;
    LabelPoints := TStringList.Create;
    PortPoints := TStringList.Create;
    NoERCPoints := TStringList.Create;
    Rows := TStringList.Create;
    Summary := TStringList.Create;
    Try
        WirePoints.Sorted := True;
        WirePoints.Duplicates := dupIgnore;
        LabelPoints.Sorted := True;
        LabelPoints.Duplicates := dupIgnore;
        PortPoints.Sorted := True;
        PortPoints.Duplicates := dupIgnore;
        NoERCPoints.Sorted := True;
        NoERCPoints.Duplicates := dupIgnore;
        Rows.Add('Ref,Pin,PinName,ElectricalType,X_mil,Y_mil,Wire,NetLabel,Port,NoConnect,Status,Evidence');

        R9CollectWires(Doc, WirePoints);
        R9CollectObjectPoints(Doc, eNetLabel, LabelPoints);
        R9CollectObjectPoints(Doc, ePort, PortPoints);
        R9CollectObjectPoints(Doc, eNoERC, NoERCPoints);

        TotalPins := 0;
        ConnectedPins := 0;
        MarkedPins := 0;
        UnmarkedPins := 0;
        Components := Doc.SchIterator_Create;
        If Components = Nil Then Exit;
        Components.SetState_IterationDepth(eIterateFirstLevel);
        Components.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Components.FirstSchObject;
            While Component <> Nil Do
            Begin
                Ref := Component.Designator.Text;
                Pins := Component.SchIterator_Create;
                If Pins <> Nil Then
                Begin
                    Pins.SetState_IterationDepth(eIterateFirstLevel);
                    Pins.AddFilter_ObjectSet(MkSet(ePin));
                    Try
                        Pin := Pins.FirstSchObject;
                        While Pin <> Nil Do
                        Begin
                            TotalPins := TotalPins + 1;
                            PinNo := Pin.Designator;
                            PinName := Pin.Name;
                            Hotspot := R9PinHotspot(Pin);
                            Evidence := '';
                            If R9HasPoint(WirePoints, Hotspot) Then
                                Evidence := Evidence + 'WIRE;';
                            If R9HasPoint(LabelPoints, Hotspot) Then
                                Evidence := Evidence + 'NET_LABEL;';
                            If R9HasPoint(PortPoints, Hotspot) Then
                                Evidence := Evidence + 'PORT;';

                            If Evidence <> '' Then
                            Begin
                                Status := 'CONNECTED';
                                ConnectedPins := ConnectedPins + 1;
                            End
                            Else If R9HasPoint(NoERCPoints, Hotspot) Then
                            Begin
                                Status := 'NC_MARKED';
                                Evidence := 'NO_CONNECT;';
                                MarkedPins := MarkedPins + 1;
                            End
                            Else
                            Begin
                                Status := 'OPEN_UNMARKED';
                                Evidence := 'NONE;';
                                UnmarkedPins := UnmarkedPins + 1;
                            End;

                            Rows.Add(R9CsvText(Ref) + ',' + R9CsvText(PinNo) + ',' +
                                R9CsvText(PinName) + ',' + IntToStr(Pin.Electrical) + ',' +
                                StringReplace(FormatFloat('0.000', CoordToMils(Hotspot.X)), ',', '.', rfReplaceAll) + ',' +
                                StringReplace(FormatFloat('0.000', CoordToMils(Hotspot.Y)), ',', '.', rfReplaceAll) + ',' +
                                R9CsvText(BoolToStr(R9HasPoint(WirePoints, Hotspot), True)) + ',' +
                                R9CsvText(BoolToStr(R9HasPoint(LabelPoints, Hotspot), True)) + ',' +
                                R9CsvText(BoolToStr(R9HasPoint(PortPoints, Hotspot), True)) + ',' +
                                R9CsvText(BoolToStr(R9HasPoint(NoERCPoints, Hotspot), True)) + ',' +
                                R9CsvText(Status) + ',' + R9CsvText(Evidence));
                            Pin := Pins.NextSchObject;
                        End;
                    Finally
                        Component.SchIterator_Destroy(Pins);
                    End;
                End;
                Component := Components.NextSchObject;
            End;
        Finally
            Doc.SchIterator_Destroy(Components);
        End;

        Rows.SaveToFile(CsvPath);
        Summary.Add('R9 unified master full pin audit');
        Summary.Add('Document: ' + TargetPath);
        Summary.Add('Wire endpoint count: ' + IntToStr(WirePoints.Count));
        Summary.Add('Net label anchor count: ' + IntToStr(LabelPoints.Count));
        Summary.Add('Port anchor count: ' + IntToStr(PortPoints.Count));
        Summary.Add('No-connect marker count: ' + IntToStr(NoERCPoints.Count));
        Summary.Add('Total pins: ' + IntToStr(TotalPins));
        Summary.Add('Connected pins: ' + IntToStr(ConnectedPins));
        Summary.Add('Explicitly marked NC pins: ' + IntToStr(MarkedPins));
        Summary.Add('Unmarked open pins: ' + IntToStr(UnmarkedPins));
        If UnmarkedPins = 0 Then Summary.Add('Result: PASS')
        Else Summary.Add('Result: FAIL');
        Summary.SaveToFile(SummaryPath);
        ShowMessage('Full pin audit complete. Wires: ' +
            IntToStr(WirePoints.Count) + ', total pins: ' +
            IntToStr(TotalPins) + ', connected: ' +
            IntToStr(ConnectedPins) + ', marked NC: ' +
            IntToStr(MarkedPins) + ', unmarked open: ' +
            IntToStr(UnmarkedPins) + '.');
    Finally
        Summary.Free;
        Rows.Free;
        NoERCPoints.Free;
        PortPoints.Free;
        LabelPoints.Free;
        WirePoints.Free;
    End;
End;
