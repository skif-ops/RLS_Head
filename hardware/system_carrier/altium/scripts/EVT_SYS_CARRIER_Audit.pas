{ EVT System Carrier native Altium read-only audit exporter.
  This script does not modify the PCB. It exports component, net and
  PCB-rule, pad-to-net and copper-layer-stack inventories from the
  currently active PcbDoc.

  Run procedure: ExportNativeAudit
}

Function CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function BoolText(B : Boolean) : String;
Begin
    If B Then
        Result := 'true'
    Else
        Result := 'false';
End;

Function InvariantFloat(Value : Double) : String;
Begin
    Result := StringReplace(FloatToStr(Value), ',', '.', rfReplaceAll);
End;

Function RuleKindToString(ARuleKind : TRuleKind) : String;
Begin
    Result := IntToStr(Ord(ARuleKind));

    Case ARuleKind Of
        eRule_Clearance                : Result := 'Clearance';
        eRule_MaxMinWidth              : Result := 'Width';
        eRule_MatchedLengths           : Result := 'MatchedLengths';
        eRule_DaisyChainStubLength     : Result := 'StubLength';
        eRule_PowerPlaneConnectStyle   : Result := 'PlaneConnect';
        eRule_RoutingTopology          : Result := 'RoutingTopology';
        eRule_RoutingPriority          : Result := 'RoutingPriority';
        eRule_RoutingLayers            : Result := 'RoutingLayers';
        eRule_RoutingCornerStyle       : Result := 'RoutingCorners';
        eRule_RoutingViaStyle          : Result := 'RoutingVias';
        eRule_PowerPlaneClearance      : Result := 'PlaneClearance';
        eRule_SolderMaskExpansion      : Result := 'SolderMaskExpansion';
        eRule_PasteMaskExpansion       : Result := 'PasteMaskExpansion';
        eRule_ShortCircuit             : Result := 'ShortCircuit';
        eRule_BrokenNets               : Result := 'UnRoutedNet';
        eRule_MinimumAnnularRing       : Result := 'MinimumAnnularRing';
        eRule_PolygonConnectStyle      : Result := 'PolygonConnect';
        eRule_ComponentClearance       : Result := 'ComponentClearance';
        eRule_ComponentRotations       : Result := 'ComponentOrientations';
        eRule_PermittedLayers          : Result := 'PermittedLayers';
        eRule_MaxMinImpedance          : Result := 'MaxMinImpedance';
        eRule_MaxMinHoleSize           : Result := 'HoleSize';
        eRule_MaxMinHeight             : Result := 'Height';
        eRule_DifferentialPairsRouting : Result := 'DiffPairsRouting';
        eRule_ConfinementConstraint    : Result := 'RoomDefinition';
    End;
End;

Procedure ExportComponents(Board : IPCB_Board; BasePath : String);
Var
    Iterator  : IPCB_BoardIterator;
    Component : IPCB_Component;
    Rpt       : TStringList;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pattern,x_mil,y_mil');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);

    Component := Iterator.FirstPCBObject;
    While Component <> Nil Do
    Begin
        Rpt.Add(
            CsvQuote(Component.SourceDesignator) + ',' +
            CsvQuote(Component.Pattern) + ',' +
            InvariantFloat(CoordToMils(Component.X)) + ',' +
            InvariantFloat(CoordToMils(Component.Y))
        );
        Component := Iterator.NextPCBObject;
    End;

    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'component_inventory.csv');
    Rpt.Free;
End;

Procedure ExportNets(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    Net      : IPCB_Net;
    Rpt      : TStringList;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('net_name');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eNetObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);

    Net := Iterator.FirstPCBObject;
    While Net <> Nil Do
    Begin
        Rpt.Add(CsvQuote(Net.Name));
        Net := Iterator.NextPCBObject;
    End;

    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'net_inventory.csv');
    Rpt.Free;
End;

Procedure ExportRules(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    Rule     : IPCB_Rule;
    Rpt      : TStringList;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('rule_name,rule_kind,unique_id,scope_1,scope_2,drc_enabled');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);

    Rule := Iterator.FirstPCBObject;
    While Rule <> Nil Do
    Begin
        Rpt.Add(
            CsvQuote(Rule.Name) + ',' +
            CsvQuote(RuleKindToString(Rule.RuleKind)) + ',' +
            CsvQuote(Rule.UniqueId) + ',' +
            CsvQuote(Rule.Scope1Expression) + ',' +
            CsvQuote(Rule.Scope2Expression) + ',' +
            CsvQuote(BoolText(Rule.DRCEnabled))
        );
        Rule := Iterator.NextPCBObject;
    End;

    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'rule_inventory.csv');
    Rpt.Free;
End;

Procedure ExportRuleConstraints(Board : IPCB_Board; BasePath : String);
Var
    Iterator      : IPCB_BoardIterator;
    Rule          : IPCB_Rule;
    WidthRule     : IPCB_MaxMinWidthConstraint;
    DiffRule      : IPCB_DifferentialPairsRoutingRule;
    ClearanceRule : IPCB_ClearanceConstraint;
    LayerObj      : IPCB_LayerObject;
    L             : TLayer;
    Rpt           : TStringList;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('rule_name,layer_name,min_width_raw,preferred_width_raw,max_width_raw,min_gap_raw,preferred_gap_raw,max_gap_raw');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Rule := Iterator.FirstPCBObject;
    While Rule <> Nil Do
    Begin
        If Copy(Rule.Name, 1, 2) = 'R_' Then
        Begin
            If Rule.RuleKind = eRule_Clearance Then
            Begin
                ClearanceRule := Rule;
                Rpt.Add(CsvQuote(Rule.Name) + ',All,,,,' +
                    IntToStr(ClearanceRule.Gap) + ',,');
            End;
            If (Rule.RuleKind = eRule_MaxMinWidth) Or
               (Rule.RuleKind = eRule_DifferentialPairsRouting) Then
                For L := eTopLayer To eBottomLayer Do
                Begin
                    LayerObj := Board.LayerStack.LayerObject[L];
                    If LayerObj <> Nil Then
                        If LayerObj.IsInLayerStack Then
                        Begin
                            If Rule.RuleKind = eRule_MaxMinWidth Then
                            Begin
                                WidthRule := Rule;
                                Rpt.Add(CsvQuote(Rule.Name) + ',' + CsvQuote(LayerObj.Name) + ',' +
                                    IntToStr(WidthRule.MinWidth[L]) + ',' +
                                    IntToStr(WidthRule.FavoredWidth[L]) + ',' +
                                    IntToStr(WidthRule.MaxWidth[L]) + ',,,');
                            End
                            Else
                            Begin
                                DiffRule := Rule;
                                Rpt.Add(CsvQuote(Rule.Name) + ',' + CsvQuote(LayerObj.Name) + ',' +
                                    IntToStr(DiffRule.MinWidth[L]) + ',' +
                                    IntToStr(DiffRule.PreferedWidth[L]) + ',' +
                                    IntToStr(DiffRule.MaxWidth[L]) + ',' +
                                    IntToStr(DiffRule.MinGap[L]) + ',' +
                                    IntToStr(DiffRule.PreferedGap[L]) + ',' +
                                    IntToStr(DiffRule.MaxGap[L]));
                            End;
                        End;
                End;
        End;
        Rule := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'rule_constraint_inventory.csv');
    Rpt.Free;
End;

Procedure ExportPadNets(Board : IPCB_Board; BasePath : String);
Var
    Iterator   : IPCB_BoardIterator;
    Pad        : IPCB_Pad;
    Rpt        : TStringList;
    Designator : String;
    NetName    : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('designator,pad_name,net_name');

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);

    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        Designator := '';
        NetName := '';

        If Pad.Component <> Nil Then
            Designator := Pad.Component.SourceDesignator;

        If Pad.Net <> Nil Then
            NetName := Pad.Net.Name;

        Rpt.Add(
            CsvQuote(Designator) + ',' +
            CsvQuote(Pad.Name) + ',' +
            CsvQuote(NetName)
        );
        Pad := Iterator.NextPCBObject;
    End;

    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'pad_net_inventory.csv');
    Rpt.Free;
End;

Procedure ExportLayerStack(Board : IPCB_Board; BasePath : String);
Var
    Stack    : IPCB_LayerStack;
    LayerObj : IPCB_LayerObject;
    Rpt      : TStringList;
    OrderNo  : Integer;
    Layer    : TLayer;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('order,layer_name');

    Stack := Board.LayerStack;
    If Stack <> Nil Then
    Begin
        OrderNo := 1;
        { AD26 DelphiScript does not expose FirstLayer/NextLayer. Enumerate
          signal and plane layer IDs and retain only layers in this stack. }
        For Layer := eTopLayer To eBottomLayer Do
        Begin
            LayerObj := Stack.LayerObject[Layer];
            If LayerObj <> Nil Then
                If LayerObj.IsInLayerStack Then
                Begin
                    Rpt.Add(
                        IntToStr(OrderNo) + ',' +
                        CsvQuote(LayerObj.Name)
                    );
                    Inc(OrderNo);
                End;
        End;
        For Layer := eInternalPlane1 To eInternalPlane16 Do
        Begin
            LayerObj := Stack.LayerObject[Layer];
            If LayerObj <> Nil Then
                If LayerObj.IsInLayerStack Then
                Begin
                    Rpt.Add(
                        IntToStr(OrderNo) + ',' +
                        CsvQuote(LayerObj.Name)
                    );
                    Inc(OrderNo);
                End;
        End;
    End;

    Rpt.SaveToFile(BasePath + 'layer_stack_inventory.csv');
    Rpt.Free;
End;

Procedure ExportMechanical(Board : IPCB_Board; BasePath : String);
Var
    Rect     : TCoordRect;
    Iterator : IPCB_BoardIterator;
    Pad      : IPCB_Pad;
    Rpt      : TStringList;
    I        : Integer;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('kind,id,x_raw,y_raw,width_raw,height_raw,diameter_raw,plated,details');
    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    Rect := Board.BoardOutline.BoundingRectangle;
    Rpt.Add('outline,board,' + IntToStr(Rect.Left) + ',' +
        IntToStr(Rect.Bottom) + ',' +
        IntToStr(Rect.Right - Rect.Left) + ',' +
        IntToStr(Rect.Top - Rect.Bottom) + ',,,');
    For I := 0 To Board.BoardOutline.PointCount - 1 Do
    Begin
        If Board.BoardOutline.Segments[I].Kind = ePolySegmentArc Then
            Rpt.Add('vertex,' + IntToStr(I) + ',' +
                IntToStr(Board.BoardOutline.Segments[I].VX) + ',' +
                IntToStr(Board.BoardOutline.Segments[I].VY) + ',,,' +
                IntToStr(Board.BoardOutline.Segments[I].Radius) + ',,arc')
        Else
            Rpt.Add('vertex,' + IntToStr(I) + ',' +
                IntToStr(Board.BoardOutline.Segments[I].VX) + ',' +
                IntToStr(Board.BoardOutline.Segments[I].VY) + ',,,,,line');
    End;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If (Pad.Component = Nil) And (Pad.HoleSize > 0) Then
            Rpt.Add('free_hole,' + CsvQuote(Pad.Name) + ',' +
                IntToStr(Pad.X) + ',' + IntToStr(Pad.Y) + ',,,' +
                IntToStr(Pad.HoleSize) + ',' + BoolText(Pad.Plated) + ',');
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'mechanical_inventory.csv');
    Rpt.Free;
End;

Procedure ExportPairsAndClasses(Board : IPCB_Board; BasePath : String);
Var
    Iterator : IPCB_BoardIterator;
    PairObj  : IPCB_DifferentialPair;
    ObjClass : IPCB_ObjectClass;
    Rpt      : TStringList;
    KindName : String;
    PosName  : String;
    NegName  : String;
    I        : Integer;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('pair_name,positive_net,negative_net');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eDifferentialPairObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    PairObj := Iterator.FirstPCBObject;
    While PairObj <> Nil Do
    Begin
        PosName := '';
        NegName := '';
        If PairObj.PositiveNet <> Nil Then PosName := PairObj.PositiveNet.Name;
        If PairObj.NegativeNet <> Nil Then NegName := PairObj.NegativeNet.Name;
        Rpt.Add(CsvQuote(PairObj.Name) + ',' +
                CsvQuote(PosName) + ',' + CsvQuote(NegName));
        PairObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'diff_pair_inventory.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('class_name,member_kind,member_name');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eClassObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ObjClass := Iterator.FirstPCBObject;
    While ObjClass <> Nil Do
    Begin
        KindName := IntToStr(Ord(ObjClass.MemberKind));
        If ObjClass.MemberKind = eClassMemberKind_Net Then KindName := 'Net';
        If ObjClass.MemberKind = eClassMemberKind_DifferentialPair Then
            KindName := 'DifferentialPair';
        For I := 0 To 999 Do
        Begin
            If ObjClass.MemberName[I] = '' Then Break;
            Rpt.Add(CsvQuote(ObjClass.Name) + ',' +
                    CsvQuote(KindName) + ',' +
                    CsvQuote(ObjClass.MemberName[I]));
        End;
        ObjClass := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'class_inventory.csv');
    Rpt.Free;
End;

Procedure ExportStackDetails(Board : IPCB_Board; BasePath : String);
Var
    Rpt       : TStringList;
    LayerObj  : IPCB_LayerObject;
    Layer     : TLayer;
    DielectricHeight : String;
    DielectricEr : String;
Begin
    Rpt := TStringList.Create;
    Rpt.Add('layer_name,copper_thickness_raw,dielectric_height_raw,dielectric_er');
    For Layer := eTopLayer To eBottomLayer Do
    Begin
        LayerObj := Board.LayerStack.LayerObject[Layer];
        If LayerObj <> Nil Then
            If LayerObj.IsInLayerStack Then
            Begin
                DielectricHeight := '';
                DielectricEr := '';
                If LayerObj.Dielectric <> Nil Then
                Begin
                    DielectricHeight := IntToStr(LayerObj.Dielectric.DielectricHeight);
                    DielectricEr := InvariantFloat(LayerObj.Dielectric.DielectricConstant);
                End;
                Rpt.Add(CsvQuote(LayerObj.Name) + ',' +
                    IntToStr(LayerObj.CopperThickness) + ',' +
                    DielectricHeight + ',' + CsvQuote(DielectricEr));
            End;
    End;
    Rpt.SaveToFile(BasePath + 'layer_stack_detail.csv');
    Rpt.Free;
End;

Procedure ExportNativeAudit;
Var
    Board    : IPCB_Board;
    BasePath : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('EVT System Carrier audit: no active PCB document.');
        Exit;
    End;

    { In AD26 Board.IsLibrary is true for the focused .PcbDoc as well. }
    If UpperCase(ExtractFileExt(Board.FileName)) = '.PCBLIB' Then
    Begin
        ShowMessage('EVT System Carrier audit: active document is a PCB library, not a PcbDoc.');
        Exit;
    End;

    BasePath := ExtractFilePath(Board.FileName) + 'equivalence\';
    ForceDirectories(BasePath);

    ExportComponents(Board, BasePath);
    ExportNets(Board, BasePath);
    ExportRules(Board, BasePath);
    ExportRuleConstraints(Board, BasePath);
    ExportPadNets(Board, BasePath);
    ExportLayerStack(Board, BasePath);
    ExportMechanical(Board, BasePath);
    ExportPairsAndClasses(Board, BasePath);
    ExportStackDetails(Board, BasePath);

    ShowMessage(
        'EVT System Carrier native audit exported to:' + #13#10 +
        BasePath
    );
End;
