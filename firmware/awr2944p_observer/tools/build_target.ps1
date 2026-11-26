param(
    [string]$TiRoot = "C:\ti\mmwave_mcuplus_sdk_04_07_02_01",
    [string]$CcsRoot = "C:\ti\ccs2010",
    [string]$SysConfigRoot = "C:\ti\sysconfig_1.23.0"
)

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Value) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Path, $Value, $encoding)
}

$observerRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = [IO.Path]::GetFullPath((Join-Path $observerRoot "..\.."))
$workParent = [IO.Path]::GetFullPath((Join-Path $repoRoot ".work"))
$buildRoot = [IO.Path]::GetFullPath((Join-Path $workParent "awr2944p_observer_target"))
if (-not $buildRoot.StartsWith($workParent + [IO.Path]::DirectorySeparatorChar)) {
    throw "Build directory is outside the repository work area"
}

$sdkRoot = Join-Path $TiRoot "mmwave_mcuplus_sdk_04_07_02_01"
$mcuRoot = Join-Path $TiRoot "mcu_plus_sdk_awr2x44p_10_02_00_04\mcu_plus_sdk_awr2x44p_10_02_00_04"
$dfpRoot = Join-Path $TiRoot "mmwave_dfp_02_04_18_01"
$dspLibRoot = Join-Path $TiRoot "dsplib_c66x_3_4_0_0"
$mathLibRoot = Join-Path $TiRoot "mathlib_c66x_3_1_2_1"
$armCompiler = Join-Path $CcsRoot "ccs\tools\compiler\ti-cgt-armllvm_4.0.2.LTS"
$dspCompiler = Join-Path $CcsRoot "ccs\tools\compiler\ti-cgt-c6000_8.3.13"
$make = Join-Path $CcsRoot "ccs\utils\bin\gmake.exe"
$sourceDemo = Join-Path $sdkRoot "ti\demo\awr2x44P\mmw_tdm"

$required = @(
    $sdkRoot,
    $mcuRoot,
    $dfpRoot,
    $dspLibRoot,
    $mathLibRoot,
    $armCompiler,
    $dspCompiler,
    $SysConfigRoot,
    $make,
    $sourceDemo
)
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required TI component is missing: $path"
    }
}

if (Test-Path -LiteralPath $buildRoot) {
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $buildRoot | Out-Null
$demoRoot = Join-Path $buildRoot "mmw_tdm"
Copy-Item -LiteralPath $sourceDemo -Destination $demoRoot -Recurse
Get-ChildItem -LiteralPath $demoRoot -File | Where-Object {
    $_.Name -match '^awr2x44(P|ECO)_mmw_demo' -or $_.Name -eq 'temp_stdout.txt'
} | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
}
foreach ($generatedPath in @(
        (Join-Path $demoRoot "obj_awr2x44P"),
        (Join-Path $demoRoot "mss\mssgenerated"),
        (Join-Path $demoRoot "dss\dssgenerated")
    )) {
    if (Test-Path -LiteralPath $generatedPath) {
        Remove-Item -LiteralPath $generatedPath -Recurse -Force
    }
}

$overlay = Join-Path $demoRoot "mss\observer"
$overlayHeaders = Join-Path $overlay "rls"
New-Item -ItemType Directory -Path $overlayHeaders -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $observerRoot "include\rls\awr2944p_observer.h") -Destination $overlayHeaders
Copy-Item -LiteralPath (Join-Path $observerRoot "include\rls\awr2944p_velocity_unwrap.h") -Destination $overlayHeaders
Copy-Item -LiteralPath (Join-Path $repoRoot "include\rls\radar_link.h") -Destination $overlayHeaders
Copy-Item -LiteralPath (Join-Path $observerRoot "target\include\rls\observer_app.h") -Destination $overlayHeaders
Copy-Item -LiteralPath (Join-Path $observerRoot "target\include\rls\observer_mcan_port.h") -Destination $overlayHeaders
Copy-Item -LiteralPath (Join-Path $observerRoot "src\awr2944p_observer.c") -Destination $overlay
Copy-Item -LiteralPath (Join-Path $observerRoot "src\awr2944p_velocity_unwrap.c") -Destination $overlay
Copy-Item -LiteralPath (Join-Path $repoRoot "src\radar_link.c") -Destination $overlay
Copy-Item -LiteralPath (Join-Path $observerRoot "target\src\observer_app.c") -Destination $overlay
Copy-Item -LiteralPath (Join-Path $observerRoot "target\src\observer_mcan_port.c") -Destination $overlay

$syscfgPath = Join-Path $demoRoot "mss\mss.syscfg"
$syscfg = Get-Content -LiteralPath $syscfgPath -Raw
$syscfg += Get-Content -LiteralPath (Join-Path $observerRoot "target\mss_mcan.syscfg.inc") -Raw
Write-Utf8NoBom -Path $syscfgPath -Value $syscfg

$makefilePath = Join-Path $demoRoot "mss\mmw_mss.mak"
$makefile = Get-Content -LiteralPath $makefilePath -Raw
$continuation = [char]92
$oldVpath = "          ./mss $continuation"
$newVpath = "          ./mss $continuation`n          ./mss/observer $continuation"
if (-not $makefile.Contains($oldVpath)) {
    throw "Unable to locate MSS VPATH insertion point"
}
$makefile = $makefile.Replace($oldVpath, $newVpath)
$sourceAnchor = "                           mss_main.c $continuation"
$sourceReplacement = "                           mss_main.c $continuation`n                           radar_link.c $continuation`n                           awr2944p_observer.c $continuation`n                           awr2944p_velocity_unwrap.c $continuation`n                           observer_mcan_port.c $continuation`n                           observer_app.c $continuation"
if (-not $makefile.Contains($sourceAnchor)) {
    throw "Unable to locate MSS source insertion point"
}
$makefile = $makefile.Replace($sourceAnchor, $sourceReplacement)
$includeAnchor = "MSS_CPU_INSTANCE := r5f"
$includeReplacement = "MSS_CPU_INSTANCE := r5f`n`nR5F_INCLUDE += -I./mss/mssgenerated -I./mss/observer"
if (-not $makefile.Contains($includeAnchor)) {
    throw "Unable to locate MSS include insertion point"
}
$makefile = $makefile.Replace($includeAnchor, $includeReplacement)
Write-Utf8NoBom -Path $makefilePath -Value $makefile

$mainPath = Join-Path $demoRoot "mss\mss_main.c"
$main = Get-Content -LiteralPath $mainPath -Raw
$includeAnchor = "#include <ti/demo/utils/mmwdemo_flash.h>"
$includeReplacement = "$includeAnchor`n#include `"rls/observer_app.h`""
if (-not $main.Contains($includeAnchor)) {
    throw "Unable to locate MSS include insertion point"
}
$main = $main.Replace($includeAnchor, $includeReplacement)
$initAnchor = "    MmwDemo_BoardInit();"
$initReplacement = "$initAnchor`n    DebugP_assert(rls_awr2944p_observer_app_init() == 0);"
if (-not $main.Contains($initAnchor)) {
    throw "Unable to locate MSS initialization insertion point"
}
$main = $main.Replace($initAnchor, $initReplacement)
$resultAnchor = "    MmwDemo_transmitProcessedOutput(gMmwMssMCB.loggingUartHandle,"
$resultReplacement = "    rls_awr2944p_observer_app_process(dpcResults);`n`n$resultAnchor"
if (-not $main.Contains($resultAnchor)) {
    throw "Unable to locate DPC result insertion point"
}
$main = $main.Replace($resultAnchor, $resultReplacement)
Write-Utf8NoBom -Path $mainPath -Value $main

$env:MMWAVE_SDK_DEVICE = "awr2x44P"
$env:MMWAVE_SDK_DEVICE_TYPE = "awr2x44P"
$env:CCS_INSTALL_PATH = $CcsRoot.Replace("\", "/")
$env:MMWAVE_SDK_INSTALL_PATH = $sdkRoot.Replace("\", "/")
$env:MMWAVE_AWR294X_DFP_INSTALL_PATH = $dfpRoot.Replace("\", "/")
$env:MCU_PLUS_AWR2X44P_INSTALL_PATH = $mcuRoot.Replace("\", "/")
$env:R5F_CLANG_INSTALL_PATH = $armCompiler.Replace("\", "/")
$env:C66X_CODEGEN_INSTALL_PATH = $dspCompiler.Replace("\", "/")
$env:C66x_DSPLIB_INSTALL_PATH = $dspLibRoot.Replace("\", "/")
$env:C66x_MATHLIB_INSTALL_PATH = $mathLibRoot.Replace("\", "/")
$env:SYSCONFIG_INSTALL_PATH = $SysConfigRoot.Replace("\", "/")
$env:AWR2X44P_RADARSS_IMAGE_BIN = (Join-Path $dfpRoot "firmware\radarss\xwr2x4xp_radarss_metarprc.bin").Replace("\", "/")

Push-Location $demoRoot
try {
    & $make PROC_CHAIN=TDM mmwDemo
    if ($LASTEXITCODE -ne 0) {
        throw "AWR2944P observer compilation failed with exit code $LASTEXITCODE"
    }
    & $make PROC_CHAIN=TDM bin
    $image = Join-Path $demoRoot "awr2x44P_mmw_demoTDM.appimage"
    if (-not (Test-Path -LiteralPath $image)) {
        throw "Unsigned appimage was not produced"
    }
    [pscustomobject]@{
        BuildRoot = $demoRoot
        AppImage = $image
        HighSecurityImage = Test-Path -LiteralPath ($image + ".hs")
        SigningExitCode = $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
