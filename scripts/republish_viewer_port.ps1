# One-time: add 127.0.0.1:8765->8765 on Zunda-Yaboo without losing pip (docker commit).
$ErrorActionPreference = "Stop"
$published = $null
try {
  $published = docker port Zunda-Yaboo 8765 2>$null
} catch {
  $published = $null
}
if ($published) {
  Write-Host "8765 already published: $published"
  exit 0
}
$repoRoot = Split-Path -Parent $PSScriptRoot
$modelsHost = if ($env:ZUNDA_AI_HOST) { $env:ZUNDA_AI_HOST } else { Join-Path $repoRoot "models" }
Write-Host "Commit Zunda-Yaboo -> zunda-yaboo:local, recreate with host 127.0.0.1:8765"
docker commit Zunda-Yaboo zunda-yaboo:local
docker stop Zunda-Yaboo
docker rename Zunda-Yaboo Zunda-Yaboo-old
docker run -d --name Zunda-Yaboo --hostname zunda-yaboo -w /workspace `
  -p 8080:80 -p 127.0.0.1:8765:8765 `
  -v "${repoRoot}:/workspace" -v "${modelsHost}:/models" `
  --add-host host.docker.internal:host-gateway `
  -e LM_STUDIO_HOST=host.docker.internal -e LM_STUDIO_PORT=1234 -e ZUNDA_AI_DIR=/models `
  zunda-yaboo:local sleep infinity
if ($LASTEXITCODE -ne 0) {
  docker rename Zunda-Yaboo-old Zunda-Yaboo
  docker start Zunda-Yaboo
  throw "recreate failed; old container restored"
}
docker rm Zunda-Yaboo-old
Write-Host "Published 127.0.0.1:8765 -> container 8765"
