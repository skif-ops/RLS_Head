param(
    [string]$BuildDirectory = "build-firmware-stm32h753",
    [string]$ArmGccRoot = $env:ARM_GCC_ROOT,
    [string]$NinjaPath = $env:NINJA_PATH
)

$ErrorActionPreference = "Stop"

if (-not $ArmGccRoot) {
    throw "Set ARM_GCC_ROOT to the extracted xPack GNU Arm Embedded GCC directory."
}

$gccBin = Join-Path $ArmGccRoot "bin"
$gcc = Join-Path $gccBin "arm-none-eabi-gcc.exe"
if (-not (Test-Path -LiteralPath $gcc)) {
    throw "arm-none-eabi-gcc.exe was not found under ARM_GCC_ROOT."
}

if (-not $NinjaPath) {
    $ninjaCommand = Get-Command ninja.exe -ErrorAction SilentlyContinue
    if (-not $ninjaCommand) {
        throw "Set NINJA_PATH or add ninja.exe to PATH."
    }
    $NinjaPath = $ninjaCommand.Source
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$toolchain = Join-Path $repoRoot "cmake\toolchains\arm-none-eabi-gcc.cmake"
$build = Join-Path $repoRoot $BuildDirectory
$env:Path = $gccBin + ";" + $env:Path

cmake -S $repoRoot -B $build -G Ninja `
    "-DCMAKE_MAKE_PROGRAM=$NinjaPath" `
    "-DCMAKE_TOOLCHAIN_FILE=$toolchain" `
    -DHIL_BUILD_HOST_TESTS=OFF `
    -DHIL_BUILD_STM32H753_SMOKE=OFF `
    -DEVT_BUILD_STM32H753_FIRMWARE=ON `
    -DCMAKE_BUILD_TYPE=Release

cmake --build $build

Get-FileHash -Algorithm SHA256 `
    (Join-Path $build "EVT_SYS_CARRIER_STM32H753_R1.elf"), `
    (Join-Path $build "EVT_SYS_CARRIER_STM32H753_R1.hex"), `
    (Join-Path $build "EVT_SYS_CARRIER_STM32H753_R1.bin")
