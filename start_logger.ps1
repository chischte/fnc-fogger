$ErrorActionPreference = "Stop"
$python = (Get-Command python.exe -ErrorAction Stop).Source
Push-Location $PSScriptRoot
try {
    & $python -c "from logger.background_process import ensure_background_logger; from pathlib import Path; ensure_background_logger(Path('logger/data'))"
    if ($LASTEXITCODE -ne 0) { throw "Background logger could not be started." }
} finally {
    Pop-Location
}
