Set-Location -LiteralPath $PSScriptRoot
$ptePython = if (Test-Path -LiteralPath '.venv\Scripts\python.exe') { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' } else { 'python' }
& $ptePython -m uvicorn pte.api:app --host 127.0.0.1 --port 8000
