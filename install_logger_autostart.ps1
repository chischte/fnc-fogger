$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
$action = New-ScheduledTaskAction -Execute $pythonw -Argument '-m logger.background' -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
Register-ScheduledTask -TaskName 'fnc-fogger-logger' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Record all registered FNC Fogger devices independently of the viewer.' -Force | Out-Null

$watchdogScript = Join-Path $root 'check_logger.ps1'
$watchdogAction = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$watchdogScript`"" -WorkingDirectory $root
$watchdogTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$watchdogSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'fnc-fogger-logger-watchdog' -Action $watchdogAction -Trigger $watchdogTrigger -Settings $watchdogSettings -Principal $principal -Description 'Restart FNC Fogger logger when its heartbeat is stale or task stopped.' -Force | Out-Null

# Back up the obsolete predecessor before disabling its broken autostart.
$legacy = Get-ScheduledTask -TaskName 'fastnchip-sensor-logger' -ErrorAction SilentlyContinue
if ($legacy -and ($legacy.Actions.Arguments -match 'fnc-sensors[\\/]logger[\\/]logger.py')) {
    $backup = Join-Path $root 'logger\data\recovery'
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Export-ScheduledTask -TaskName $legacy.TaskName | Set-Content -LiteralPath (Join-Path $backup 'legacy-logger-task.xml') -Encoding UTF8
    Disable-ScheduledTask -TaskName $legacy.TaskName | Out-Null
}
Start-ScheduledTask -TaskName 'fnc-fogger-logger'
Get-ScheduledTask -TaskName 'fnc-fogger-logger','fnc-fogger-logger-watchdog' | Select-Object TaskName,State
