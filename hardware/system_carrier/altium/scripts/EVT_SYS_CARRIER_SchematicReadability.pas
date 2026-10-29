{ Audit and repair presentation-only component text on the canonical native
  schematics. Electrical objects and component locations are not changed.

  Run procedures:
    ExportSchematicReadabilityAudit
    RepairSchematicReadability
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function BoolText(B : Boolean) : String;
Begin
    If B Then Result := 'true' Else Result := 'false';
End;

Function IsCanonicalNativePath(APath : String) : Boolean;
Var
    P : String;
Begin
    P := LowerCase(APath);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (Pos('\build\', P) = 0);
End;

Function IsCarrierSheet(SheetName : String) : Boolean;
Begin
    Result :=
        (SheetName = 'EVT_SYS_CARRIER.SchDoc') Or
        (SheetName = '10_POWER_INPUT.SchDoc') Or
        (SheetName = '20_MCU_CORE.SchDoc') Or
        (SheetName = '30_TIME_GNSS.SchDoc') Or
        (SheetName = '40_IMU.SchDoc') Or
        (SheetName = '50_RADAR_IO_CAN.SchDoc') Or
        (SheetName = '60_HOST_UART.SchDoc') Or
        (SheetName = '70_DEBUG_BOOT.SchDoc');
End;

Function FindCarrierProject : IProject;
Var
    WS        : IWorkspace;
    Candidate : IProject;
    Doc       : IDocument;
    I, J      : Integer;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;

    For I := 0 To WS.DM_ProjectCount - 1 Do
    Begin
        Candidate := WS.DM_Projects(I);
        If Candidate = Nil Then Continue;
        If ExtractFileName(Candidate.DM_ProjectFullPath) <> 'EVT_SYS_CARRIER.PrjPcb' Then Continue;
        If Not IsCanonicalNativePath(Candidate.DM_ProjectFullPath) Then Continue;
        For J := 0 To Candidate.DM_LogicalDocumentCount - 1 Do
        Begin
            Doc := Candidate.DM_LogicalDocuments(J);
            If Doc = Nil Then Continue;
            If Doc.DM_DocumentKind <> 'SCH' Then Continue;
            If Not IsCarrierSheet(ExtractFileName(Doc.DM_FullPath)) Then Continue;
            Result := Candidate;
            Exit;
        End;
    End;
End;

Function LoadSheet(Doc : IDocument; Var ServerDoc : IServerDocument) : ISch_Document;
Begin
    Result := Nil;
    ServerDoc := Nil;
    If Doc = Nil Then Exit;
    Result := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
    If Result <> Nil Then Exit;
    ServerDoc := Client.OpenDocument('SCH', Doc.DM_FullPath);
    If ServerDoc = Nil Then Exit;
    Client.ShowDocument(ServerDoc);
    Result := SchServer.GetSchDocumentByPath(Doc.DM_FullPath);
End;

Function RectsOverlap(A, B : TCoordRect) : Boolean;
Begin
    Result :=
        (A.Left < B.Right) And (A.Right > B.Left) And
        (A.Bottom < B.Top) And (A.Top > B.Bottom);
End;

Function RectOutside(R : TCoordRect; MinX, MinY, MaxX, MaxY : TCoord) : Boolean;
Begin
    Result :=
        (R.Left < MinX) Or (R.Right > MaxX) Or
        (R.Bottom < MinY) Or (R.Top > MaxY);
End;

Function SafeMargin(Doc : ISch_Document) : TCoord;
Begin
    Result := Doc.SheetMarginWidth;
    If Result < MilsToCoord(200) Then Result := MilsToCoord(200);
End;

Procedure ExportSchematicReadabilityAudit;
Var
    Project       : IProject;
    Doc           : IDocument;
    ServerDoc     : IServerDocument;
    SchDoc        : ISch_Document;
    Iterator      : ISch_Iterator;
    Component     : ISch_Component;
    DesignatorObj : ISch_Parameter;
    CommentObj    : ISch_Parameter;
    Report        : TStringList;
    SheetName     : String;
    BasePath      : String;
    Ref           : String;
    CommentText   : String;
    SymbolRect    : TCoordRect;
    FullRect      : TCoordRect;
    DesignatorRect: TCoordRect;
    CommentRect   : TCoordRect;
    Margin        : TCoord;
    I             : Integer;
    Count         : Integer;
Begin
    Project := FindCarrierProject;
    If Project = Nil Then
    Begin
        ShowMessage('Schematic readability audit stopped: canonical native project not found.');
        Exit;
    End;

    Report := TStringList.Create;
    Report.Add('sheet,designator,comment,comment_hidden,designator_hidden,' +
               'symbol_left_mil,symbol_bottom_mil,symbol_right_mil,symbol_top_mil,' +
               'full_left_mil,full_bottom_mil,full_right_mil,full_top_mil,' +
               'designator_over_symbol,comment_over_symbol,symbol_outside_safe_frame,' +
               'full_outside_safe_frame,sheet_width_mil,sheet_height_mil');
    Count := 0;
    BasePath := '';

    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
        If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;
        SheetName := ExtractFileName(Doc.DM_FullPath);
        If Not IsCarrierSheet(SheetName) Then Continue;

        SchDoc := LoadSheet(Doc, ServerDoc);
        If SchDoc = Nil Then Continue;
        If BasePath = '' Then BasePath := ExtractFilePath(Doc.DM_FullPath) + '..\equivalence\';
        Margin := SafeMargin(SchDoc);

        Iterator := SchDoc.SchIterator_Create;
        If Iterator = Nil Then Continue;
        Iterator.SetState_IterationDepth(eIterateFirstLevel);
        Iterator.AddFilter_ObjectSet(MkSet(eSchComponent));
        Try
            Component := Iterator.FirstSchObject;
            While Component <> Nil Do
            Begin
                DesignatorObj := Component.Designator;
                CommentObj := Component.Comment;
                Ref := Trim(DesignatorObj.Text);
                CommentText := Trim(CommentObj.Text);
                SymbolRect := Component.BoundingRectangle;
                FullRect := Component.BoundingRectangle_Full;
                DesignatorRect := DesignatorObj.BoundingRectangle;
                CommentRect := CommentObj.BoundingRectangle;
                Report.Add(
                    CsvQuote(SheetName) + ',' + CsvQuote(Ref) + ',' + CsvQuote(CommentText) + ',' +
                    BoolText(CommentObj.IsHidden) + ',' + BoolText(DesignatorObj.IsHidden) + ',' +
                    IntToStr(Round(CoordToMils(SymbolRect.Left))) + ',' +
                    IntToStr(Round(CoordToMils(SymbolRect.Bottom))) + ',' +
                    IntToStr(Round(CoordToMils(SymbolRect.Right))) + ',' +
                    IntToStr(Round(CoordToMils(SymbolRect.Top))) + ',' +
                    IntToStr(Round(CoordToMils(FullRect.Left))) + ',' +
                    IntToStr(Round(CoordToMils(FullRect.Bottom))) + ',' +
                    IntToStr(Round(CoordToMils(FullRect.Right))) + ',' +
                    IntToStr(Round(CoordToMils(FullRect.Top))) + ',' +
                    BoolText((Not DesignatorObj.IsHidden) And RectsOverlap(DesignatorRect, SymbolRect)) + ',' +
                    BoolText((Not CommentObj.IsHidden) And RectsOverlap(CommentRect, SymbolRect)) + ',' +
                    BoolText(RectOutside(SymbolRect, Margin, Margin,
                        SchDoc.SheetSizeX - Margin, SchDoc.SheetSizeY - Margin)) + ',' +
                    BoolText(RectOutside(FullRect, Margin, Margin,
                        SchDoc.SheetSizeX - Margin, SchDoc.SheetSizeY - Margin)) + ',' +
                    IntToStr(Round(CoordToMils(SchDoc.SheetSizeX))) + ',' +
                    IntToStr(Round(CoordToMils(SchDoc.SheetSizeY)))
                );
                Count := Count + 1;
                Component := Iterator.NextSchObject;
            End;
        Finally
            SchDoc.SchIterator_Destroy(Iterator);
        End;
    End;

    If BasePath <> '' Then
    Begin
        ForceDirectories(BasePath);
        Report.SaveToFile(BasePath + 'schematic_readability_audit.csv');
    End;
    Report.Free;
    ShowMessage('Schematic readability audit exported: ' + IntToStr(Count) + ' components.');
End;

Procedure ClampTextToSheet(TextObj : ISch_Parameter; SchDoc : ISch_Document;
                           Margin : TCoord);
Var
    R             : TCoordRect;
    DX, DY        : TCoord;
Begin
    R := TextObj.BoundingRectangle;
    DX := 0;
    DY := 0;
    If R.Left < Margin Then DX := Margin - R.Left;
    If R.Right + DX > SchDoc.SheetSizeX - Margin Then
        DX := SchDoc.SheetSizeX - Margin - R.Right;
    If R.Bottom < Margin Then DY := Margin - R.Bottom;
    If R.Top + DY > SchDoc.SheetSizeY - Margin Then
        DY := SchDoc.SheetSizeY - Margin - R.Top;
    If (DX <> 0) Or (DY <> 0) Then TextObj.MoveByXY(DX, DY);
End;

Procedure RepairSchematicReadability;
Var
    Project       : IProject;
    Doc           : IDocument;
    ServerDoc     : IServerDocument;
    SchDoc        : ISch_Document;
    Iterator      : ISch_Iterator;
    Component     : ISch_Component;
    DesignatorObj : ISch_Parameter;
    CommentObj    : ISch_Parameter;
    SymbolRect    : TCoordRect;
    Margin        : TCoord;
    SheetName     : String;
    Ref           : String;
    I             : Integer;
    SheetsChanged : Integer;
    CommentsHidden: Integer;
    DesignatorsSet: Integer;
Begin
    Project := FindCarrierProject;
    If Project = Nil Then
    Begin
        ShowMessage('Schematic readability repair stopped: canonical native project not found.');
        Exit;
    End;

    SheetsChanged := 0;
    CommentsHidden := 0;
    DesignatorsSet := 0;
    For I := 0 To Project.DM_LogicalDocumentCount - 1 Do
    Begin
        Doc := Project.DM_LogicalDocuments(I);
        If (Doc = Nil) Or (Doc.DM_DocumentKind <> 'SCH') Then Continue;
        If Not IsCanonicalNativePath(Doc.DM_FullPath) Then Continue;
        SheetName := ExtractFileName(Doc.DM_FullPath);
        If Not IsCarrierSheet(SheetName) Then Continue;

        SchDoc := LoadSheet(Doc, ServerDoc);
        If SchDoc = Nil Then Continue;
        Margin := SafeMargin(SchDoc);
        SchServer.ProcessControl.PreProcess(SchDoc, '');
        Try
            Iterator := SchDoc.SchIterator_Create;
            If Iterator = Nil Then Continue;
            Iterator.SetState_IterationDepth(eIterateFirstLevel);
            Iterator.AddFilter_ObjectSet(MkSet(eSchComponent));
            Try
                Component := Iterator.FirstSchObject;
                While Component <> Nil Do
                Begin
                    DesignatorObj := Component.Designator;
                    CommentObj := Component.Comment;
                    SymbolRect := Component.BoundingRectangle;
                    Ref := Trim(DesignatorObj.Text);

                    SchServer.RobotManager.SendMessage(CommentObj.I_ObjectAddress,
                        c_BroadCast, SCHM_BeginModify, c_NoEventData);
                    If Not CommentObj.IsHidden Then CommentsHidden := CommentsHidden + 1;
                    CommentObj.IsHidden := True;
                    SchServer.RobotManager.SendMessage(CommentObj.I_ObjectAddress,
                        c_BroadCast, SCHM_EndModify, c_NoEventData);

                    SchServer.RobotManager.SendMessage(DesignatorObj.I_ObjectAddress,
                        c_BroadCast, SCHM_BeginModify, c_NoEventData);
                    If (Ref <> '') And (Ref[1] <> '#') Then
                    Begin
                        DesignatorObj.IsHidden := False;
                        DesignatorObj.Autoposition := False;
                        DesignatorObj.Location := Point(SymbolRect.Left,
                            SymbolRect.Top + MilsToCoord(180));
                        ClampTextToSheet(DesignatorObj, SchDoc, Margin);
                        DesignatorsSet := DesignatorsSet + 1;
                    End
                    Else
                        DesignatorObj.IsHidden := True;
                    SchServer.RobotManager.SendMessage(DesignatorObj.I_ObjectAddress,
                        c_BroadCast, SCHM_EndModify, c_NoEventData);

                    Component := Iterator.NextSchObject;
                End;
            Finally
                SchDoc.SchIterator_Destroy(Iterator);
            End;
        Finally
            SchServer.ProcessControl.PostProcess(SchDoc, '');
        End;
        SchDoc.GraphicallyInvalidate;
        Client.ShowDocument(Client.GetDocumentByPath(Doc.DM_FullPath));
        SaveCurrentDocument;
        SheetsChanged := SheetsChanged + 1;
    End;

    ShowMessage(
        'Schematic readability repair complete. Sheets saved: ' + IntToStr(SheetsChanged) +
        '; comments hidden: ' + IntToStr(CommentsHidden) +
        '; designators positioned: ' + IntToStr(DesignatorsSet) + '.');
End;
