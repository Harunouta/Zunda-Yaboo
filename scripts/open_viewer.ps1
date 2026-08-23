$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONIOENCODING = "utf-8"
Write-Host "Starting Zunda-Yaboo viewer on http://127.0.0.1:8765/"
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
  & py -3 scripts\web_viewer_server.py --open-browser
  exit $LASTEXITCODE
}
& python scripts\web_viewer_server.py --open-browser
