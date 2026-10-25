$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'backend')
if (!(Test-Path '.venv')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12, then run this script again.' }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependencies did not install.' }
$terminalPort = if ($env:PORT) { $env:PORT } else { '8000' }
& .\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port $terminalPort --workers 1
