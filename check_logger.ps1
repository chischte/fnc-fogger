$ErrorActionPreference = "Stop"
$taskName = "fnc-fogger-logger"
$statusPath = Join-Path $PSScriptRoot "logger\data\background-status.json"
$task = Get-ScheduledTask -TaskName $taskName
$healthy = $false
if (Test-Path -LiteralPath $statusPath) {
    try {
        $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        $age = ([DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse($status.updated_at)).TotalSeconds
        $healthy = $age -ge 0 -and $age -lt 90
    } catch { $healthy = $false }
}
if ($healthy -and $task.State -eq "Running") { exit 0 }
if ($task.State -eq "Running") {
    Stop-ScheduledTask -TaskName $taskName
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        if ((Get-ScheduledTask -TaskName $taskName).State -ne "Running") { break }
        Start-Sleep -Milliseconds 300
    }
}
Start-ScheduledTask -TaskName $taskName
