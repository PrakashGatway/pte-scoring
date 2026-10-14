param([switch]$SkipModelDownload)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-PtePython {
    param([string[]]$Arguments)
    & $script:PtePython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE" }
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment. Install Python 3.10 or newer.' }
}
$script:PtePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Invoke-PtePython -Arguments @('-m','pip','install','-r','requirements.txt','-r','requirements-test.txt')
Invoke-PtePython -Arguments @('-m','pip','install','llama-cpp-python==0.3.36','--only-binary=:all:','--extra-index-url','https://abetlen.github.io/llama-cpp-python/whl/cpu')
if (-not $SkipModelDownload) { Invoke-PtePython -Arguments @('download_models.py') }
Write-Host 'Setup complete. Run .\run.ps1 and open http://127.0.0.1:8765/'
