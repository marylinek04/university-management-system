# Demo preflight - verifies the stack is ready to record/present.
# Usage (from ai_agent\): powershell -ExecutionPolicy Bypass -File scripts\preflight_demo.ps1
$fail = $false
function Check($name, $script, $fix) {
    try { $null = & $script; Write-Host "[OK]   $name" }
    catch { Write-Host "[FAIL] $name  ->  $fix"; $script:fail = $true }
}
Check "docker installed"          { docker --version | Out-Null; if ($LASTEXITCODE) { throw } }                 "install Docker Desktop"
Check "docker compose available"  { docker compose version | Out-Null; if ($LASTEXITCODE) { throw } }           "update Docker Desktop"
Check "compose services running"  { $s = docker compose ps --status running; if ($s -notmatch "agent") { throw } } "run: docker compose up --build"
Check "agent UI healthy (:8501)"  { Invoke-WebRequest -UseBasicParsing http://localhost:8501/_stcore/health -TimeoutSec 5 | Out-Null } "wait for the agent container to become healthy"
Check "ollama reachable (:11434)" { Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/tags -TimeoutSec 5 | Out-Null }      "run: docker compose up ollama ollama-pull"
Check "llama3.1 model pulled"     { $t = (Invoke-WebRequest -UseBasicParsing http://localhost:11434/api/tags -TimeoutSec 5).Content; if ($t -notmatch "llama3.1") { throw } } "run: docker compose up ollama-pull"

if (-not $fail) {
    Write-Host "`nREADY - open http://localhost:8501, send one warm-up message, start recording."
} else {
    Write-Host "`nNOT READY - fix the [FAIL] lines above, then re-run."
    exit 1
}
