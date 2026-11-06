# Cria o ambiente na 1ª execução e roda o transcritor. Argumentos repassados (ex.: arquivos, -f, -r).
$ErrorActionPreference = 'Stop'
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host 'Criando ambiente (.venv)...' -ForegroundColor Cyan
    py -3.12 -m venv (Join-Path $PSScriptRoot '.venv')
    & $py -m pip install -q --upgrade pip
    & $py -m pip install -q -e $PSScriptRoot
}
if (-not (Test-Path (Join-Path $PSScriptRoot 'config.json'))) {
    Write-Host 'config.json ausente: copie config.example.json e ajuste (IA fica desligada).' -ForegroundColor Yellow
}
& $py -m transcritor @args
exit $LASTEXITCODE
