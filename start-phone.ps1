$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'mobile')
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Mobile dependencies did not install.' }
npx expo start --lan
