#requires -Version 5.1
<#
.SYNOPSIS
    Package Math3D Teaching as a Windows exe.

.DESCRIPTION
    Uses the project virtualenv (.venv) and Math3DTeaching.spec to run PyInstaller.
    Intermediate cache goes to .temp\build and is removed afterwards, so the repo
    root stays clean. Final output: dist\Math3DTeaching\Math3DTeaching.exe

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_exe.ps1
#>
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtualenv not found: $python. Run 'uv sync' first."
}

Write-Host "==> Install / verify PyInstaller"
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    & uv pip install --python $python --upgrade pyinstaller pyinstaller-hooks-contrib
} else {
    & $python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
}

$workPath = Join-Path $repoRoot ".temp\build"
$distPath = Join-Path $repoRoot "dist"

Write-Host "==> Clean previous output"
if (Test-Path -LiteralPath $workPath) { Remove-Item -Recurse -Force -LiteralPath $workPath }
if (Test-Path -LiteralPath $distPath) { Remove-Item -Recurse -Force -LiteralPath $distPath }

Write-Host "==> Run PyInstaller"
& $python -m PyInstaller --noconfirm --workpath $workPath --distpath $distPath "Math3DTeaching.spec"

Write-Host "==> Remove intermediate cache"
if (Test-Path -LiteralPath $workPath) { Remove-Item -Recurse -Force -LiteralPath $workPath }

$exe = Join-Path $distPath "Math3DTeaching\Math3DTeaching.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build failed: $exe not found."
}
Write-Host "==> Done: $exe"
