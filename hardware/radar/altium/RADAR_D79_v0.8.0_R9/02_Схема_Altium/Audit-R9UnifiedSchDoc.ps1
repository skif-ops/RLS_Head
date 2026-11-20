param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [string]$OutputCsv,

    [string]$OutputSummary,

    [string]$OutputDanglingCsv,

    [string]$OutputLabelCsv
)

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInput)
$folder = [System.IO.Path]::GetDirectoryName($resolvedInput)

if (-not $OutputCsv) {
    $OutputCsv = Join-Path $folder ($baseName + '_pin_audit.csv')
}
if (-not $OutputSummary) {
    $OutputSummary = Join-Path $folder ($baseName + '_pin_audit.txt')
}
if (-not $OutputDanglingCsv) {
    $OutputDanglingCsv = Join-Path $folder ($baseName + '_dangling_wire_ends.csv')
}
if (-not $OutputLabelCsv) {
    $OutputLabelCsv = Join-Path $folder ($baseName + '_unattached_labels.csv')
}

function ConvertTo-RecordMap {
    param([string]$Record)

    $result = @{}
    foreach ($part in $Record.Split('|')) {
        if (-not $part) {
            continue
        }
        $separator = $part.IndexOf('=')
        if ($separator -lt 1) {
            continue
        }
        $key = $part.Substring(0, $separator)
        $value = $part.Substring($separator + 1)
        $result[$key] = $value
    }
    return $result
}

function Get-PointKey {
    param([int]$X, [int]$Y)
    return "$X`:$Y"
}

$ascii = [System.Text.Encoding]::ASCII.GetString(
    [System.IO.File]::ReadAllBytes($resolvedInput)
)
$recordTexts = [regex]::Matches($ascii, '\|RECORD=[^\r\n\x00]+') |
    ForEach-Object { $_.Value }

$designators = @{}
$wirePoints = [System.Collections.Generic.HashSet[string]]::new()
$labelPoints = [System.Collections.Generic.HashSet[string]]::new()
$labelsByPoint = @{}
$portPoints = [System.Collections.Generic.HashSet[string]]::new()
$noErcPoints = [System.Collections.Generic.HashSet[string]]::new()
$pins = [System.Collections.Generic.List[object]]::new()
$wireSegments = [System.Collections.Generic.List[object]]::new()

foreach ($recordText in $recordTexts) {
    $record = ConvertTo-RecordMap $recordText
    if (-not $record.ContainsKey('RECORD')) {
        continue
    }

    switch ([int]$record.RECORD) {
        2 {
            $pins.Add([pscustomobject]@{
                OwnerIndex = [int]$record.OwnerIndex
                Pin = $record.Designator
                PinName = $record.Name
                ElectricalType = [int]$record.Electrical
                PinConglomerate = [int]$record.PinConglomerate
                PinLength = [int]$record.PinLength
                X = [int]$record.'Location.X'
                Y = [int]$record.'Location.Y'
            })
        }
        18 {
            [void]$portPoints.Add((Get-PointKey ([int]$record.'Location.X') ([int]$record.'Location.Y')))
        }
        22 {
            [void]$noErcPoints.Add((Get-PointKey ([int]$record.'Location.X') ([int]$record.'Location.Y')))
        }
        25 {
            $labelKey = Get-PointKey ([int]$record.'Location.X') ([int]$record.'Location.Y')
            [void]$labelPoints.Add($labelKey)
            if (-not $labelsByPoint.ContainsKey($labelKey)) {
                $labelsByPoint[$labelKey] = [System.Collections.Generic.List[string]]::new()
            }
            $labelsByPoint[$labelKey].Add($record.Text)
        }
        27 {
            $vertexCount = [int]$record.LocationCount
            for ($index = 1; $index -le $vertexCount; $index++) {
                [void]$wirePoints.Add((Get-PointKey ([int]$record["X$index"]) ([int]$record["Y$index"])))
            }
            if ($vertexCount -eq 2) {
                $wireSegments.Add([pscustomobject]@{
                    Index = $wireSegments.Count
                    X1 = [int]$record.X1
                    Y1 = [int]$record.Y1
                    X2 = [int]$record.X2
                    Y2 = [int]$record.Y2
                })
            }
        }
        34 {
            if ($record.Name -eq 'Designator') {
                $designators[[int]$record.OwnerIndex] = $record.Text
            }
        }
    }
}

$rows = [System.Collections.Generic.List[object]]::new()
$connected = 0
$markedNc = 0
$open = 0
$pinHotspots = [System.Collections.Generic.HashSet[string]]::new()
$pinsByHotspot = @{}

foreach ($pin in $pins) {
    $hotspotX = $pin.X
    $hotspotY = $pin.Y
    switch ($pin.PinConglomerate -band 3) {
        0 { $hotspotX += $pin.PinLength }
        1 { $hotspotY += $pin.PinLength }
        2 { $hotspotX -= $pin.PinLength }
        3 { $hotspotY -= $pin.PinLength }
    }

    $key = Get-PointKey $hotspotX $hotspotY
    [void]$pinHotspots.Add($key)
    if (-not $pinsByHotspot.ContainsKey($key)) {
        $pinsByHotspot[$key] = [System.Collections.Generic.List[string]]::new()
    }
    $pinsByHotspot[$key].Add("$($designators[$pin.OwnerIndex]).$($pin.Pin)")
    $hasWire = $wirePoints.Contains($key)
    $hasLabel = $labelPoints.Contains($key)
    $hasPort = $portPoints.Contains($key)
    $hasNoErc = $noErcPoints.Contains($key)

    if ($hasWire -or $hasLabel -or $hasPort) {
        $status = 'CONNECTED'
        $connected++
    }
    elseif ($hasNoErc) {
        $status = 'NC_MARKED'
        $markedNc++
    }
    else {
        $status = 'OPEN_UNMARKED'
        $open++
    }

    $evidence = @()
    if ($hasWire) { $evidence += 'WIRE' }
    if ($hasLabel) { $evidence += 'NET_LABEL' }
    if ($hasPort) { $evidence += 'PORT' }
    if ($hasNoErc) { $evidence += 'NO_CONNECT' }
    if ($evidence.Count -eq 0) { $evidence += 'NONE' }

    $rows.Add([pscustomobject]@{
        Ref = $designators[$pin.OwnerIndex]
        Pin = $pin.Pin
        PinName = $pin.PinName
        ElectricalType = $pin.ElectricalType
        X_mil = $hotspotX * 10
        Y_mil = $hotspotY * 10
        Wire = $hasWire
        NetLabel = $hasLabel
        Port = $hasPort
        NoConnect = $hasNoErc
        Status = $status
        Evidence = ($evidence -join ';') + ';'
    })
}

$approvedDirectiveKeys = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
foreach ($applicationName in @(
    'R9_unified_flat_nc_application.csv',
    'R9_unified_flat_no_driver_application.csv'
)) {
    $applicationPath = Join-Path $folder $applicationName
    if (-not (Test-Path -LiteralPath $applicationPath)) {
        continue
    }
    foreach ($applicationRow in (Import-Csv -LiteralPath $applicationPath)) {
        if ($applicationRow.Ref -and $applicationRow.Pin -and
            $applicationRow.Application -notmatch 'FAIL|NOT_FOUND|MISSING') {
            [void]$approvedDirectiveKeys.Add(
                "$($applicationRow.Ref)|$($applicationRow.Pin)"
            )
        }
    }
}

$connectedWithDirective = @(
    $rows | Where-Object {
        $_.NoConnect -and ($_.Wire -or $_.NetLabel -or $_.Port)
    }
)
$unexpectedConnectedDirective = @(
    $connectedWithDirective | Where-Object {
        -not $approvedDirectiveKeys.Contains("$($_.Ref)|$($_.Pin)")
    }
)

$rows | Export-Csv -LiteralPath $OutputCsv -NoTypeInformation -Encoding utf8

function Test-PointOnSegment {
    param(
        [int]$X,
        [int]$Y,
        [object]$Segment
    )

    $dx = $Segment.X2 - $Segment.X1
    $dy = $Segment.Y2 - $Segment.Y1
    $cross = ($X - $Segment.X1) * $dy - ($Y - $Segment.Y1) * $dx
    if ($cross -ne 0) {
        return $false
    }

    return ($X -ge [Math]::Min($Segment.X1, $Segment.X2) -and
            $X -le [Math]::Max($Segment.X1, $Segment.X2) -and
            $Y -ge [Math]::Min($Segment.Y1, $Segment.Y2) -and
            $Y -le [Math]::Max($Segment.Y1, $Segment.Y2))
}

$horizontalSegments = @{}
$verticalSegments = @{}
$diagonalSegments = [System.Collections.Generic.List[object]]::new()
foreach ($segment in $wireSegments) {
    if ($segment.Y1 -eq $segment.Y2) {
        if (-not $horizontalSegments.ContainsKey($segment.Y1)) {
            $horizontalSegments[$segment.Y1] = [System.Collections.Generic.List[object]]::new()
        }
        $horizontalSegments[$segment.Y1].Add($segment)
    }
    elseif ($segment.X1 -eq $segment.X2) {
        if (-not $verticalSegments.ContainsKey($segment.X1)) {
            $verticalSegments[$segment.X1] = [System.Collections.Generic.List[object]]::new()
        }
        $verticalSegments[$segment.X1].Add($segment)
    }
    else {
        $diagonalSegments.Add($segment)
    }
}

function Get-TouchingSegmentCount {
    param([int]$X, [int]$Y)

    $indexes = [System.Collections.Generic.HashSet[int]]::new()
    if ($horizontalSegments.ContainsKey($Y)) {
        foreach ($segment in $horizontalSegments[$Y]) {
            if ($X -ge [Math]::Min($segment.X1, $segment.X2) -and
                $X -le [Math]::Max($segment.X1, $segment.X2)) {
                [void]$indexes.Add($segment.Index)
                if ($indexes.Count -gt 1) { return $indexes.Count }
            }
        }
    }
    if ($verticalSegments.ContainsKey($X)) {
        foreach ($segment in $verticalSegments[$X]) {
            if ($Y -ge [Math]::Min($segment.Y1, $segment.Y2) -and
                $Y -le [Math]::Max($segment.Y1, $segment.Y2)) {
                [void]$indexes.Add($segment.Index)
                if ($indexes.Count -gt 1) { return $indexes.Count }
            }
        }
    }
    foreach ($segment in $diagonalSegments) {
        if (Test-PointOnSegment $X $Y $segment) {
            [void]$indexes.Add($segment.Index)
            if ($indexes.Count -gt 1) { return $indexes.Count }
        }
    }
    return $indexes.Count
}

$dangling = [System.Collections.Generic.List[object]]::new()
$danglingKeys = [System.Collections.Generic.HashSet[string]]::new()
$nonOrthogonal = 0
$zeroLength = 0

foreach ($segment in $wireSegments) {
    if ($segment.X1 -eq $segment.X2 -and $segment.Y1 -eq $segment.Y2) {
        $zeroLength++
    }
    elseif ($segment.X1 -ne $segment.X2 -and $segment.Y1 -ne $segment.Y2) {
        $nonOrthogonal++
    }

    foreach ($endpoint in @(
        [pscustomobject]@{ End = 1; X = $segment.X1; Y = $segment.Y1 },
        [pscustomobject]@{ End = 2; X = $segment.X2; Y = $segment.Y2 }
    )) {
        $key = Get-PointKey $endpoint.X $endpoint.Y
        $hasAnchor = ($pinHotspots.Contains($key) -or
                      $labelPoints.Contains($key) -or
                      $portPoints.Contains($key))
        $touchingSegments = Get-TouchingSegmentCount $endpoint.X $endpoint.Y

        if (-not $hasAnchor -and $touchingSegments -le 1 -and $danglingKeys.Add($key)) {
            if ($endpoint.End -eq 1) {
                $otherX = $segment.X2
                $otherY = $segment.Y2
            }
            else {
                $otherX = $segment.X1
                $otherY = $segment.Y1
            }
            $otherKey = Get-PointKey $otherX $otherY
            $otherEvidence = [System.Collections.Generic.List[string]]::new()
            if ($pinsByHotspot.ContainsKey($otherKey)) {
                $otherEvidence.Add('PIN:' + ($pinsByHotspot[$otherKey] -join '+'))
            }
            if ($labelsByPoint.ContainsKey($otherKey)) {
                $otherEvidence.Add('LABEL:' + ($labelsByPoint[$otherKey] -join '+'))
            }
            if ($portPoints.Contains($otherKey)) {
                $otherEvidence.Add('PORT')
            }
            $otherTouching = Get-TouchingSegmentCount $otherX $otherY
            if ($otherTouching -gt 1) {
                $otherEvidence.Add("WIRE_COUNT:$otherTouching")
            }
            if ($otherEvidence.Count -eq 0) {
                $otherEvidence.Add('NO_ANCHOR')
            }
            $dangling.Add([pscustomobject]@{
                Segment = $segment.Index
                End = $endpoint.End
                X_mil = $endpoint.X * 10
                Y_mil = $endpoint.Y * 10
                Length_mil = (([Math]::Abs($segment.X2 - $segment.X1) +
                    [Math]::Abs($segment.Y2 - $segment.Y1)) * 10)
                Other_X_mil = $otherX * 10
                Other_Y_mil = $otherY * 10
                OtherEvidence = $otherEvidence -join ';'
                Evidence = 'NO_PIN_LABEL_PORT_OR_SECOND_WIRE'
            })
        }
    }
}

$unattachedLabels = [System.Collections.Generic.List[object]]::new()
foreach ($labelKey in $labelPoints) {
    $parts = $labelKey.Split(':')
    $x = [int]$parts[0]
    $y = [int]$parts[1]
    $attached = $pinHotspots.Contains($labelKey)
    if (-not $attached) {
        $attached = (Get-TouchingSegmentCount $x $y) -gt 0
    }
    if (-not $attached) {
        $unattachedLabels.Add([pscustomobject]@{
            X_mil = $x * 10
            Y_mil = $y * 10
            Evidence = 'NO_PIN_OR_WIRE_AT_LABEL_ANCHOR'
        })
    }
}

$dangling | Export-Csv -LiteralPath $OutputDanglingCsv -NoTypeInformation -Encoding utf8
$unattachedLabels | Export-Csv -LiteralPath $OutputLabelCsv -NoTypeInformation -Encoding utf8

$summary = @(
    'R9 unified master full pin audit'
    "Document: $resolvedInput"
    "Wire endpoint count: $($wirePoints.Count)"
    "Net label anchor count: $($labelPoints.Count)"
    "Port anchor count: $($portPoints.Count)"
    "No-connect marker count: $($noErcPoints.Count)"
    "Total pins: $($pins.Count)"
    "Connected pins: $connected"
    "Explicitly marked NC pins: $markedNc"
    "Unmarked open pins: $open"
    "Connected pins with reviewed ERC directives: $($connectedWithDirective.Count - $unexpectedConnectedDirective.Count)"
    "Connected pins with unexpected NC/ERC directives: $($unexpectedConnectedDirective.Count)"
    "Dangling wire endpoints: $($dangling.Count)"
    "Unattached net labels: $($unattachedLabels.Count)"
    "Non-orthogonal wire segments: $nonOrthogonal"
    "Zero-length wire segments: $zeroLength"
    $(if ($open -eq 0 -and $unexpectedConnectedDirective.Count -eq 0 -and
          $dangling.Count -eq 0 -and
          $unattachedLabels.Count -eq 0 -and $nonOrthogonal -eq 0 -and
          $zeroLength -eq 0) { 'Result: PASS' } else { 'Result: FAIL' })
)
$summary | Set-Content -LiteralPath $OutputSummary -Encoding utf8
$summary

