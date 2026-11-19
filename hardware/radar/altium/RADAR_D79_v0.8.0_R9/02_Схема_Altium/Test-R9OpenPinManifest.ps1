param(
    [Parameter(Mandatory = $true)]
    [string]$AuditCsv,

    [Parameter(Mandatory = $true)]
    [string]$ManifestCsv,

    [string]$OutputPath
)

$audit = Import-Csv -LiteralPath $AuditCsv
$manifest = Import-Csv -LiteralPath $ManifestCsv
$openPins = @($audit | Where-Object { $_.Status -eq 'OPEN_UNMARKED' })

function Get-Key {
    param([object]$Row)
    return "$($Row.Ref)|$($Row.Pin)"
}

$openKeys = @($openPins | ForEach-Object { Get-Key $_ })
$manifestKeys = @($manifest | ForEach-Object { Get-Key $_ })
$duplicateManifest = @($manifestKeys | Group-Object | Where-Object Count -ne 1)
$missingManifest = @($openKeys | Where-Object { $_ -notin $manifestKeys })
$extraManifest = @($manifestKeys | Where-Object { $_ -notin $openKeys })
$groundRows = @($manifest | Where-Object {
    $_.Disposition -eq 'CONNECT_GND' -and $_.Suppress -eq 'NO'
})
$suppressedRows = @($manifest | Where-Object {
    $_.Disposition -in @('INTENTIONAL_NC', 'MECHANICAL_NC') -and
    $_.Suppress -eq 'YES'
})
$invalidRows = @($manifest | Where-Object {
    -not (
        ($_.Disposition -eq 'CONNECT_GND' -and $_.Suppress -eq 'NO') -or
        ($_.Disposition -in @('INTENTIONAL_NC', 'MECHANICAL_NC') -and
            $_.Suppress -eq 'YES')
    )
})

$result = if (
    $openPins.Count -eq 180 -and
    $manifest.Count -eq 180 -and
    $groundRows.Count -eq 4 -and
    $suppressedRows.Count -eq 176 -and
    $duplicateManifest.Count -eq 0 -and
    $missingManifest.Count -eq 0 -and
    $extraManifest.Count -eq 0 -and
    $invalidRows.Count -eq 0
) { 'PASS' } else { 'FAIL' }

$summary = @(
    'R9 open-pin disposition manifest audit'
    "Open pins in schematic audit: $($openPins.Count)"
    "Manifest rows: $($manifest.Count)"
    "Required GND connections: $($groundRows.Count)"
    "Reviewed intentional NC entries: $($suppressedRows.Count)"
    "Duplicate manifest keys: $($duplicateManifest.Count)"
    "Open pins missing from manifest: $($missingManifest.Count)"
    "Manifest entries absent from open-pin audit: $($extraManifest.Count)"
    "Invalid disposition rows: $($invalidRows.Count)"
    "Result: $result"
)

if ($OutputPath) {
    $summary | Set-Content -LiteralPath $OutputPath -Encoding utf8
}
$summary

if ($result -ne 'PASS') {
    exit 1
}
