{ Apply the EVT routing contracts to the active PcbDoc.
  Repeated runs add missing named rules and set the two differential-pair rules.
  Run procedure: ApplyEVTRules
}

Function EVTHasRule(Board : IPCB_Board; RuleName : String) : Boolean;
Var
    Iterator : IPCB_BoardIterator;
    Rule     : IPCB_Rule;
Begin
    Result := False;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Rule := Iterator.FirstPCBObject;
    While Rule <> Nil Do
    Begin
        If UpperCase(Rule.Name) = UpperCase(RuleName) Then
            Result := True;
        Rule := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function EVTCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function EVTFindDiffRule(Board : IPCB_Board; RuleName : String) : IPCB_DifferentialPairsRoutingRule;
Var
    Iterator : IPCB_BoardIterator;
    Rule     : IPCB_DifferentialPairsRoutingRule;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Rule := Iterator.FirstPCBObject;
    While Rule <> Nil Do
    Begin
        If (Rule.RuleKind = eRule_DifferentialPairsRouting) And
           (UpperCase(Rule.Name) = UpperCase(RuleName)) Then
            Result := Rule;
        Rule := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure EVTSetDiffRule(Board : IPCB_Board; RuleName, Scope1,
                         MinWidthText, PreferredWidthText, MaxWidthText,
                         MinGapText, PreferredGapText, MaxGapText : String);
Var
    Rule : IPCB_DifferentialPairsRoutingRule;
    L    : TLayer;
Begin
    Rule := EVTFindDiffRule(Board, RuleName);
    If Rule = Nil Then
    Begin
        Rule := PCBServer.PCBRuleFactory(eRule_DifferentialPairsRouting);
        Rule.Name := RuleName;
        Board.AddPCBObject(Rule);
    End;
    Rule.Comment := 'EVT routing contract';
    Rule.Scope1Expression := Scope1;
    Rule.Scope2Expression := 'All';
    Rule.NetScope := eNetScope_AnyNet;
    Rule.LayerKind := eRuleLayerKind_SameLayer;
    For L := MinLayer To MaxLayer Do
    Begin
        Rule.MinWidth[L] := EVTCoord(MinWidthText);
        Rule.PreferedWidth[L] := EVTCoord(PreferredWidthText);
        Rule.MaxWidth[L] := EVTCoord(MaxWidthText);
        Rule.MinGap[L] := EVTCoord(MinGapText);
        Rule.PreferedGap[L] := EVTCoord(PreferredGapText);
        Rule.MaxGap[L] := EVTCoord(MaxGapText);
    End;
End;

Function EVTAddWidth(Board : IPCB_Board; RuleName, Scope1, MinText,
                     PreferredText, MaxText : String) : Boolean;
Var
    Rule : IPCB_MaxMinWidthConstraint;
    L    : TLayer;
Begin
    Result := False;
    If EVTHasRule(Board, RuleName) Then Exit;

    Rule := PCBServer.PCBRuleFactory(eRule_MaxMinWidth);
    Rule.Name := RuleName;
    Rule.Comment := 'EVT routing contract';
    Rule.Scope1Expression := Scope1;
    Rule.Scope2Expression := 'All';
    Rule.NetScope := eNetScope_AnyNet;
    Rule.LayerKind := eRuleLayerKind_SameLayer;
    For L := MinLayer To MaxLayer Do
    Begin
        Rule.MinWidth[L] := EVTCoord(MinText);
        Rule.FavoredWidth[L] := EVTCoord(PreferredText);
        Rule.MaxWidth[L] := EVTCoord(MaxText);
    End;
    Board.AddPCBObject(Rule);
    Result := True;
End;

Function EVTAddClearance(Board : IPCB_Board; RuleName, Scope1,
                         Scope2, GapText : String) : Boolean;
Var
    Rule : IPCB_ClearanceConstraint;
Begin
    Result := False;
    If EVTHasRule(Board, RuleName) Then Exit;

    Rule := PCBServer.PCBRuleFactory(eRule_Clearance);
    Rule.Name := RuleName;
    Rule.Comment := 'EVT routing contract';
    Rule.Scope1Expression := Scope1;
    Rule.Scope2Expression := Scope2;
    Rule.NetScope := eNetScope_DifferentNetsOnly;
    Rule.LayerKind := eRuleLayerKind_SameLayer;
    Rule.Gap := EVTCoord(GapText);
    Board.AddPCBObject(Rule);
    Result := True;
End;

Procedure ApplyEVTRules;
Var
    Board : IPCB_Board;
    Added : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('ApplyEVTRules: no active PCB document.');
        Exit;
    End;
    If UpperCase(ExtractFileExt(Board.FileName)) <> '.PCBDOC' Then
    Begin
        ShowMessage('ApplyEVTRules: select the EVT PcbDoc first.');
        Exit;
    End;

    Added := 0;
    PCBServer.PreProcess;
    { Add general clearance first, so the two scoped clearances take priority. }
    If EVTAddClearance(Board, 'R_GENERAL_CLEARANCE', 'All', 'All', '0.20mm') Then Inc(Added);
    If EVTAddClearance(Board, 'R_ETH_MDI_CLEARANCE',
            'InDifferentialPairClass(''DP_ETH_MDI'')',
            'Not InDifferentialPairClass(''DP_ETH_MDI'')', '0.20mm') Then Inc(Added);
    If EVTAddClearance(Board, 'R_TIMING_TO_SW_CLEARANCE',
            'InNetClass(''NC_TIMING'')', 'InNet(''BUCK_SW'')', '1.00mm') Then Inc(Added);
    If EVTAddWidth(Board, 'R_3V3_TRUNK_WIDTH', 'InNet(''3V3'')',
            '1.50mm', '1.50mm', '3.00mm') Then Inc(Added);
    EVTSetDiffRule(Board, 'R_ETH_MDI_DIFF',
            'InDifferentialPairClass(''DP_ETH_MDI'')',
            '0.26mm', '0.26mm', '0.26mm',
            '0.20mm', '0.20mm', '0.20mm');
    EVTSetDiffRule(Board, 'R_CAN_DIFF',
            'InDifferentialPairClass(''DP_CAN'')',
            '0.20mm', '0.20mm', '0.30mm',
            '0.20mm', '0.20mm', '0.30mm');
    PCBServer.PostProcess;

    ShowMessage('ApplyEVTRules: added ' + IntToStr(Added) +
                ' width/clearance rules and configured two pair rules. Save and audit the PcbDoc.');
End;
