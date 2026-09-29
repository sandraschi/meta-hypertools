$ErrorActionPreference = "Stop"
# src-tauri lives under web_sota/, so the repo root is two levels up.
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendExe = "meta-mcp-backend.exe"
$BackendPort = 10718
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== meta-mcp Tauri Release Build ===" -ForegroundColor Cyan

# Step 0: Verify frontend API base matches the backend port (catches
# "Failed to fetch" before spending 10 minutes on Rust).
$apiFile = Join-Path $Root "web_sota\src\api\client.ts"
if (Test-Path $apiFile) {
    $apiContent = Get-Content $apiFile -Raw
    if ($apiContent -match "127\.0\.0\.1:(\d+)") {
        $apiPort = [int]$Matches[1]
        if ($apiPort -ne $BackendPort) {
            throw "API base in web_sota/src/api/client.ts points to port $apiPort but backend serves on $BackendPort. Production has no Vite proxy - this gives 'Failed to fetch' in the installed app."
        }
        Write-Host "  API base port: $apiPort (matches backend) ✓" -ForegroundColor Green
    }
}

# Step 1: TypeScript lint gate + React frontend build (production API base)
Write-Host "-> [1/4] Building frontend (web_sota)..." -ForegroundColor Yellow
Push-Location (Join-Path $Root "web_sota")
Write-Host "  tsc --noEmit..." -ForegroundColor Gray
$tscOut = npx tsc --noEmit 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $tscOut
    throw "TypeScript compilation failed - fix all errors before building NSIS installer"
}
$env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
Remove-Item Env:\VITE_API_BASE_URL -ErrorAction SilentlyContinue
Pop-Location

# Step 2: PyInstaller backend (onefile)
Write-Host "-> [2/4] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\meta-mcp-backend.spec"
if (-not (Test-Path $specFile)) { throw "Backend spec file not found at $specFile" }
Push-Location $Root
$fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
if (Test-Path $fm) {
    $c = Get-Content $fm -Raw
    if ($c -match 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)') {
        $c = $c -replace 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)', 'except PackageNotFoundError:
    try:
        __version__ = _version("fastmcp")
    except PackageNotFoundError:
        __version__ = "0.0.0"'
        Set-Content $fm -Value $c -Encoding utf8
        Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
    }
}
$pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyiExe)) {
    Write-Host "  pyinstaller missing from project venv - adding as dev dependency" -ForegroundColor Yellow
    uv add --dev pyinstaller pefile altgraph
    uv sync
}
Remove-Item "$Root\dist\$BackendExe" -Force -ErrorAction SilentlyContinue
Get-Process meta-mcp-backend -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
& $pyiExe "$specFile" --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Pop-Location

# Gate: smoke-test the frozen binary on an ephemeral port (proves serving,
# not just starting - hits /health and one real JSON route).
$frozenExe = "$Root\dist\$BackendExe"
Write-Host "  Smoke-testing frozen binary..." -ForegroundColor Yellow
$testPort = 11999
$testProc = Start-Process -FilePath $frozenExe -NoNewWindow -PassThru `
    -RedirectStandardError "$Root\dist\pyi-crash.log" `
    -EnvironmentVariables @{ MCP_PORT = "$testPort"; MCP_HOST = "127.0.0.1" }
Start-Sleep -Seconds 12
try {
    if ($testProc.HasExited) {
        $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw -ErrorAction SilentlyContinue
        throw "Frozen binary crashed on launch (exit $($testProc.ExitCode)):`n$crash"
    }
    $health = Invoke-WebRequest "http://127.0.0.1:$testPort/health" -UseBasicParsing -TimeoutSec 10
    if ($health.StatusCode -ne 200) { throw "Frozen /health returned $($health.StatusCode)" }
    $ctx = Invoke-WebRequest "http://127.0.0.1:$testPort/api/v1/chat/context" -UseBasicParsing -TimeoutSec 15
    if ($ctx.StatusCode -ne 200) { throw "Frozen chat/context returned $($ctx.StatusCode)" }
    $errText = Get-Content "$Root\dist\pyi-crash.log" -Raw -ErrorAction SilentlyContinue
    if ($errText -match "No module named|Traceback \(most recent call last\)") {
        throw "Frozen binary logged import failure:`n$errText"
    }
    Write-Host "  Frozen binary smoke test PASSED (/health + chat/context)" -ForegroundColor Green
} finally {
    if (-not $testProc.HasExited) { $testProc.Kill(); $testProc.Dispose() }
    Remove-Item "$Root\dist\pyi-crash.log" -Force -ErrorAction SilentlyContinue
}

# Step 3: Embed in Tauri resources (+ dev fallback) with size gate
Write-Host "-> [3/4] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\dist\$BackendExe"
$sizeMB = (Get-Item $src).Length / 1MB
if ($sizeMB -lt 5) {
    throw "Backend exe is only $([math]::Round($sizeMB, 1)) MB - PyInstaller produced an empty/broken binary. Check build\meta-mcp-backend\warn-*.txt for hidden import warnings."
}
Copy-Item $src "$ResourceDir\$BackendExe" -Force
Copy-Item $src "$DevDir\meta-mcp-backend-$Triple.exe" -Force
Write-Host "  Backend exe: $([math]::Round($sizeMB, 1)) MB" -ForegroundColor Green
$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example (never .env) OK" -ForegroundColor Green
}
Remove-Item "$PSScriptRoot\target\release\$BackendExe" -Force -ErrorAction SilentlyContinue

# Step 4: Single NSIS installer
Write-Host "-> [4/4] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
npx @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
