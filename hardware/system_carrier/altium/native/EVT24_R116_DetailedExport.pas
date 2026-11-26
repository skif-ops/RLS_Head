Function R116CsvQuote(S : String) : String;
Begin
    S := StringReplace(S, '"', '""', rfReplaceAll);
    Result := '"' + S + '"';
End;

Function R116Float(Value : Double) : String;
Begin
    Result := StringReplace(FloatToStr(Value), ',', '.', rfReplaceAll);
End;

Procedure ExportR116Details;
Var
    Board       : IPCB_Board;
    Iterator    : IPCB_BoardIterator;
    TrackObj    : IPCB_Track;
    ViaObj      : IPCB_Via;
    PadObj      : IPCB_Pad;
    ComponentObj: IPCB_Component;
    Connection  : IPCB_Connection;
    FillObj      : IPCB_Fill;
    PolygonObj   : IPCB_Polygon;
    Rpt         : TStringList;
    NetName     : String;
    Designator  : String;
    BasePath    : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
        Board := PCBServer.GetPCBBoardByPath(
            'C:\Users\skifn\.codex\.chatgpt-projects\g-p-6a9feb917c48819182ec25e1ef55310c\RLS_Head-git\hardware\system_carrier\altium\native\EVT24_REWORK_R168.PcbDoc');
    If Board = Nil Then
    Begin
        ShowMessage('R116 detail export stopped: no active PCB.');
        Exit;
    End;
    If UpperCase(ExtractFileName(Board.FileName)) = '' Then
    Begin
        ShowMessage('Detail export stopped: active PCB has no filename.');
        Exit;
    End;

    BasePath := ChangeFileExt(Board.FileName, '') + '_detail_';

    Rpt := TStringList.Create;
    Rpt.Add('net,layer,x1_mm,y1_mm,x2_mm,y2_mm,width_mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    TrackObj := Iterator.FirstPCBObject;
    While TrackObj <> Nil Do
    Begin
        NetName := '';
        If TrackObj.Net <> Nil Then NetName := TrackObj.Net.Name;
        Rpt.Add(R116CsvQuote(NetName) + ',' + IntToStr(Ord(TrackObj.Layer)) + ',' +
            R116Float(CoordToMMs(TrackObj.X1)) + ',' +
            R116Float(CoordToMMs(TrackObj.Y1)) + ',' +
            R116Float(CoordToMMs(TrackObj.X2)) + ',' +
            R116Float(CoordToMMs(TrackObj.Y2)) + ',' +
            R116Float(CoordToMMs(TrackObj.Width)));
        TrackObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'tracks.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('net,x_mm,y_mm,size_mm,hole_mm,low_layer,high_layer');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ViaObj := Iterator.FirstPCBObject;
    While ViaObj <> Nil Do
    Begin
        NetName := '';
        If ViaObj.Net <> Nil Then NetName := ViaObj.Net.Name;
        Rpt.Add(R116CsvQuote(NetName) + ',' +
            R116Float(CoordToMMs(ViaObj.X)) + ',' +
            R116Float(CoordToMMs(ViaObj.Y)) + ',' +
            R116Float(CoordToMMs(ViaObj.Size)) + ',' +
            R116Float(CoordToMMs(ViaObj.HoleSize)) + ',' +
            IntToStr(Ord(ViaObj.LowLayer)) + ',' +
            IntToStr(Ord(ViaObj.HighLayer)));
        ViaObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'vias.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('designator,pad,net,x_mm,y_mm,layer,hole_mm,x_size_mm,y_size_mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    PadObj := Iterator.FirstPCBObject;
    While PadObj <> Nil Do
    Begin
        Designator := '';
        NetName := '';
        If PadObj.Component <> Nil Then Designator := PadObj.Component.SourceDesignator;
        If PadObj.Net <> Nil Then NetName := PadObj.Net.Name;
        Rpt.Add(R116CsvQuote(Designator) + ',' + R116CsvQuote(PadObj.Name) + ',' +
            R116CsvQuote(NetName) + ',' + R116Float(CoordToMMs(PadObj.X)) + ',' +
            R116Float(CoordToMMs(PadObj.Y)) + ',' + IntToStr(Ord(PadObj.Layer)) + ',' +
            R116Float(CoordToMMs(PadObj.HoleSize)) + ',' +
            R116Float(CoordToMMs(PadObj.TopXSize)) + ',' +
            R116Float(CoordToMMs(PadObj.TopYSize)));
        PadObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'pads.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('designator,pattern,x_mm,y_mm,rotation,layer,left_mm,bottom_mm,right_mm,top_mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    ComponentObj := Iterator.FirstPCBObject;
    While ComponentObj <> Nil Do
    Begin
        Rpt.Add(R116CsvQuote(ComponentObj.SourceDesignator) + ',' +
            R116CsvQuote(ComponentObj.Pattern) + ',' +
            R116Float(CoordToMMs(ComponentObj.X)) + ',' +
            R116Float(CoordToMMs(ComponentObj.Y)) + ',' +
            R116Float(ComponentObj.Rotation) + ',' + IntToStr(Ord(ComponentObj.Layer)) + ',' +
            R116Float(CoordToMMs(ComponentObj.BoundingRectangle.Left)) + ',' +
            R116Float(CoordToMMs(ComponentObj.BoundingRectangle.Bottom)) + ',' +
            R116Float(CoordToMMs(ComponentObj.BoundingRectangle.Right)) + ',' +
            R116Float(CoordToMMs(ComponentObj.BoundingRectangle.Top)));
        ComponentObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'components.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('net,layer,x1_mm,y1_mm,x2_mm,y2_mm,rotation');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eFillObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    FillObj := Iterator.FirstPCBObject;
    While FillObj <> Nil Do
    Begin
        NetName := '';
        If FillObj.Net <> Nil Then NetName := FillObj.Net.Name;
        Rpt.Add(R116CsvQuote(NetName) + ',' + IntToStr(Ord(FillObj.Layer)) + ',' +
            R116Float(CoordToMMs(FillObj.X1Location)) + ',' +
            R116Float(CoordToMMs(FillObj.Y1Location)) + ',' +
            R116Float(CoordToMMs(FillObj.X2Location)) + ',' +
            R116Float(CoordToMMs(FillObj.Y2Location)) + ',' +
            R116Float(FillObj.Rotation));
        FillObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'fills.csv');
    Rpt.Free;

    Rpt := TStringList.Create;
    Rpt.Add('net,layer,left_mm,bottom_mm,right_mm,top_mm');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePolyObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    PolygonObj := Iterator.FirstPCBObject;
    While PolygonObj <> Nil Do
    Begin
        NetName := '';
        If PolygonObj.Net <> Nil Then NetName := PolygonObj.Net.Name;
        Rpt.Add(R116CsvQuote(NetName) + ',' + IntToStr(Ord(PolygonObj.Layer)) + ',' +
            R116Float(CoordToMMs(PolygonObj.BoundingRectangle.Left)) + ',' +
            R116Float(CoordToMMs(PolygonObj.BoundingRectangle.Bottom)) + ',' +
            R116Float(CoordToMMs(PolygonObj.BoundingRectangle.Right)) + ',' +
            R116Float(CoordToMMs(PolygonObj.BoundingRectangle.Top)));
        PolygonObj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'polygons.csv');
    Rpt.Free;

    Board.ConnectivelyValidateNets;
    Rpt := TStringList.Create;
    Rpt.Add('mode,net,x1_mm,y1_mm,x2_mm,y2_mm,layer1,layer2');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eConnectionObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Connection := Iterator.FirstPCBObject;
    While Connection <> Nil Do
    Begin
        NetName := '';
        If Connection.Net <> Nil Then NetName := Connection.Net.Name;
        Rpt.Add(IntToStr(Ord(Connection.Mode)) + ',' + R116CsvQuote(NetName) + ',' +
            R116Float(CoordToMMs(Connection.X1)) + ',' +
            R116Float(CoordToMMs(Connection.Y1)) + ',' +
            R116Float(CoordToMMs(Connection.X2)) + ',' +
            R116Float(CoordToMMs(Connection.Y2)) + ',' +
            IntToStr(Ord(Connection.Layer1)) + ',' +
            IntToStr(Ord(Connection.Layer2)));
        Connection := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Rpt.SaveToFile(BasePath + 'connections.csv');
    Rpt.Free;

    ShowMessage('Detailed geometry exported for ' + ExtractFileName(Board.FileName) + '.');
End;
