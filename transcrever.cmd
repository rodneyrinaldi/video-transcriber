@echo off
rem Duplo clique: modo interativo. Arrastar arquivos sobre este .cmd: transcreve direto.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0transcrever.ps1" %*
if "%~1"=="" exit /b
pause
