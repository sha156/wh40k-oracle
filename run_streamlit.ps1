$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Project virtualenv not found: $pythonExe"
}

Set-Location $projectRoot
& $pythonExe -m streamlit run app.py @args
