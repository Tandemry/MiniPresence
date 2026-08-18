$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path -LiteralPath ".venv/Scripts/python.exe")) {
    python -m venv .venv
}
$MiniPresencePython = (Resolve-Path ".venv/Scripts/python.exe").Path

& $MiniPresencePython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed with exit code $LASTEXITCODE" }
& $MiniPresencePython -m pytest
if ($LASTEXITCODE -ne 0) { throw "tests failed with exit code $LASTEXITCODE" }
& $MiniPresencePython -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name MiniPresence `
    --icon "src/minipresence/assets/MiniPresence.ico" `
    --add-data "src/minipresence/assets;minipresence/assets" `
    --paths src `
    src/minipresence/__main__.py
if ($LASTEXITCODE -ne 0) { throw "packaging failed with exit code $LASTEXITCODE" }

$Version = & $MiniPresencePython -c "import minipresence; print(minipresence.__version__)"
if ($LASTEXITCODE -ne 0) { throw "version lookup failed with exit code $LASTEXITCODE" }
$Archive = "dist/MiniPresence-$Version-windows-x64.zip"
Compress-Archive -LiteralPath "dist/MiniPresence.exe", "README.md", "LICENSE" -DestinationPath $Archive -Force
Write-Host "Built $Archive"
