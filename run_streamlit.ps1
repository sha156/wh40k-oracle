$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    [Console]::Error.WriteLine("Project CPython 3.11 executable not found: $pythonExe")
    exit 1
}

# Validate the project interpreter before importing Streamlit or loading assets.
$runtime = & $pythonExe -c "import sys; print(sys.implementation.name + ':' + str(sys.version_info.major) + '.' + str(sys.version_info.minor))"
if ($LASTEXITCODE -ne 0 -or $runtime -cne 'cpython:3.11') {
    [Console]::Error.WriteLine("This launcher requires a working CPython 3.11 project virtualenv: $pythonExe")
    exit 1
}

# Windows PowerShell 5.1's native invocation loses empty arguments and embedded
# quotes. Encode the Windows argv convention explicitly for both 5.1 and 7.
function ConvertTo-NativeArgument([string] $value) {
    $escaped = [regex]::Replace($value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

Set-Location $projectRoot
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $pythonExe
$startInfo.WorkingDirectory = $projectRoot
$startInfo.UseShellExecute = $false
$launchArgs = @('-m', 'streamlit', 'run', 'app.py') + @($args)
$startInfo.Arguments = ($launchArgs | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '

try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    try {
        $process.WaitForExit()
        $exitCode = $process.ExitCode
    }
    finally {
        $process.Dispose()
    }
}
catch {
    [Console]::Error.WriteLine("Unable to start the project Streamlit process with CPython 3.11.")
    exit 1
}

exit $exitCode
