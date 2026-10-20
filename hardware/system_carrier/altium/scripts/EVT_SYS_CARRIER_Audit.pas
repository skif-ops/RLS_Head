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
            FloatToStr(CoordToMils(Component.X)) + ',' +
            FloatToStr(CoordToMils(Component.Y))
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
    ExportPadNets(Board, BasePath);
    ExportLayerStack(Board, BasePath);

    ShowMessage(
        'EVT System Carrier native audit exported to:' + #13#10 +
        BasePath
    );
End;
