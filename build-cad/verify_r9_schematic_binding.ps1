param(
    [Parameter(Mandatory = $true)]
    [string]$BoardPath,
    [Parameter(Mandatory = $true)]
    [string]$ReferenceBindingPath,
    [Parameter(Mandatory = $true)]
    [string]$SchematicDirectory,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$NativeCompileStatus = 'REQUIRES_ALTIUM_COMPILE'
)

$ErrorActionPreference = 'Stop'

function Convert-Record {
    param([string]$Line)
    $record = @{}
    foreach ($field in $Line.Trim('|').Split('|')) {
        $parts = $field.Split('=', 2)
        if ($parts.Count -eq 2) {
            $record[$parts[0]] = $parts[1]
        }
    }
    return $record
}

$lines = Get-Content -LiteralPath $BoardPath
$nets = @{}
$components = @{}
$pads = [System.Collections.Generic.List[object]]::new()

foreach ($line in $lines) {
    if ($line.StartsWith('|RECORD=Net|')) {
        $record = Convert-Record $line
        $nets[$record.ID] = $record.NAME
    }
    elseif ($line.StartsWith('|RECORD=Component|')) {
        $record = Convert-Record $line
        $components[$record.ID] = $record.SOURCEDESIGNATOR
    }
}

foreach ($line in $lines) {
    if (-not $line.StartsWith('|RECORD=Pad|')) {
        continue
    }
    $record = Convert-Record $line
    $netName = ''
    if ($record.ContainsKey('NET')) {
        $netName = $nets[$record.NET]
    }
    $pads.Add([pscustomobject]@{
        Designator = $components[$record.COMPONENT]
        Pad = $record.NAME
        Net = $netName
    })
}

$reference = Import-Csv -LiteralPath $ReferenceBindingPath
$referenceKeys = $reference | ForEach-Object {
    '{0}|{1}|{2}' -f $_.Designator, $_.Pad, $_.Graph_net
} | Sort-Object
$currentKeys = $pads | ForEach-Object {
    '{0}|{1}|{2}' -f $_.Designator, $_.Pad, $_.Net
} | Sort-Object
$differences = @(Compare-Object $referenceKeys $currentKeys)

$sheetFiles = @(Get-ChildItem -LiteralPath $SchematicDirectory -Filter '*.SchDoc' | Sort-Object Name)
$sheetEvidence = @($sheetFiles | ForEach-Object {
    [ordered]@{
        file = $_.Name
        bytes = $_.Length
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
})

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$pads | Export-Csv -LiteralPath (Join-Path $OutputDirectory 'R9_pad_binding.csv') -NoTypeInformation -Encoding utf8

$result = [ordered]@{
    generated_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    board = (Resolve-Path -LiteralPath $BoardPath).Path
    board_sha256 = (Get-FileHash -LiteralPath $BoardPath -Algorithm SHA256).Hash.ToLowerInvariant()
    schematic_sheets = $sheetFiles.Count
    board_components = $components.Count
    board_nets = $nets.Count
    board_pads = $pads.Count
    reference_binding_rows = $reference.Count
    binding_multiset_differences = $differences.Count
    schematic_to_r9_binding = if ($differences.Count -eq 0) { 'PASS' } else { 'FAIL' }
    native_compile = $NativeCompileStatus
    production_authority = 'NOT_AUTHORIZED'
    sheets = $sheetEvidence
}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'R9_schematic_verification.json') -Encoding utf8

if ($differences.Count -ne 0) {
    $differences | Export-Csv -LiteralPath (Join-Path $OutputDirectory 'R9_binding_differences.csv') -NoTypeInformation -Encoding utf8
    throw "R9 schematic binding mismatch: $($differences.Count) multiset differences"
}

$result
