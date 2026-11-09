param(
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$EntryPoint = Join-Path $PSScriptRoot "__main__.py"
$WorkDirectory = Join-Path $RepositoryRoot ".codex-temp\evt-visualizer-pyinstaller"
$SpecDirectory = Join-Path $RepositoryRoot ".codex-temp\evt-visualizer-spec"
$Destination = Join-Path $RepositoryRoot $OutputDirectory

Push-Location $RepositoryRoot
try {
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name EVT_GSN_Visualizer `
        --paths $RepositoryRoot `
        --distpath $Destination `
        --workpath $WorkDirectory `
        --specpath $SpecDirectory `
        --collect-submodules serial `
        $EntryPoint
} finally {
    Pop-Location
}
