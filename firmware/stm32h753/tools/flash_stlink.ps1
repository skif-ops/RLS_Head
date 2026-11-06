param(
    [Parameter(Mandatory = $true)]
    [string]$Image,
    [string]$Programmer = "STM32_Programmer_CLI.exe",
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$resolvedImage = (Resolve-Path -LiteralPath $Image).Path
$programmerCommand = Get-Command $Programmer -ErrorAction SilentlyContinue
if (-not $programmerCommand) {
    throw "STM32_Programmer_CLI.exe was not found. Install STM32CubeProgrammer or pass -Programmer."
}

if ($VerifyOnly) {
    & $programmerCommand.Source -c port=SWD mode=UR reset=HWrst -v $resolvedImage
} else {
    & $programmerCommand.Source -c port=SWD mode=UR reset=HWrst -e all -d $resolvedImage -v -rst
}

if ($LASTEXITCODE -ne 0) {
    throw "STM32CubeProgrammer returned exit code $LASTEXITCODE."
}
