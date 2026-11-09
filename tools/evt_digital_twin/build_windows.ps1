param(
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$EntryPoint = Join-Path $PSScriptRoot "__main__.py"
$WorkDirectory = Join-Path $RepositoryRoot ".codex-temp\evt-digital-twin-pyinstaller"
$SpecDirectory = Join-Path $RepositoryRoot ".codex-temp\evt-digital-twin-spec"
$Destination = Join-Path $RepositoryRoot $OutputDirectory

Push-Location $RepositoryRoot
try {
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name EVT_GSN_Digital_Twin `
        --paths $RepositoryRoot `
        --distpath $Destination `
        --workpath $WorkDirectory `
        --specpath $SpecDirectory `
        $EntryPoint
} finally {
    Pop-Location
}
