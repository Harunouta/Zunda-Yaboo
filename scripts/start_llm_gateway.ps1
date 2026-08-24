# Build and run the OpenAI-compatible LLM gateway in front of LM Studio.
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

docker build -t zunda-llm-gw:local "$repoRoot\gateway"
docker rm -f zunda-llm-gw 2>$null | Out-Null
docker run -d --name zunda-llm-gw --hostname zunda-llm-gw `
  --add-host=host.docker.internal:host-gateway `
  -p 4000:4000 `
  -e GW_LMSTUDIO_HOST=host.docker.internal `
  -e GW_LMSTUDIO_PORT=1234 `
  -e GW_POLICY_MODEL=qwen3-4b-instruct-2507 `
  -e GW_IDS_MODEL=qwen2.5-7b-instruct `
  -e GW_PROSE_MODEL=qwen2.5-14b-instruct `
  -e GW_CRISIS_MODEL=qwen3.6-27b `
  zunda-llm-gw:local

Write-Host "Gateway http://127.0.0.1:4000/health  (LM Studio remains :1234)"
docker exec Zunda-Yaboo python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:4000/health', timeout=5).read().decode())" 2>$null
