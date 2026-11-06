# Gera dist\video-transcriber.exe (onefile). Requer: pip install -e ".[dev]"
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$py = '.venv\Scripts\python.exe'
& $py -m PyInstaller --noconfirm --clean --onefile --console `
    --name video-transcriber `
    --paths . `
    --collect-all faster_whisper `
    --collect-binaries ctranslate2 `
    --collect-binaries onnxruntime `
    --collect-data av `
    --exclude-module torch --exclude-module tkinter `
    transcritor\__main__.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Copy-Item config.example.json dist\config.example.json -Force
Write-Host "OK: dist\video-transcriber.exe (copie config.json para dist\)" -ForegroundColor Green
