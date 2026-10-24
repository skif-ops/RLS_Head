{ Bind the locked EVT differential-pair and timing classes to native PCB nets.
  Run ApplyEVTClasses with EVT_SYS_CARRIER.PcbDoc active.
}

Function EVTClassNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
Var
    Iterator : IPCB_BoardIterator;
    Net      : IPCB_Net;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eNetObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Net := Iterator.FirstPCBObject;
    While Net <> Nil Do
    Begin
        If UpperCase(Net.Name) = UpperCase(NetName) Then
            Result := Net;
        Net := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function EVTClassPair(Board : IPCB_Board; PairName : String) : IPCB_DifferentialPair;
Var
    Iterator : IPCB_BoardIterator;
    PairObj  : IPCB_DifferentialPair;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eDifferentialPairObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    PairObj := Iterator.FirstPCBObject;
    While PairObj <> Nil Do
    Begin
        If UpperCase(PairObj.Name) = UpperCase(PairName) Then
            Result := PairObj;
        PairObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function EVTHasClass(Board : IPCB_Board; ClassName : String) : Boolean;
Var
    Iterator : IPCB_BoardIterator;
    ObjClass : IPCB_ObjectClass;
Begin
    Result := False;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eClassObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ObjClass := Iterator.FirstPCBObject;
    While ObjClass <> Nil Do
    Begin
        If UpperCase(ObjClass.Name) = UpperCase(ClassName) Then
            Result := True;
        ObjClass := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function EVTHasClassMember(ObjClass : IPCB_ObjectClass;
                           MemberName : String) : Boolean;
Var
    I : Integer;
Begin
    Result := False;
    For I := 0 To 999 Do
    Begin
        If ObjClass.MemberName[I] = '' Then Exit;
        If UpperCase(ObjClass.MemberName[I]) = UpperCase(MemberName) Then
            Result := True;
    End;
End;

Procedure EVTBindPair(Board : IPCB_Board; PairName, PosName, NegName : String);
Var
    PairObj : IPCB_DifferentialPair;
Begin
    PairObj := EVTClassPair(Board, PairName);
    If PairObj = Nil Then
    Begin
        PairObj := PCBServer.PCBObjectFactory(eDifferentialPairObject,
                                              eNoDimension, eCreate_Default);
        PairObj.Name := PairName;
        PairObj.PositiveNet := EVTClassNet(Board, PosName);
        PairObj.NegativeNet := EVTClassNet(Board, NegName);
        Board.AddPCBObject(PairObj);
    End;
End;

Procedure EVTBindClass(Board : IPCB_Board; ClassName : String;
                       MemberKind : TClassMemberKind;
                       Member1, Member2, Member3 : String);
Var
    ObjClass : IPCB_ObjectClass;
Begin
    If EVTHasClass(Board, ClassName) Then Exit;
    ObjClass := PCBServer.PCBClassFactoryByClassMember(MemberKind);
    ObjClass.SuperClass := False;
    ObjClass.Name := ClassName;
    Board.AddPCBObject(ObjClass);
    If Not EVTHasClassMember(ObjClass, Member1) Then ObjClass.AddMemberByName(Member1);
    If (Member2 <> '') And (Not EVTHasClassMember(ObjClass, Member2)) Then
        ObjClass.AddMemberByName(Member2);
    If (Member3 <> '') And (Not EVTHasClassMember(ObjClass, Member3)) Then
        ObjClass.AddMemberByName(Member3);
End;

Procedure EVTBindNetClass(Board : IPCB_Board; ClassName, Members : String);
Var
    ObjClass : IPCB_ObjectClass;
Begin
    If EVTHasClass(Board, ClassName) Then Exit;
    ObjClass := PCBServer.PCBClassFactoryByClassMember(eClassMemberKind_Net);
    ObjClass.SuperClass := False;
    ObjClass.Name := ClassName;
    Board.AddPCBObject(ObjClass);
End;

Procedure EVTRepairClass(Board : IPCB_Board; ClassName, Members : String);
Var
    Iterator : IPCB_BoardIterator;
    ObjClass : IPCB_ObjectClass;
    Remaining : String;
    Item      : String;
    Sep       : Integer;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eClassObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ObjClass := Iterator.FirstPCBObject;
    While ObjClass <> Nil Do
    Begin
        If UpperCase(ObjClass.Name) = UpperCase(ClassName) Then
        Begin
            Remaining := Members;
            While Remaining <> '' Do
            Begin
                Sep := Pos(';', Remaining);
                If Sep = 0 Then
                Begin
                    Item := Remaining;
                    Remaining := '';
                End
                Else
                Begin
                    Item := Copy(Remaining, 1, Sep - 1);
                    Delete(Remaining, 1, Sep);
                End;
                If (Item <> '') And (Not EVTHasClassMember(ObjClass, Item)) Then
                    ObjClass.AddMemberByName(Item);
            End;
        End;
        ObjClass := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyEVTClasses;
Var
    Board : IPCB_Board;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    If UpperCase(ExtractFileExt(Board.FileName)) <> '.PCBDOC' Then Exit;
    If (EVTClassNet(Board, 'ETH_TXP') = Nil) Or
       (EVTClassNet(Board, 'ETH_TXN') = Nil) Or
       (EVTClassNet(Board, 'ETH_RXP') = Nil) Or
       (EVTClassNet(Board, 'ETH_RXN') = Nil) Or
       (EVTClassNet(Board, 'RADAR_CANH') = Nil) Or
       (EVTClassNet(Board, 'RADAR_CANL') = Nil) Or
       (EVTClassNet(Board, 'GNSS_PPS') = Nil) Or
       (EVTClassNet(Board, 'RADAR_REF') = Nil) Or
       (EVTClassNet(Board, 'IMU_DRDY') = Nil) Then
    Begin
        ShowMessage('EVT class binding: a required native net is missing.');
        Exit;
    End;

    PCBServer.PreProcess;
    EVTBindPair(Board, 'DP_ETH_TX', 'ETH_TXP', 'ETH_TXN');
    EVTBindPair(Board, 'DP_ETH_RX', 'ETH_RXP', 'ETH_RXN');
    EVTBindPair(Board, 'DP_CAN', 'RADAR_CANH', 'RADAR_CANL');
    EVTBindClass(Board, 'DP_ETH_MDI', eClassMemberKind_DifferentialPair,
                 'DP_ETH_TX', 'DP_ETH_RX', '');
    EVTBindClass(Board, 'DP_CAN', eClassMemberKind_DifferentialPair,
                 'DP_CAN', '', '');
    EVTBindNetClass(Board, 'NC_POWER_12V',
        'VIN_RAW;VIN_PROTECTED;RADAR_12V');
    EVTBindNetClass(Board, 'NC_POWER_3V3', '3V3;VDDA_FILTERED');
    EVTBindNetClass(Board, 'NC_ETH_MDI',
        'ETH_TXP;ETH_TXN;ETH_RXP;ETH_RXN');
    EVTBindNetClass(Board, 'NC_GNSS_RF', 'GNSS_RF');
    EVTBindNetClass(Board, 'NC_CAN', 'RADAR_CANH;RADAR_CANL');
    EVTBindNetClass(Board, 'NC_TIMING',
        'GNSS_PPS;RADAR_REF;IMU_DRDY');
    EVTBindNetClass(Board, 'NC_RMII',
        'ETH_50M;ETH_MDIO;ETH_MDC;ETH_CRS_DV;ETH_RXD0;ETH_RXD1;' +
        'ETH_TX_EN;ETH_TXD0;ETH_TXD1;ETH_NRST');
    EVTBindNetClass(Board, 'NC_IMU_SPI',
        'IMU_NSS;IMU_SCK;IMU_MISO;IMU_MOSI');
    EVTRepairClass(Board, 'DP_ETH_MDI', 'DP_ETH_TX;DP_ETH_RX');
    EVTRepairClass(Board, 'DP_CAN', 'DP_CAN');
    EVTRepairClass(Board, 'NC_POWER_12V',
        'VIN_RAW;VIN_PROTECTED;RADAR_12V');
    EVTRepairClass(Board, 'NC_POWER_3V3', '3V3;VDDA_FILTERED');
    EVTRepairClass(Board, 'NC_ETH_MDI',
        'ETH_TXP;ETH_TXN;ETH_RXP;ETH_RXN');
    EVTRepairClass(Board, 'NC_GNSS_RF', 'GNSS_RF');
    EVTRepairClass(Board, 'NC_CAN', 'RADAR_CANH;RADAR_CANL');
    EVTRepairClass(Board, 'NC_TIMING', 'GNSS_PPS;RADAR_REF;IMU_DRDY');
    EVTRepairClass(Board, 'NC_RMII',
        'ETH_50M;ETH_MDIO;ETH_MDC;ETH_CRS_DV;ETH_RXD0;ETH_RXD1;' +
        'ETH_TX_EN;ETH_TXD0;ETH_TXD1;ETH_NRST');
    EVTRepairClass(Board, 'NC_IMU_SPI',
        'IMU_NSS;IMU_SCK;IMU_MISO;IMU_MOSI');
    PCBServer.PostProcess;
    ShowMessage('EVT class binding applied. Save and audit pairs and classes.');
End;
