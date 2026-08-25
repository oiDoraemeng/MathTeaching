$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$webRoot = Join-Path $repoRoot "ui\agent_web"
Push-Location $webRoot
try {
    pnpm install --frozen-lockfile
    pnpm build
    $index = Join-Path $webRoot "dist\index.html"
    $manifest = Join-Path $webRoot "dist\manifest.json"
    if (!(Test-Path -LiteralPath $index) -or !(Test-Path -LiteralPath $manifest)) {
        throw "MathAgent Web UI build did not produce dist/index.html and dist/manifest.json"
    }
} finally {
    Pop-Location
}
