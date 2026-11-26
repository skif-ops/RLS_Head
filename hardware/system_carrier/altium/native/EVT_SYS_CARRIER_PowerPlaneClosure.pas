{ Apply the audited 3V3/GND plane fanout closure to the physical candidate. }

Function PPCCoord(ValueText : String) : TCoord;
Var
    UnitKind : TUnit;
Begin
    UnitKind := eMetric;
    StringToCoordUnit(ValueText, Result, UnitKind);
End;

Function PPCIsCandidate(Board : IPCB_Board) : Boolean;
Var
    P : String;
Begin
    Result := False;
    If Board = Nil Then Exit;
    P := LowerCase(Board.FileName);
    Result := (Pos('\hardware\system_carrier\altium\native\', P) > 0) And
        (UpperCase(ExtractFileName(Board.FileName)) =
         'EVT_SYS_CARRIER_PHYSICAL_CLOSURE_CANDIDATE.PCBDOC');
End;

Function PPCFindNet(Board : IPCB_Board; NetName : String) : IPCB_Net;
Var
    Iterator : IPCB_BoardIterator;
    NetObj : IPCB_Net;
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

Function PPCFind3V3Plane(Board : IPCB_Board) : IPCB_Polygon;
Var
    Iterator : IPCB_BoardIterator;
    PolyObj : IPCB_Polygon;
Begin
    Result := Nil;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePolyObject));
    Iterator.AddFilter_LayerSet(MkSet(eMidLayer2));
    Iterator.AddFilter_Method(eProcessAll);
    PolyObj := Iterator.FirstPCBObject;
    While PolyObj <> Nil Do
    Begin
        If UpperCase(PolyObj.Name) = 'EVT_3V3_L3_PLANE' Then
        Begin
            Result := PolyObj;
            Break;
        End;
        PolyObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PPCConfigure3V3Plane(Board : IPCB_Board; Rail : IPCB_Net;
                                Var PolygonObj : IPCB_Polygon;
                                Var Created : Boolean);
Var
    I : Integer;
Begin
    Board.BoardOutline.Invalidate;
    Board.BoardOutline.Rebuild;
    Board.BoardOutline.Validate;
    PolygonObj := PPCFind3V3Plane(Board);
    Created := PolygonObj = Nil;
    If Created Then
        PolygonObj := PCBServer.PCBObjectFactory(ePolyObject, eNoDimension, eCreate_Default)
    Else
        PolygonObj.BeginModify;
    PolygonObj.Name := 'EVT_3V3_L3_PLANE';
    PolygonObj.Layer := eMidLayer2;
    PolygonObj.Net := Rail;
    PolygonObj.PolygonType := eSignalLayerPolygon;
    PolygonObj.PolyHatchStyle := ePolySolid;
    PolygonObj.PourOver := ePolygonPourOver_None;
    PolygonObj.Grid := MMsToCoord(0.25);
    PolygonObj.TrackSize := MMsToCoord(0.25);
    PolygonObj.MinTrack := MMsToCoord(0.20);
    PolygonObj.BorderWidth := MMsToCoord(0.25);
    PolygonObj.ArcApproximation := MMsToCoord(0.05);
    PolygonObj.RemoveDead := False;
    PolygonObj.RemoveIslandsByArea := False;
    PolygonObj.RemoveNarrowNecks := False;
    PolygonObj.PointCount := Board.BoardOutline.PointCount;
    For I := 0 To Board.BoardOutline.PointCount - 1 Do
        PolygonObj.Segments[I] := Board.BoardOutline.Segments[I];
End;

Procedure PPCAddTrack(Board : IPCB_Board; NetName, X1Text, Y1Text,
                      X2Text, Y2Text, WidthText : String;
                      Var Count : Integer);
Var
    TrackObj : IPCB_Track;
    NetObj : IPCB_Net;
Begin
    NetObj := PPCFindNet(Board, NetName);
    If NetObj = Nil Then Exit;
    TrackObj := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    TrackObj.X1 := PPCCoord(X1Text);
    TrackObj.Y1 := PPCCoord(Y1Text);
    TrackObj.X2 := PPCCoord(X2Text);
    TrackObj.Y2 := PPCCoord(Y2Text);
    TrackObj.Width := PPCCoord(WidthText);
    TrackObj.Layer := eTopLayer;
    TrackObj.Net := NetObj;
    Board.AddPCBObject(TrackObj);
    Inc(Count);
End;

Procedure PPCAddVia(Board : IPCB_Board; NetName, XText, YText,
                    SizeText, HoleText : String; HighLayer : TLayer;
                    Var Count : Integer);
Var
    ViaObj : IPCB_Via;
    NetObj : IPCB_Net;
Begin
    NetObj := PPCFindNet(Board, NetName);
    If NetObj = Nil Then Exit;
    ViaObj := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    ViaObj.X := PPCCoord(XText);
    ViaObj.Y := PPCCoord(YText);
    ViaObj.Size := PPCCoord(SizeText);
    ViaObj.HoleSize := PPCCoord(HoleText);
    ViaObj.LowLayer := eTopLayer;
    ViaObj.HighLayer := HighLayer;
    ViaObj.Net := NetObj;
    Board.AddPCBObject(ViaObj);
    Inc(Count);
End;

Function PPCSameSegment(TrackObj : IPCB_Track; X1Text, Y1Text,
                        X2Text, Y2Text : String) : Boolean;
Begin
    Result := (((TrackObj.X1 = PPCCoord(X1Text)) And (TrackObj.Y1 = PPCCoord(Y1Text)) And
                (TrackObj.X2 = PPCCoord(X2Text)) And (TrackObj.Y2 = PPCCoord(Y2Text))) Or
               ((TrackObj.X1 = PPCCoord(X2Text)) And (TrackObj.Y1 = PPCCoord(Y2Text)) And
                (TrackObj.X2 = PPCCoord(X1Text)) And (TrackObj.Y2 = PPCCoord(Y1Text))));
End;

Procedure PPCRemoveTrack(Board : IPCB_Board; NetName, X1Text, Y1Text,
                         X2Text, Y2Text : String; Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    TrackObj, NextTrack : IPCB_Track;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(MkSet(eTopLayer));
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NextTrack := Iterator.NextPCBObject;
        If (TrackObj.Component = Nil) And (TrackObj.Net <> Nil) And
           (UpperCase(TrackObj.Net.Name) = UpperCase(NetName)) And
           PPCSameSegment(TrackObj, X1Text, Y1Text, X2Text, Y2Text) Then
        Begin
            Board.RemovePCBObject(TrackObj);
            Inc(Count);
        End;
        TrackObj := NextTrack;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure PPCRemoveVia(Board : IPCB_Board; NetName, XText, YText : String;
                       Var Count : Integer);
Var
    Iterator : IPCB_BoardIterator;
    ViaObj, NextVia : IPCB_Via;
Begin
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NextVia := Iterator.NextPCBObject;
        If (ViaObj.Net <> Nil) And
           (UpperCase(ViaObj.Net.Name) = UpperCase(NetName)) And
           (ViaObj.X = PPCCoord(XText)) And (ViaObj.Y = PPCCoord(YText)) Then
        Begin
            Board.RemovePCBObject(ViaObj);
            Inc(Count);
        End;
        ViaObj := NextVia;
    End;
    Board.BoardIterator_Destroy(Iterator);
End;

Procedure ApplyPowerPlaneClosure;
Var
    Board : IPCB_Board;
    Rail3V3 : IPCB_Net;
    PolygonObj : IPCB_Polygon;
    Created : Boolean;
    AddedTracks, AddedVias, RemovedTracks, RemovedVias : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Not PPCIsCandidate(Board) Then
    Begin
        ShowMessage('Power-plane closure stopped: select EVT_SYS_CARRIER_physical_closure_candidate.PcbDoc.');
        Exit;
    End;
    If Board.BoardOutline.PointCount < 3 Then
    Begin
        ShowMessage('Power-plane closure stopped: invalid board outline.');
        Exit;
    End;
    Rail3V3 := PPCFindNet(Board, '3V3');
    If (Rail3V3 = Nil) Or (PPCFindNet(Board, 'GND') = Nil) Then
    Begin
        ShowMessage('Power-plane closure stopped: 3V3 or GND net missing.');
        Exit;
    End;
    AddedTracks := 0; AddedVias := 0; RemovedTracks := 0; RemovedVias := 0;
    PPCConfigure3V3Plane(Board, Rail3V3, PolygonObj, Created);
    PCBServer.PreProcess;
    Try
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '52.675003mm', '55.250004mm', '51.450997mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '51.450997mm', '56.45mm', '51.450997mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '56.45mm', '51.450997mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '66.499994mm', '42.520006mm', '66.325mm', '42.043692mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '66.325mm', '42.043692mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '64.675004mm', '41.750005mm', '65.814197mm', '41.750005mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '65.814197mm', '41.750005mm', '65.814197mm', '41.907291mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '65.814197mm', '41.907291mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '39.324991mm', '43.750001mm', '37.875476mm', '43.787485mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '37.875476mm', '43.787485mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '59.749995mm', '27.32499mm', '59.799109mm', '25.375608mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '59.799109mm', '25.375608mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '63.999999mm', '54.019983mm', '63.999999mm', '53.569983mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '63.999999mm', '53.569983mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '52.675003mm', '55.250004mm', '51.450997mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '51.450997mm', '56.500728mm', '51.450997mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '56.500728mm', '51.450997mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '16.999991mm', '60.774986mm', '16.350472mm', '61.149986mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '16.350472mm', '61.149986mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '77.385012mm', '53.999994mm', '77.935012mm', '53.999994mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '77.935012mm', '53.999994mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '64.675004mm', '36.249991mm', '61.738149mm', '36.249991mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '61.738149mm', '36.249991mm', '61.738149mm', '33.461196mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '61.738149mm', '33.461196mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '64.675004mm', '41.750005mm', '65.814197mm', '41.750005mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '65.814197mm', '41.750005mm', '65.814197mm', '41.907291mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '65.814197mm', '41.907291mm', '66.224994mm', '42.043692mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '64.675004mm', '48.249992mm', '65.723507mm', '48.306035mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '65.723507mm', '48.306035mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '54.750005mm', '52.675003mm', '54.8mm', '53mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '54.8mm', '53mm', '54.8mm', '53.6mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '54.8mm', '53.6mm', '55mm', '53.8mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '55mm', '53.8mm', '55mm', '54mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '55mm', '54mm', '55.8mm', '54.8mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '55.8mm', '54.8mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '39.324991mm', '43.750001mm', '37.875476mm', '43.787485mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '37.875476mm', '43.787485mm', '37.500001mm', '44.070002mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '43.750001mm', '52.675003mm', '43.486497mm', '53.483127mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '43.486497mm', '53.483127mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '43.250002mm', '52.675003mm', '43.486497mm', '53.483127mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '39.324991mm', '39.750009mm', '38.275195mm', '39.729304mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '38.275195mm', '39.729304mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '43.250002mm', '27.32499mm', '43.250002mm', '28.544681mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '43.250002mm', '28.544681mm', '42.671337mm', '28.544681mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '42.671337mm', '28.544681mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '49.749989mm', '27.32499mm', '49.848898mm', '26.179251mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '49.848898mm', '26.179251mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '39.324991mm', '48.249992mm', '37.877058mm', '48.327385mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '37.877058mm', '48.327385mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '54.750005mm', '27.32499mm', '54.750005mm', '28.546569mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '54.750005mm', '28.546569mm', '54.484967mm', '28.546569mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '54.484967mm', '28.546569mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '59.749995mm', '27.32499mm', '59.85mm', '25.375608mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '59.85mm', '25.375608mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '51.499999mm', '59.262493mm', '51.6mm', '58.8mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '51.6mm', '58.8mm', '51.8mm', '58.6mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '51.8mm', '58.6mm', '52.4mm', '58.6mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '52.4mm', '58.6mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '53.012492mm', '58.749997mm', '53.191724mm', '59.162763mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '53.191724mm', '59.162763mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '69.599988mm', '28.675mm', '67.967579mm', '27.804515mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '67.967579mm', '27.804515mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '37.500001mm', '44.520002mm', '37.500001mm', '44.070002mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '37.500001mm', '44.070002mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '37.500001mm', '41.520008mm', '37.500001mm', '41.070008mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '37.500001mm', '41.070008mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '34.500007mm', '34.519997mm', '34.500007mm', '34.069997mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '34.500007mm', '34.069997mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '42.99999mm', '25.019991mm', '42.99999mm', '24.569991mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '42.99999mm', '24.569991mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '49.000004mm', '25.019991mm', '49.000004mm', '24.569991mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '49.000004mm', '24.569991mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '54.999992mm', '25.019991mm', '54.999992mm', '24.569991mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '54.999992mm', '24.569991mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '61.000005mm', '25.019991mm', '61.000005mm', '24.569991mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '61.000005mm', '24.569991mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '69.499988mm', '31.019979mm', '69.499988mm', '30.569979mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '69.499988mm', '30.569979mm', RemovedVias);
        PPCRemoveVia(Board, '3V3', '66.499994mm', '34.519997mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '66.499994mm', '42.520006mm', '66.224994mm', '42.043692mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '66.224994mm', '42.043692mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '71.999983mm', '50.175008mm', '71.999983mm', '49.725008mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '71.999983mm', '49.725008mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '63.999999mm', '54.019983mm', '63.999999mm', '53.75mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '63.999999mm', '53.75mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '54.999992mm', '54.020009mm', '55.4mm', '54.4mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '55.4mm', '54.4mm', '55.8mm', '54.8mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '47.000008mm', '54.019983mm', '48.000006mm', '54.599992mm', RemovedTracks);
        PPCRemoveTrack(Board, '3V3', '67.499992mm', '40.52001mm', '66.249992mm', '40.52001mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '66.249992mm', '40.52001mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '51.049987mm', '24.500002mm', '50.599987mm', '24.500002mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '50.599987mm', '24.500002mm', RemovedVias);
        PPCRemoveVia(Board, '3V3', '42.99999mm', '54.020009mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '49.000004mm', '61.019995mm', '49.000004mm', '60.569995mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '49.000004mm', '60.569995mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '51.224993mm', '62.000003mm', '50.774993mm', '62.000003mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '50.774993mm', '62.000003mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '54.999992mm', '61.019995mm', '54.999992mm', '60.569995mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '54.999992mm', '60.569995mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '76.999998mm', '24.919991mm', '76.999998mm', '24.469991mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '76.999998mm', '24.469991mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '68.999989mm', '39.212495mm', '68.999989mm', '38.762495mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '68.999989mm', '38.762495mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '50.635002mm', '3.72999mm', '50.836248mm', '3.327498mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '50.836248mm', '3.327498mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '72.000008mm', '53.175002mm', '72.000008mm', '52.725002mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '72.000008mm', '52.725002mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '63.999999mm', '6.325006mm', '65.749999mm', '6.325006mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '65.749999mm', '6.325006mm', RemovedVias);
        PPCRemoveTrack(Board, '3V3', '36.724996mm', '40.924988mm', '37.002593mm', '41.279163mm', RemovedTracks);
        PPCRemoveVia(Board, '3V3', '37.002593mm', '41.279163mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '64.675004mm', '35.749992mm', '64.2mm', '35.8mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '64.2mm', '35.8mm', '63.8mm', '35.8mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.8mm', '35.8mm', '63.6mm', '35.6mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.6mm', '35.6mm', '63.6mm', '35.2mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.6mm', '35.2mm', '63.4mm', '35mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.4mm', '35mm', '63.4mm', '34.8mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.4mm', '34.8mm', '63mm', '34.4mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63mm', '34.4mm', '63mm', '34.2mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63mm', '34.2mm', '62.8mm', '34mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '62.8mm', '34mm', '62.8mm', '33.8mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '62.8mm', '33.8mm', '61.8mm', '32.8mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '61.8mm', '32.8mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '64.675004mm', '41.250006mm', '65.809668mm', '41.250006mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '65.809668mm', '41.250006mm', '65.809668mm', '41.062821mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '65.809668mm', '41.062821mm', RemovedVias);
        PPCRemoveVia(Board, 'GND', '64.675004mm', '47.749993mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '52.675003mm', '55.250004mm', '51.450997mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '55.250004mm', '51.450997mm', '56.5mm', '51.450997mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '56.5mm', '51.450997mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '39.324991mm', '44.25mm', '38.276991mm', '44.314771mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '38.276991mm', '44.314771mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '39.324991mm', '40.250008mm', '37.975254mm', '40.276632mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '37.975254mm', '40.276632mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '42.750003mm', '27.32499mm', '42.750003mm', '26.181547mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '42.750003mm', '26.181547mm', '42.627375mm', '26.181547mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '42.627375mm', '26.181547mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '49.24999mm', '27.32499mm', '49.319778mm', '25.87667mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '49.319778mm', '25.87667mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '54.250006mm', '27.32499mm', '54.151097mm', '26.179251mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '54.151097mm', '26.179251mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '51.999998mm', '59.262493mm', '52.389709mm', '59.487493mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '52.389709mm', '59.487493mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '52.499997mm', '59.262493mm', '52.389709mm', '59.487493mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '53.012492mm', '58.249998mm', '53.462405mm', '58.241116mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '53.462405mm', '58.241116mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '69.599988mm', '29.325011mm', '70.038331mm', '29.223249mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '70.038331mm', '29.223249mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '19.749999mm', '58.462494mm', '19.674171mm', '58.906059mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '19.674171mm', '58.906059mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '19.25mm', '58.462494mm', '19.044653mm', '58.86291mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '19.044653mm', '58.86291mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '20.000011mm', '57.000013mm', '20.450011mm', '57.000013mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '20.450011mm', '57.000013mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '19.25mm', '55.537506mm', '18.953391mm', '54.959126mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '18.953391mm', '54.959126mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '19.749999mm', '55.537506mm', '19.606771mm', '54.69966mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '19.606771mm', '54.69966mm', RemovedVias);
        PPCRemoveVia(Board, 'GND', '37.500001mm', '45.479995mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '37.500001mm', '42.480001mm', '37.280005mm', '43.301038mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '37.280005mm', '43.301038mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '42.99999mm', '25.980009mm', '42.627375mm', '26.181547mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '49.000004mm', '25.980009mm', '49.319778mm', '25.87667mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '54.999992mm', '25.980009mm', '54.151097mm', '26.179251mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '61.000005mm', '25.980009mm', '63.298102mm', '25.980009mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '63.298102mm', '25.980009mm', '63.298102mm', '28.278106mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '63.298102mm', '28.278106mm', RemovedVias);
        PPCRemoveVia(Board, 'GND', '66.499994mm', '35.47999mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '66.499994mm', '43.479999mm', '66.181796mm', '43.798197mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '66.181796mm', '43.798197mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '58.50001mm', '25.275007mm', '58.110299mm', '25.500007mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '58.110299mm', '25.500007mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '67.999991mm', '48.479989mm', '67.999991mm', '48.929989mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '67.999991mm', '48.929989mm', RemovedVias);
        PPCRemoveVia(Board, 'GND', '54.999992mm', '54.980002mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '67.499992mm', '41.480003mm', '67.774992mm', '41.956317mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '67.774992mm', '41.956317mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '68.274997mm', '46.00001mm', '68.724997mm', '46.00001mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '68.724997mm', '46.00001mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '52.950008mm', '24.500002mm', '52.950008mm', '25.350002mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '52.950008mm', '25.350002mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '67.499992mm', '38.980008mm', '66.244255mm', '39.705008mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '66.244255mm', '39.705008mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '68.49999mm', '36.27501mm', '68.82499mm', '36.837927mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '68.82499mm', '36.837927mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '42.99999mm', '54.980002mm', '42.99999mm', '55.430002mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '42.99999mm', '55.430002mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '49.000004mm', '61.979988mm', '49.000004mm', '62.429988mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '49.000004mm', '62.429988mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '52.775002mm', '62.000003mm', '53.225002mm', '62.000003mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '53.225002mm', '62.000003mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '54.999992mm', '61.979988mm', '54.999992mm', '62.429988mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '54.999992mm', '62.429988mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '34.774988mm', '17.49999mm', '35.224988mm', '17.49999mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '35.224988mm', '17.49999mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '76.999998mm', '25.880009mm', '76.263877mm', '25.455009mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '76.263877mm', '25.455009mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '22.000007mm', '18.274995mm', '21.43709mm', '18.599995mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '21.43709mm', '18.599995mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '62.000003mm', '18.274995mm', '61.624715mm', '19.675588mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '61.624715mm', '19.675588mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '15.999993mm', '55.974996mm', '15.883525mm', '56.409663mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '15.883525mm', '56.409663mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '21.000009mm', '54.225012mm', '21.340814mm', '55.111777mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '21.340814mm', '55.111777mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '22.000007mm', '60.774986mm', '22.000007mm', '61.224986mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '22.000007mm', '61.224986mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '16.999991mm', '60.774986mm', '16.3mm', '61.149986mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '16.3mm', '61.149986mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '76.615011mm', '53.999994mm', '77.865011mm', '53.999994mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '77.865011mm', '53.999994mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '77.385012mm', '53.999994mm', '77.865011mm', '53.999994mm', RemovedTracks);
        PPCRemoveTrack(Board, 'GND', '76.937489mm', '28.999993mm', '77.387489mm', '28.999993mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '77.387489mm', '28.999993mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '10.61499mm', '57.000013mm', '10.06499mm', '57.000013mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '10.06499mm', '57.000013mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '11.384991mm', '57.000013mm', '11.934991mm', '57.000013mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '11.934991mm', '57.000013mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '50.635002mm', '4.99999mm', '50.9532mm', '4.681792mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '50.9532mm', '4.681792mm', RemovedVias);
        PPCRemoveVia(Board, 'GND', '50.635002mm', '6.26999mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '3.150006mm', '60.125mm', '2.920766mm', '60.512233mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '2.920766mm', '60.512233mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '46.00001mm', '56.325008mm', '46.00001mm', '56.775008mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '46.00001mm', '56.775008mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '19.825005mm', '17.49999mm', '20.275005mm', '17.49999mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '20.275005mm', '17.49999mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '59.825001mm', '17.49999mm', '60.275001mm', '17.49999mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '60.275001mm', '17.49999mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '78.824988mm', '34.000008mm', '79.274988mm', '34.000008mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '79.274988mm', '34.000008mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '77.499997mm', '38.924992mm', '77.499997mm', '39.374992mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '77.499997mm', '39.374992mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '24.000003mm', '11.324996mm', '24.000003mm', '11.774996mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '24.000003mm', '11.774996mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '63.999999mm', '11.324996mm', '63.999999mm', '10.674996mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '63.999999mm', '10.674996mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '61.749991mm', '11.54999mm', '61.550518mm', '11.953364mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '61.550518mm', '11.953364mm', RemovedVias);
        PPCRemoveTrack(Board, 'GND', '61.749991mm', '2.450008mm', '61.550519mm', '2.046633mm', RemovedTracks);
        PPCRemoveVia(Board, 'GND', '61.550519mm', '2.046633mm', RemovedVias);
        If Created Then
        Begin
            Board.AddPCBObject(PolygonObj);
            PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                          PCBM_BoardRegisteration, PolygonObj.I_ObjectAddress);
        End
        Else
            PolygonObj.EndModify;

        { 3V3 U1-103 }
        PPCAddTrack(Board, '3V3', '64.675004mm', '36.249991mm', '61.738149mm', '36.249991mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '61.738149mm', '36.249991mm', '61.738149mm', '33.461196mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '61.738149mm', '33.461196mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-114 }
        PPCAddTrack(Board, '3V3', '64.675004mm', '41.750005mm', '65.814197mm', '41.750005mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '65.814197mm', '41.750005mm', '65.814197mm', '41.907291mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '65.814197mm', '41.907291mm', '66.224994mm', '42.043692mm', '0.15mm', AddedTracks);

        { 3V3 U1-127 }
        PPCAddTrack(Board, '3V3', '64.675004mm', '48.249992mm', '65.723507mm', '48.306035mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '65.723507mm', '48.306035mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-149 }
        PPCAddTrack(Board, '3V3', '54.750005mm', '52.675003mm', '54.8mm', '53mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '54.8mm', '53mm', '54.8mm', '53.6mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '54.8mm', '53.6mm', '55mm', '53.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '55mm', '53.8mm', '55mm', '54mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '55mm', '54mm', '55.8mm', '54.8mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '55.8mm', '54.8mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-15 }
        PPCAddTrack(Board, '3V3', '39.324991mm', '43.750001mm', '37.875476mm', '43.787485mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '37.875476mm', '43.787485mm', '37.500001mm', '44.070002mm', '0.15mm', AddedTracks);

        { 3V3 U1-171 }
        PPCAddTrack(Board, '3V3', '43.750001mm', '52.675003mm', '43.486497mm', '53.483127mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '43.486497mm', '53.483127mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-172 }
        PPCAddTrack(Board, '3V3', '43.250002mm', '52.675003mm', '43.486497mm', '53.483127mm', '0.15mm', AddedTracks);

        { 3V3 U1-23 }
        PPCAddTrack(Board, '3V3', '39.324991mm', '39.750009mm', '38.275195mm', '39.729304mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '38.275195mm', '39.729304mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-49 }
        PPCAddTrack(Board, '3V3', '43.250002mm', '27.32499mm', '43.250002mm', '28.544681mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '43.250002mm', '28.544681mm', '42.671337mm', '28.544681mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '42.671337mm', '28.544681mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-62 }
        PPCAddTrack(Board, '3V3', '49.749989mm', '27.32499mm', '49.848898mm', '26.179251mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '49.848898mm', '26.179251mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-6 }
        PPCAddTrack(Board, '3V3', '39.324991mm', '48.249992mm', '37.877058mm', '48.327385mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '37.877058mm', '48.327385mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-72 }
        PPCAddTrack(Board, '3V3', '54.750005mm', '27.32499mm', '54.750005mm', '28.546569mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '54.750005mm', '28.546569mm', '54.484967mm', '28.546569mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '54.484967mm', '28.546569mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U1-82 }
        PPCAddTrack(Board, '3V3', '59.749995mm', '27.32499mm', '59.85mm', '25.375608mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '59.85mm', '25.375608mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U2-5 }
        PPCAddTrack(Board, '3V3', '51.499999mm', '59.262493mm', '51.6mm', '58.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '51.6mm', '58.8mm', '51.8mm', '58.6mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '51.8mm', '58.6mm', '52.4mm', '58.6mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '52.4mm', '58.6mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U2-8 }
        PPCAddTrack(Board, '3V3', '53.012492mm', '58.749997mm', '53.191724mm', '59.162763mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '53.191724mm', '59.162763mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 U4-3 }
        PPCAddTrack(Board, '3V3', '69.599988mm', '28.675mm', '67.967579mm', '27.804515mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '67.967579mm', '27.804515mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C100-1 }
        PPCAddTrack(Board, '3V3', '37.500001mm', '44.520002mm', '37.500001mm', '44.070002mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '37.500001mm', '44.070002mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C101-1 }
        PPCAddTrack(Board, '3V3', '37.500001mm', '41.520008mm', '37.500001mm', '41.070008mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '37.500001mm', '41.070008mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C102-1 }
        PPCAddTrack(Board, '3V3', '34.500007mm', '34.519997mm', '34.500007mm', '34.069997mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '34.500007mm', '34.069997mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C103-1 }
        PPCAddTrack(Board, '3V3', '42.99999mm', '25.019991mm', '42.99999mm', '24.569991mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '42.99999mm', '24.569991mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C104-1 }
        PPCAddTrack(Board, '3V3', '49.000004mm', '25.019991mm', '49.000004mm', '24.569991mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '49.000004mm', '24.569991mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C105-1 }
        PPCAddTrack(Board, '3V3', '54.999992mm', '25.019991mm', '54.999992mm', '24.569991mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '54.999992mm', '24.569991mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C106-1 }
        PPCAddTrack(Board, '3V3', '61.000005mm', '25.019991mm', '61.000005mm', '24.569991mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '61.000005mm', '24.569991mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C107-1 }
        PPCAddTrack(Board, '3V3', '69.499988mm', '31.019979mm', '69.499988mm', '30.569979mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '69.499988mm', '30.569979mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C108-1 }
        PPCAddVia(Board, '3V3', '66.499994mm', '34.519997mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C109-1 }
        PPCAddTrack(Board, '3V3', '66.499994mm', '42.520006mm', '66.224994mm', '42.043692mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '66.224994mm', '42.043692mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 R605-1 }
        PPCAddTrack(Board, '3V3', '71.999983mm', '50.175008mm', '71.999983mm', '49.725008mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '71.999983mm', '49.725008mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C111-1 }
        PPCAddTrack(Board, '3V3', '63.999999mm', '54.019983mm', '63.999999mm', '53.75mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '63.999999mm', '53.75mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C112-1 }
        PPCAddTrack(Board, '3V3', '54.999992mm', '54.020009mm', '55.4mm', '54.4mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, '3V3', '55.4mm', '54.4mm', '55.8mm', '54.8mm', '0.15mm', AddedTracks);

        { 3V3 C113-1 }
        PPCAddTrack(Board, '3V3', '47.000008mm', '54.019983mm', '48.000006mm', '54.599992mm', '0.15mm', AddedTracks);

        { 3V3 C114-1 }
        PPCAddTrack(Board, '3V3', '67.499992mm', '40.52001mm', '66.249992mm', '40.52001mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '66.249992mm', '40.52001mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C12-1 }
        PPCAddTrack(Board, '3V3', '51.049987mm', '24.500002mm', '50.599987mm', '24.500002mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '50.599987mm', '24.500002mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C15-1 }
        PPCAddVia(Board, '3V3', '42.99999mm', '54.020009mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C20-1 }
        PPCAddTrack(Board, '3V3', '49.000004mm', '61.019995mm', '49.000004mm', '60.569995mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '49.000004mm', '60.569995mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C21-1 }
        PPCAddTrack(Board, '3V3', '51.224993mm', '62.000003mm', '50.774993mm', '62.000003mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '50.774993mm', '62.000003mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C22-1 }
        PPCAddTrack(Board, '3V3', '54.999992mm', '61.019995mm', '54.999992mm', '60.569995mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '54.999992mm', '60.569995mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 C40-1 }
        PPCAddTrack(Board, '3V3', '76.999998mm', '24.919991mm', '76.999998mm', '24.469991mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '76.999998mm', '24.469991mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 FB1-1 }
        PPCAddTrack(Board, '3V3', '68.999989mm', '39.212495mm', '68.999989mm', '38.762495mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '68.999989mm', '38.762495mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 J10-1 }
        PPCAddTrack(Board, '3V3', '50.635002mm', '3.72999mm', '50.836248mm', '3.327498mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '50.836248mm', '3.327498mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 R600-1 }
        PPCAddTrack(Board, '3V3', '72.000008mm', '53.175002mm', '72.000008mm', '52.725002mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '72.000008mm', '52.725002mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 R70-2 }
        PPCAddTrack(Board, '3V3', '63.999999mm', '6.325006mm', '65.749999mm', '6.325006mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '65.749999mm', '6.325006mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { 3V3 Y1-4 }
        PPCAddTrack(Board, '3V3', '36.724996mm', '40.924988mm', '37.002593mm', '41.279163mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, '3V3', '37.002593mm', '41.279163mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-102 }
        PPCAddTrack(Board, 'GND', '64.675004mm', '35.749992mm', '64.2mm', '35.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '64.2mm', '35.8mm', '63.8mm', '35.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.8mm', '35.8mm', '63.6mm', '35.6mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.6mm', '35.6mm', '63.6mm', '35.2mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.6mm', '35.2mm', '63.4mm', '35mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.4mm', '35mm', '63.4mm', '34.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.4mm', '34.8mm', '63mm', '34.4mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63mm', '34.4mm', '63mm', '34.2mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63mm', '34.2mm', '62.8mm', '34mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '62.8mm', '34mm', '62.8mm', '33.8mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '62.8mm', '33.8mm', '61.8mm', '32.8mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '61.8mm', '32.8mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-113 }
        PPCAddTrack(Board, 'GND', '64.675004mm', '41.250006mm', '65.809668mm', '41.250006mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '65.809668mm', '41.250006mm', '65.809668mm', '41.062821mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '65.809668mm', '41.062821mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-126 }
        PPCAddVia(Board, 'GND', '64.675004mm', '47.749993mm', '0.3mm', '0.18mm', eMidLayer1, AddedVias);

        { GND U1-148 }
        PPCAddTrack(Board, 'GND', '55.250004mm', '52.675003mm', '55.250004mm', '51.450997mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '55.250004mm', '51.450997mm', '56.5mm', '51.450997mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '56.5mm', '51.450997mm', '0.4mm', '0.2mm', eMidLayer1, AddedVias);

        { GND U1-14 }
        PPCAddTrack(Board, 'GND', '39.324991mm', '44.25mm', '38.276991mm', '44.314771mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '38.276991mm', '44.314771mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-22 }
        PPCAddTrack(Board, 'GND', '39.324991mm', '40.250008mm', '37.975254mm', '40.276632mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '37.975254mm', '40.276632mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-48 }
        PPCAddTrack(Board, 'GND', '42.750003mm', '27.32499mm', '42.750003mm', '26.181547mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '42.750003mm', '26.181547mm', '42.627375mm', '26.181547mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '42.627375mm', '26.181547mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-61 }
        PPCAddTrack(Board, 'GND', '49.24999mm', '27.32499mm', '49.319778mm', '25.87667mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '49.319778mm', '25.87667mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U1-71 }
        PPCAddTrack(Board, 'GND', '54.250006mm', '27.32499mm', '54.151097mm', '26.179251mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '54.151097mm', '26.179251mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U2-6 }
        PPCAddTrack(Board, 'GND', '51.999998mm', '59.262493mm', '52.389709mm', '59.487493mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '52.389709mm', '59.487493mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U2-7 }
        PPCAddTrack(Board, 'GND', '52.499997mm', '59.262493mm', '52.389709mm', '59.487493mm', '0.15mm', AddedTracks);

        { GND U2-9 }
        PPCAddTrack(Board, 'GND', '53.012492mm', '58.249998mm', '53.462405mm', '58.241116mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '53.462405mm', '58.241116mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U4-2 }
        PPCAddTrack(Board, 'GND', '69.599988mm', '29.325011mm', '70.038331mm', '29.223249mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '70.038331mm', '29.223249mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U9-15 }
        PPCAddTrack(Board, 'GND', '19.749999mm', '58.462494mm', '19.674171mm', '58.906059mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '19.674171mm', '58.906059mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U9-16 }
        PPCAddTrack(Board, 'GND', '19.25mm', '58.462494mm', '19.044653mm', '58.86291mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '19.044653mm', '58.86291mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U9-17 }
        PPCAddTrack(Board, 'GND', '20.000011mm', '57.000013mm', '20.450011mm', '57.000013mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '20.450011mm', '57.000013mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U9-5 }
        PPCAddTrack(Board, 'GND', '19.25mm', '55.537506mm', '18.953391mm', '54.959126mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '18.953391mm', '54.959126mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND U9-6 }
        PPCAddTrack(Board, 'GND', '19.749999mm', '55.537506mm', '19.606771mm', '54.69966mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '19.606771mm', '54.69966mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C100-2 }
        PPCAddVia(Board, 'GND', '37.500001mm', '45.479995mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C101-2 }
        PPCAddTrack(Board, 'GND', '37.500001mm', '42.480001mm', '37.280005mm', '43.301038mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '37.280005mm', '43.301038mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C103-2 }
        PPCAddTrack(Board, 'GND', '42.99999mm', '25.980009mm', '42.627375mm', '26.181547mm', '0.15mm', AddedTracks);

        { GND C104-2 }
        PPCAddTrack(Board, 'GND', '49.000004mm', '25.980009mm', '49.319778mm', '25.87667mm', '0.15mm', AddedTracks);

        { GND C105-2 }
        PPCAddTrack(Board, 'GND', '54.999992mm', '25.980009mm', '54.151097mm', '26.179251mm', '0.15mm', AddedTracks);

        { GND C106-2 }
        PPCAddTrack(Board, 'GND', '61.000005mm', '25.980009mm', '63.298102mm', '25.980009mm', '0.15mm', AddedTracks);
        PPCAddTrack(Board, 'GND', '63.298102mm', '25.980009mm', '63.298102mm', '28.278106mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '63.298102mm', '28.278106mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C108-2 }
        PPCAddVia(Board, 'GND', '66.499994mm', '35.47999mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C109-2 }
        PPCAddTrack(Board, 'GND', '66.499994mm', '43.479999mm', '66.181796mm', '43.798197mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '66.181796mm', '43.798197mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C10-2 }
        PPCAddTrack(Board, 'GND', '58.50001mm', '25.275007mm', '58.110299mm', '25.500007mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '58.110299mm', '25.500007mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C110-2 }
        PPCAddTrack(Board, 'GND', '67.999991mm', '48.479989mm', '67.999991mm', '48.929989mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '67.999991mm', '48.929989mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C112-2 }
        PPCAddVia(Board, 'GND', '54.999992mm', '54.980002mm', '0.4mm', '0.2mm', eMidLayer1, AddedVias);

        { GND C114-2 }
        PPCAddTrack(Board, 'GND', '67.499992mm', '41.480003mm', '67.774992mm', '41.956317mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '67.774992mm', '41.956317mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C11-2 }
        PPCAddTrack(Board, 'GND', '68.274997mm', '46.00001mm', '68.724997mm', '46.00001mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '68.724997mm', '46.00001mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C12-2 }
        PPCAddTrack(Board, 'GND', '52.950008mm', '24.500002mm', '52.950008mm', '25.350002mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '52.950008mm', '25.350002mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C13-2 }
        PPCAddTrack(Board, 'GND', '67.499992mm', '38.980008mm', '66.244255mm', '39.705008mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '66.244255mm', '39.705008mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C14-2 }
        PPCAddTrack(Board, 'GND', '68.49999mm', '36.27501mm', '68.82499mm', '36.837927mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '68.82499mm', '36.837927mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C15-2 }
        PPCAddTrack(Board, 'GND', '42.99999mm', '54.980002mm', '42.99999mm', '55.430002mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '42.99999mm', '55.430002mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C20-2 }
        PPCAddTrack(Board, 'GND', '49.000004mm', '61.979988mm', '49.000004mm', '62.429988mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '49.000004mm', '62.429988mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C21-2 }
        PPCAddTrack(Board, 'GND', '52.775002mm', '62.000003mm', '53.225002mm', '62.000003mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '53.225002mm', '62.000003mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C22-2 }
        PPCAddTrack(Board, 'GND', '54.999992mm', '61.979988mm', '54.999992mm', '62.429988mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '54.999992mm', '62.429988mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C3-2 }
        PPCAddTrack(Board, 'GND', '34.774988mm', '17.49999mm', '35.224988mm', '17.49999mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '35.224988mm', '17.49999mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C40-2 }
        PPCAddTrack(Board, 'GND', '76.999998mm', '25.880009mm', '76.263877mm', '25.455009mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '76.263877mm', '25.455009mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C6D-2 }
        PPCAddTrack(Board, 'GND', '22.000007mm', '18.274995mm', '21.43709mm', '18.599995mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '21.43709mm', '18.599995mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C7D-2 }
        PPCAddTrack(Board, 'GND', '62.000003mm', '18.274995mm', '61.624715mm', '19.675588mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '61.624715mm', '19.675588mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C90-2 }
        PPCAddTrack(Board, 'GND', '15.999993mm', '55.974996mm', '15.883525mm', '56.409663mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '15.883525mm', '56.409663mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C91-2 }
        PPCAddTrack(Board, 'GND', '21.000009mm', '54.225012mm', '21.340814mm', '55.111777mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '21.340814mm', '55.111777mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C92-2 }
        PPCAddTrack(Board, 'GND', '22.000007mm', '60.774986mm', '22.000007mm', '61.224986mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '22.000007mm', '61.224986mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND C93-2 }
        PPCAddTrack(Board, 'GND', '16.999991mm', '60.774986mm', '16.3mm', '61.149986mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '16.3mm', '61.149986mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND D3-3 }
        PPCAddTrack(Board, 'GND', '76.615011mm', '53.999994mm', '77.865011mm', '53.999994mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '77.865011mm', '53.999994mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND D3-8 }
        PPCAddTrack(Board, 'GND', '77.385012mm', '53.999994mm', '77.865011mm', '53.999994mm', '0.15mm', AddedTracks);

        { GND D4-3 }
        PPCAddTrack(Board, 'GND', '76.937489mm', '28.999993mm', '77.387489mm', '28.999993mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '77.387489mm', '28.999993mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND D8-3 }
        PPCAddTrack(Board, 'GND', '10.61499mm', '57.000013mm', '10.06499mm', '57.000013mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '10.06499mm', '57.000013mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND D8-8 }
        PPCAddTrack(Board, 'GND', '11.384991mm', '57.000013mm', '11.934991mm', '57.000013mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '11.934991mm', '57.000013mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND J10-3 }
        PPCAddTrack(Board, 'GND', '50.635002mm', '4.99999mm', '50.9532mm', '4.681792mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '50.9532mm', '4.681792mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND J10-5 }
        PPCAddVia(Board, 'GND', '50.635002mm', '6.26999mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND J8-6 }
        PPCAddTrack(Board, 'GND', '3.150006mm', '60.125mm', '2.920766mm', '60.512233mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '2.920766mm', '60.512233mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R10-2 }
        PPCAddTrack(Board, 'GND', '46.00001mm', '56.325008mm', '46.00001mm', '56.775008mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '46.00001mm', '56.775008mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R1-2 }
        PPCAddTrack(Board, 'GND', '19.825005mm', '17.49999mm', '20.275005mm', '17.49999mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '20.275005mm', '17.49999mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R2-2 }
        PPCAddTrack(Board, 'GND', '59.825001mm', '17.49999mm', '60.275001mm', '17.49999mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '60.275001mm', '17.49999mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R41-2 }
        PPCAddTrack(Board, 'GND', '78.824988mm', '34.000008mm', '79.274988mm', '34.000008mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '79.274988mm', '34.000008mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R42-2 }
        PPCAddTrack(Board, 'GND', '77.499997mm', '38.924992mm', '77.499997mm', '39.374992mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '77.499997mm', '39.374992mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R63-2 }
        PPCAddTrack(Board, 'GND', '24.000003mm', '11.324996mm', '24.000003mm', '11.774996mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '24.000003mm', '11.774996mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND R73-2 }
        PPCAddTrack(Board, 'GND', '63.999999mm', '11.324996mm', '63.999999mm', '10.674996mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '63.999999mm', '10.674996mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND SW1-2 }
        PPCAddTrack(Board, 'GND', '61.749991mm', '11.54999mm', '61.550518mm', '11.953364mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '61.550518mm', '11.953364mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);

        { GND SW1-2 }
        PPCAddTrack(Board, 'GND', '61.749991mm', '2.450008mm', '61.550519mm', '2.046633mm', '0.15mm', AddedTracks);
        PPCAddVia(Board, 'GND', '61.550519mm', '2.046633mm', '0.4mm', '0.2mm', eBottomLayer, AddedVias);
        PolygonObj.Rebuild;
    Finally
        PCBServer.PostProcess;
    End;
    Board.ViewManager_FullUpdate;
    ShowMessage('Power-plane closure applied: ' + IntToStr(AddedTracks) +
                ' tracks, ' + IntToStr(AddedVias) + ' vias; removed ' +
                IntToStr(RemovedTracks) + ' tracks and ' +
                IntToStr(RemovedVias) + ' vias. Repour, save and run full DRC.');
End;
