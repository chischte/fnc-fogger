$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start_logger.ps1")
$viewerScript = Join-Path $PSScriptRoot "logger\viewer.py"
$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
Start-Process -FilePath $pythonw -ArgumentList "`"$viewerScript`"" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
