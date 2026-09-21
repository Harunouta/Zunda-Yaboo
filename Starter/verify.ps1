# Health checks for Starter stack (gateway, viewer, dry-run).
$ErrorActionPreference = "Stop"
$container = "Zunda-Yaboo"
$failed = 0

function Ok($msg) { Write-Host "[OK] $msg" }
function Bad($msg) { Write-Host "[FAIL] $msg"; $script:failed++ }

Write-Host "=== Starter verify ==="

$gw = docker inspect -f "{{.State.Running}}" zunda-llm-gw 2>$null
if ($gw -eq "true") { Ok "zunda-llm-gw running" } else { Bad "zunda-llm-gw not running" }

$zy = docker inspect -f "{{.State.Running}}" $container 2>$null
if ($zy -eq "true") { Ok "Zunda-Yaboo running" } else { Bad "Zunda-Yaboo not running" }

try {
  $h = Invoke-WebRequest -Uri "http://127.0.0.1:4000/health" -UseBasicParsing -TimeoutSec 5
  if ($h.StatusCode -ge 200 -and $h.StatusCode -lt 500) { Ok "gateway :4000/health" } else { Bad "gateway health status $($h.StatusCode)" }
} catch {
  Bad "gateway :4000/health — $($_.Exception.Message)"
}

foreach ($path in @("/", "/compare.html")) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765$path" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { Ok "viewer http://127.0.0.1:8765$path" } else { Bad "viewer $path status $($r.StatusCode)" }
  } catch {
    Bad "viewer $path — $($_.Exception.Message)"
  }
}

if ($zy -eq "true") {
  docker exec -w /workspace -e PYTHONPATH=/workspace $container python -m src.main --no-llm --standard zunda --start 1853-01 --end 1853-03 --run-name starter_verify_dry
  if ($LASTEXITCODE -eq 0) { Ok "dry-run 1853-01..03" } else { Bad "dry-run failed" }
} else {
  Bad "skip dry-run (container down)"
}

if ($failed -gt 0) {
  Write-Host "=== FAILED ($failed) — see Starter/VERIFY.md ==="
  exit 1
}
Write-Host "=== ALL OK ==="
exit 0
