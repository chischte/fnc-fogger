param(
    [Parameter(Mandatory=$true)][string]$DeviceUrl,
    [Parameter(Mandatory=$true)][string]$DeviceId,
    [ValidateSet("esp32s3", "esp32c3_supermini")]
    [string]$Environment = "esp32s3",
    [switch]$Yes
)

$firmware = Join-Path $PSScriptRoot ".pio\build\$Environment\firmware.bin"
Push-Location $PSScriptRoot
try {
    $arguments = @("-m", "logger.firmware_update", "--device-id", $DeviceId,
                   "--url", $DeviceUrl, "--file", $firmware)
    if ($Yes) { $arguments += "--yes" }
    & python @arguments
    $updateExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $updateExitCode
