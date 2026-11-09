{ Repair and apply the independently checked U9 power-closure candidate. }

Function PCBCCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function PCBCandidateBoard(Board : IPCB_Board) : Boolean;
Var
    P : String;
Begin
    Result := False;
    If Board = Nil Then Exit;
    P := LowerCase(Board.FileName);
    Result :=
        (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (UpperCase(ExtractFileName(Board.FileName)) =
         'EVT_SYS_CARRIER_PHYSICAL_CLOSURE_CANDIDATE.PCBDOC');
End;

Function PCFindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
Var
    Iterator : IPCB_BoardIterator;
    NetObj   : IPCB_Net;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eNetObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    NetObj := Iterator.FirstPCBObject;
    While NetObj <> Nil Do
    Begin
        If UpperCase(NetObj.Name) = UpperCase(NetName) Then
        Begin
            Result := NetObj;
            Break;
        End;
        NetObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PCAddTrack(Board : IPCB_Board;
                     NetName, X1Text, Y1Text, X2Text, Y2Text, WidthText : String;
                     LayerValue : TLayer; Var Count : Integer);
Var
    TrackObj : IPCB_Track;
    NetObj   : IPCB_Net;
Begin
    NetObj := PCFindNet(Board, NetName);
    If NetObj = Nil Then Exit;

    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    TrackObj.X1 := PCBCCoord(X1Text);
    TrackObj.Y1 := PCBCCoord(Y1Text);
    TrackObj.X2 := PCBCCoord(X2Text);
    TrackObj.Y2 := PCBCCoord(Y2Text);
    TrackObj.Width := PCBCCoord(WidthText);
    TrackObj.Layer := LayerValue;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure PCRemoveFirstRadarRoute(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(MkSet(eBottomLayer));
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And
           (TrackObj.Net <> Nil) And
           (UpperCase(TrackObj.Net.Name) = 'RADAR_12V') And
           (TrackObj.Width = PCBCCoord('0.60mm')) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PCAddVia(Board : IPCB_Board; NetName, XText, YText : String;
                   Var Count : Integer);
Var
    ViaObj : IPCB_Via;
    NetObj : IPCB_Net;
Begin
    NetObj := PCFindNet(Board, NetName);
    If NetObj = Nil Then Exit;

    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := PCBCCoord(XText);
    ViaObj.Y := PCBCCoord(YText);
    ViaObj.Size := PCBCCoord('0.50mm');
    ViaObj.HoleSize := PCBCCoord('0.20mm');
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := eBottomLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Procedure PCRemoveU9Tracks(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
    NetName   : String;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) Then
        Begin
            NetName := UpperCase(TrackObj.Net.Name);
            If (NetName = 'VIN_PROTECTED') Or
               (NetName = 'BUCK5_SW') Or
               (NetName = '5V_GNSS') Then
            Begin
                Board.RemovePCBObject(TrackObj);
                Inc(Count);
            End;
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function PCViaMatches(ViaObj : IPCB_Via; XText, YText : String) : Boolean;
Begin
    Result := (ViaObj.X = PCBCCoord(XText)) And
              (ViaObj.Y = PCBCCoord(YText));
End;

Procedure PCRemoveU9Vias(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (PCViaMatches(ViaObj, '16mm', '53.025mm')) Or
           (PCViaMatches(ViaObj, '17mm', '59.225mm')) Or
           (PCViaMatches(ViaObj, '21mm', '51.275mm')) Or
           (PCViaMatches(ViaObj, '24.5mm', '55.325mm')) Or
           (PCViaMatches(ViaObj, '20.25mm', '60.5mm')) Or
           (PCViaMatches(ViaObj, '21mm', '61.5mm')) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Function PCLocalNet(NetName : String) : Boolean;
Var
    N : String;
Begin
    N := UpperCase(NetName);
    Result :=
        (N = 'U5_PG') Or (N = 'U5_SS_LOCAL') Or
        (N = 'U6_DVDT') Or (N = 'U6_ILIM_LOCAL') Or
        (N = 'U6_OVLO_LOCAL') Or (N = 'U6_UVLO_LOCAL') Or
        (N = 'U7_DVDT') Or (N = 'U7_ILIM_LOCAL') Or
        (N = 'U7_OVLO_LOCAL') Or (N = 'U7_UVLO_LOCAL') Or
        (N = 'U9_PG') Or (N = 'U9_SS_LOCAL') Or
        (N = 'VCAP1_LOCAL') Or (N = 'VCAP2_LOCAL') Or
        (N = 'SYS_EFUSE_FLT') Or (N = 'SHDN_PD') Or (N = 'STB_PD') Or
        (N = 'VDDA_FILTERED') Or (N = 'RADAR_EFUSE_FLT');
End;

Procedure PCRemoveLocalTracks(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) And
           PCLocalNet(TrackObj.Net.Name) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PCRemoveLocalVias(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And PCLocalNet(ViaObj.Net.Name) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PCRemoveSWDIOTerminalTracks(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator  : IPCB_BoardIterator;
    TrackObj  : IPCB_Track;
    NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) And
           (UpperCase(TrackObj.Net.Name) = 'SWDIO') And
           (((TrackObj.X1 > PCBCCoord('64mm')) And (TrackObj.Y1 > PCBCCoord('43mm'))) Or
            ((TrackObj.X2 > PCBCCoord('64mm')) And (TrackObj.Y2 > PCBCCoord('43mm')))) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PCRemoveSWDIOTerminalVia(Board : IPCB_Board; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj   : IPCB_Via;
    NextVia  : IPCB_Via;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And (UpperCase(ViaObj.Net.Name) = 'SWDIO') And
           (ViaObj.Y > PCBCCoord('43mm')) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyL4Relocation;
Var
    Board         : IPCB_Board;
    AddedTracks   : Integer;
    AddedVias     : Integer;
    RemovedTracks : Integer;
    RemovedVias   : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Not PCBCandidateBoard(Board) Then
    Begin
        ShowMessage('Physical closure stopped: select EVT_SYS_CARRIER_physical_closure_candidate.PcbDoc.');
        Exit;
    End;

    AddedTracks := 0;
    AddedVias := 0;
    RemovedTracks := 0;
    RemovedVias := 0;
    PCBServer.PreProcess;
    Try
        PCRemoveU9Tracks(Board, RemovedTracks);
        PCRemoveU9Vias(Board, RemovedVias);
        PCRemoveLocalTracks(Board, RemovedTracks);
        PCRemoveLocalVias(Board, RemovedVias);
        PCRemoveSWDIOTerminalTracks(Board, RemovedTracks);
        PCRemoveSWDIOTerminalVia(Board, RemovedVias);

        { VIN_PROTECTED: main bottom copper to C90, then Mid-Layer 2 to C93. }
        PCAddTrack(Board, 'VIN_PROTECTED', '30mm', '22mm', '2mm', '22mm',
                   '0.60mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '2mm', '22mm', '2mm', '50mm',
                   '0.60mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '2mm', '50mm', '16mm', '50mm',
                   '0.60mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '16mm', '50mm', '16mm', '53.025mm',
                   '0.60mm', eBottomLayer, AddedTracks);
        PCAddVia(Board, 'VIN_PROTECTED', '16mm', '53.025mm', AddedVias);
        PCAddTrack(Board, 'VIN_PROTECTED', '16mm', '53.025mm', '17mm', '59.225mm',
                   '0.50mm', eMidLayer2, AddedTracks);
        PCAddVia(Board, 'VIN_PROTECTED', '17mm', '59.225mm', AddedVias);
        PCAddVia(Board, 'VIN_PROTECTED', '21mm', '61.5mm', AddedVias);
        PCAddTrack(Board, 'VIN_PROTECTED', '17mm', '59.225mm', '17mm', '63mm',
                   '0.50mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '17mm', '63mm', '21mm', '63mm',
                   '0.50mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '21mm', '63mm', '21mm', '61.5mm',
                   '0.50mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '21mm', '61.5mm', '20.75mm', '58.4625mm',
                   '0.25mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '20.75mm', '58.4625mm', '21.4625mm', '57.75mm',
                   '0.25mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VIN_PROTECTED', '21.4625mm', '57.75mm', '21.4625mm', '56.75mm',
                   '0.25mm', eTopLayer, AddedTracks);

        { BUCK5_SW: leave the small pads narrowly, then widen in free space. }
        PCAddTrack(Board, 'BUCK5_SW', '18.5375mm', '56.75mm', '18.5375mm', '57.75mm',
                   '0.25mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'BUCK5_SW', '18.5375mm', '57.75mm', '18.2mm', '58.2mm',
                   '0.25mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'BUCK5_SW', '18.2mm', '58.2mm', '18.2mm', '63mm',
                   '0.80mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'BUCK5_SW', '18.2mm', '63mm', '26.815mm', '63mm',
                   '0.80mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'BUCK5_SW', '26.815mm', '63mm', '26.815mm', '57mm',
                   '0.80mm', eTopLayer, AddedTracks);

        { 5V_GNSS: J8/C91 branch, bottom crossover, R90/L9 and U9 branch. }
        PCAddTrack(Board, '5V_GNSS', '3.15mm', '53.875mm', '3.15mm', '49.5mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '3.15mm', '49.5mm', '19mm', '49.5mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '19mm', '49.5mm', '21mm', '51.275mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddVia(Board, '5V_GNSS', '21mm', '51.275mm', AddedVias);
        PCAddVia(Board, '5V_GNSS', '24.5mm', '55.325mm', AddedVias);
        PCAddTrack(Board, '5V_GNSS', '21mm', '51.275mm', '24.5mm', '55.325mm',
                   '0.50mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '24.5mm', '55.325mm', '25mm', '54.5mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '25mm', '54.5mm', '29.185mm', '54.5mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '29.185mm', '54.5mm', '29.185mm', '57mm',
                   '0.50mm', eTopLayer, AddedTracks);
        PCAddVia(Board, '5V_GNSS', '20.25mm', '60.5mm', AddedVias);
        PCAddTrack(Board, '5V_GNSS', '20.25mm', '58.4625mm', '20.25mm', '60.5mm',
                   '0.25mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, '5V_GNSS', '20.25mm', '60.5mm', '24.5mm', '55.325mm',
                   '0.50mm', eMidLayer2, AddedTracks);

        { Top Layer local routes planned against the exported physical geometry. }
        PCAddTrack(Board, 'U5_PG', '35.4625mm', '14.75mm', '37mm', '16.675mm',
                   '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U5_SS_LOCAL', '32.5375mm', '14.75mm', '33mm', '17.1mm',
                   '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U5_SS_LOCAL', '33mm', '17.1mm', '33.225mm', '17.5mm',
                   '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'U6_DVDT', '22.725mm', '13.125mm', '23.9mm', '13.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_DVDT', '23.9mm', '13.2mm', '24.9mm', '14.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_DVDT', '24.9mm', '14.2mm', '25mm', '14.6mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_DVDT', '25mm', '14.6mm', '24.9mm', '14.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_DVDT', '24.9mm', '14.8mm', '23.2mm', '16.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_DVDT', '23.2mm', '16.2mm', '22mm', '16.725mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'U6_OVLO_LOCAL', '20.71mm', '14.225mm', '19mm', '13mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '19mm', '13mm', '19.9mm', '16.1mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '19.9mm', '16.1mm', '21.3mm', '17.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '21.3mm', '17.5mm', '22.7mm', '17.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '22.7mm', '17.5mm', '24.7mm', '15.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '24.7mm', '15.5mm', '25.3mm', '15mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '25.3mm', '15mm', '25.4mm', '14.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '25.4mm', '14.8mm', '25.4mm', '14.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '25.4mm', '14.2mm', '25.3mm', '14mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '25.3mm', '14mm', '23.4mm', '12.1mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '23.4mm', '12.1mm', '23.3mm', '12.1mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '23.3mm', '12.1mm', '22mm', '11.325mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U6_OVLO_LOCAL', '22mm', '11.325mm', '24mm', '9.675mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'SYS_EFUSE_FLT', '21.275mm', '13.125mm', '20.098mm', '12.891mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SYS_EFUSE_FLT', '20.098mm', '12.891mm', AddedVias);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '25mm', '16.675mm', '24.434mm', '17.241mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SYS_EFUSE_FLT', '24.434mm', '17.241mm', AddedVias);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '39.325mm', '50.75mm', '38.54mm', '50.906mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SYS_EFUSE_FLT', '38.54mm', '50.906mm', AddedVias);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '20.098mm', '12.891mm', '19.6mm', '14.8mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '19.6mm', '14.8mm', '20.2mm', '15.4mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '20.2mm', '15.4mm', '23mm', '13.6mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '23mm', '13.6mm', '23.4mm', '13.2mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '23.4mm', '13.2mm', '24mm', '13.2mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '24mm', '13.2mm', '25mm', '14.4mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '25mm', '14.4mm', '24.434mm', '17.241mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '24.434mm', '17.241mm', '24mm', '18.4mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '24mm', '18.4mm', '24mm', '30mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SYS_EFUSE_FLT', '24mm', '30mm', '38.54mm', '50.906mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'SHDN_PD', '72.4mm', '28.025mm', '72.844mm', '27.36mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SHDN_PD', '72.844mm', '27.36mm', AddedVias);
        PCAddTrack(Board, 'SHDN_PD', '77.5mm', '37.275mm', '76.7mm', '37.275mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SHDN_PD', '76.7mm', '37.275mm', AddedVias);
        PCAddTrack(Board, 'SHDN_PD', '72.844mm', '27.36mm', '72.8mm', '29.8mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'SHDN_PD', '72.8mm', '29.8mm', '76.7mm', '37.275mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'STB_PD', '72.4mm', '29.975mm', '72.974mm', '31.361mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'STB_PD', '72.974mm', '31.361mm', AddedVias);
        PCAddTrack(Board, 'STB_PD', '77.175mm', '34mm', '76.375mm', '34mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'STB_PD', '76.375mm', '34mm', AddedVias);
        PCAddTrack(Board, 'STB_PD', '72.974mm', '31.361mm', '76.2mm', '37.6mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'STB_PD', '76.2mm', '37.6mm', '76.6mm', '38mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'STB_PD', '76.6mm', '38mm', '77mm', '37.8mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'STB_PD', '77mm', '37.8mm', '77.4mm', '37.4mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'STB_PD', '77.4mm', '37.4mm', '76.375mm', '34mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'VDDA_FILTERED', '39.325mm', '32.250mm', '39.325mm', '31.750mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '39.325mm', '32.250mm', '38.540mm', '32.094mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'VDDA_FILTERED', '38.540mm', '32.094mm', AddedVias);
        PCAddTrack(Board, 'VDDA_FILTERED', '68.500mm', '34.725mm', '69.066mm', '35.291mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'VDDA_FILTERED', '69.066mm', '35.291mm', AddedVias);
        PCAddTrack(Board, 'VDDA_FILTERED', '67.500mm', '38.020mm', '67.944mm', '37.355mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'VDDA_FILTERED', '67.944mm', '37.355mm', AddedVias);
        PCAddTrack(Board, 'VDDA_FILTERED', '69.000mm', '40.787mm', '68.261mm', '40.481mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'VDDA_FILTERED', '68.261mm', '40.481mm', AddedVias);
        PCAddTrack(Board, 'VDDA_FILTERED', '38.540mm', '32.094mm', '68.800mm', '26.400mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '68.800mm', '26.400mm', '71.200mm', '27.600mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '71.200mm', '27.600mm', '71.600mm', '28.000mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '71.600mm', '28.000mm', '72.400mm', '28.800mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '72.400mm', '28.800mm', '71.600mm', '32.000mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '71.600mm', '32.000mm', '69.066mm', '35.291mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '69.066mm', '35.291mm', '67.944mm', '37.355mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'VDDA_FILTERED', '67.944mm', '37.355mm', '68.261mm', '40.481mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '61.275mm', '13.125mm', '60.098mm', '12.891mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'RADAR_EFUSE_FLT', '60.098mm', '12.891mm', AddedVias);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '65.000mm', '16.675mm', '64.434mm', '17.241mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'RADAR_EFUSE_FLT', '64.434mm', '17.241mm', AddedVias);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '60.098mm', '12.891mm', '57.000mm', '18.600mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '57.000mm', '18.600mm', '57.600mm', '19.200mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '57.600mm', '19.200mm', '60.200mm', '20.000mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '60.200mm', '20.000mm', '64.200mm', '17.200mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '64.200mm', '17.200mm', '64.434mm', '17.241mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '39.325mm', '50.250mm', '37.125mm', '50.250mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'RADAR_EFUSE_FLT', '37.125mm', '50.250mm', AddedVias);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '65.000mm', '16.675mm', '64.434mm', '16.109mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'RADAR_EFUSE_FLT', '64.434mm', '16.109mm', AddedVias);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '37.125mm', '50.250mm', '56.400mm', '24.600mm', '0.20mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '56.400mm', '24.600mm', '59.600mm', '23.400mm', '0.20mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '59.600mm', '23.400mm', '61.800mm', '21.200mm', '0.20mm', eBottomLayer, AddedTracks);
        PCAddVia(Board, 'RADAR_EFUSE_FLT', '61.800mm', '21.200mm', AddedVias);
        PCAddTrack(Board, 'RADAR_EFUSE_FLT', '61.800mm', '21.200mm', '64.434mm', '16.109mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'U7_UVLO_LOCAL', '61.275mm', '14.875mm', '59mm', '16mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_UVLO_LOCAL', '59mm', '16mm', '59mm', '12.9mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_UVLO_LOCAL', '59mm', '12.9mm', '60.825mm', '9.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_UVLO_LOCAL', '60.825mm', '9.5mm', '61.1mm', '8.4mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_UVLO_LOCAL', '61.1mm', '8.4mm', '61.7mm', '7.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_UVLO_LOCAL', '61.7mm', '7.8mm', '62mm', '7.675mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'U7_DVDT', '62.725mm', '13.125mm', '63.9mm', '13.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '63.9mm', '13.2mm', '64.9mm', '14.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '64.9mm', '14.2mm', '65.8mm', '16mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '65.8mm', '16mm', '65.8mm', '19mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '65.8mm', '19mm', '65.6mm', '19.3mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '65.6mm', '19.3mm', '65.3mm', '19.6mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '65.3mm', '19.6mm', '65mm', '19.7mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '65mm', '19.7mm', '63.7mm', '19.7mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '63.7mm', '19.7mm', '62.8mm', '18.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '62.8mm', '18.5mm', '62.8mm', '17.6mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '62.8mm', '17.6mm', '62mm', '16.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U7_DVDT', '62mm', '16.8mm', '62mm', '16.725mm', '0.20mm', eTopLayer, AddedTracks);

        { L3 trunks use via locations checked against all copper layers. }
        PCAddTrack(Board, 'U6_UVLO_LOCAL', '21.275mm', '14.875mm', '20.294mm', '14.680mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U6_UVLO_LOCAL', '20.294mm', '14.680mm', AddedVias);
        PCAddTrack(Board, 'U6_UVLO_LOCAL', '20.825mm', '10.5mm', '21.391mm', '9.934mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U6_UVLO_LOCAL', '21.391mm', '9.934mm', AddedVias);
        PCAddTrack(Board, 'U6_UVLO_LOCAL', '20.294mm', '14.680mm', '21.2mm', '11.8mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'U6_UVLO_LOCAL', '21.2mm', '11.8mm', '21.391mm', '9.934mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'U6_UVLO_LOCAL', '20.825mm', '10.5mm', '22mm', '9.675mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'U6_ILIM_LOCAL', '22.9mm', '14.225mm', '24.371mm', '14.518mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U6_ILIM_LOCAL', '24.371mm', '14.518mm', AddedVias);
        PCAddTrack(Board, 'U6_ILIM_LOCAL', '18.175mm', '17.5mm', '17.375mm', '17.5mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U6_ILIM_LOCAL', '17.375mm', '17.5mm', AddedVias);
        PCAddTrack(Board, 'U6_ILIM_LOCAL', '24.371mm', '14.518mm', '22mm', '15.2mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'U6_ILIM_LOCAL', '22mm', '15.2mm', '17.375mm', '17.5mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'U7_OVLO_LOCAL', '61.1mm', '14.225mm', '60.315mm', '14.381mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U7_OVLO_LOCAL', '60.315mm', '14.381mm', AddedVias);
        PCAddTrack(Board, 'U7_OVLO_LOCAL', '62mm', '9.325mm', '61.694mm', '8.586mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U7_OVLO_LOCAL', '61.694mm', '8.586mm', AddedVias);
        PCAddTrack(Board, 'U7_OVLO_LOCAL', '60.315mm', '14.381mm', '61.694mm', '8.586mm', '0.20mm', eMidLayer2, AddedTracks);
        PCAddTrack(Board, 'U7_OVLO_LOCAL', '62mm', '9.325mm', '64mm', '9.675mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'U7_ILIM_LOCAL', '62.9mm', '14.225mm', '64.371mm', '14.518mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U7_ILIM_LOCAL', '64.371mm', '14.518mm', AddedVias);
        PCAddTrack(Board, 'U7_ILIM_LOCAL', '58.175mm', '17.5mm', '60.013mm', '19.338mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U7_ILIM_LOCAL', '60.013mm', '19.338mm', AddedVias);
        PCAddTrack(Board, 'U7_ILIM_LOCAL', '64.371mm', '14.518mm', '60.013mm', '19.338mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'U9_PG', '18.5375mm', '56.25mm', '17.753mm', '56.094mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U9_PG', '17.753mm', '56.094mm', AddedVias);
        PCAddTrack(Board, 'U9_PG', '24.5mm', '53.675mm', '23.761mm', '53.369mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'U9_PG', '23.761mm', '53.369mm', AddedVias);
        PCAddTrack(Board, 'U9_PG', '17.753mm', '56.094mm', '23.761mm', '53.369mm', '0.20mm', eMidLayer2, AddedTracks);

        PCAddTrack(Board, 'U9_SS_LOCAL', '21.4625mm', '56.25mm', '22.1mm', '56.3mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U9_SS_LOCAL', '22.1mm', '56.3mm', '22.2mm', '56.4mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U9_SS_LOCAL', '22.2mm', '56.4mm', '22.2mm', '58.9mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'U9_SS_LOCAL', '22.2mm', '58.9mm', '22mm', '59.225mm', '0.20mm', eTopLayer, AddedTracks);

        PCAddTrack(Board, 'VCAP1_LOCAL', '58.5mm', '23.725mm', '58.5mm', '23.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP1_LOCAL', '58.5mm', '23.8mm', '59.3mm', '24.6mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP1_LOCAL', '59.3mm', '24.6mm', '59.3mm', '27.2mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP1_LOCAL', '59.3mm', '27.2mm', '59.25mm', '27.325mm', '0.20mm', eTopLayer, AddedTracks);

        { Move the SWDIO terminal via outside U1 while preserving the IMU_DRDY corridor. }
        PCAddTrack(Board, 'SWDIO', '64.675mm', '46.75mm', '65.8mm', '46.75mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddVia(Board, 'SWDIO', '65.8mm', '46.75mm', AddedVias);
        PCAddTrack(Board, 'SWDIO', '62.4mm', '43.4mm', '65.8mm', '46.75mm', '0.20mm', eBottomLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP2_LOCAL', '66.725mm', '46mm', '66.725mm', '47.8mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP2_LOCAL', '66.725mm', '47.8mm', '65.5mm', '47.25mm', '0.20mm', eTopLayer, AddedTracks);
        PCAddTrack(Board, 'VCAP2_LOCAL', '65.5mm', '47.25mm', '64.675mm', '47.25mm', '0.20mm', eTopLayer, AddedTracks);

        Board.ConnectivelyValidateNets;
        Board.NewUndo;
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Action', 'Redraw');
    RunProcess('PCB:Zoom');
    ShowMessage('Power and local closure applied. Removed tracks: ' +
                IntToStr(RemovedTracks) + '; removed vias: ' +
                IntToStr(RemovedVias) + '; added tracks: ' +
                IntToStr(AddedTracks) + '; vias: ' + IntToStr(AddedVias) +
                '. Save, repour polygons and run full DRC.');
End;
