<#!
Build a distributable .exe for VAT_Audit_Project on Windows using PyInstaller.
- Default mode: --onedir (folder with exe + libs)
- Pass -OneFile to produce a single exe (larger startup cost)
#>
param(
    [string]$PythonExe = "python",
    [switch]$OneFile
)

$root = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$distName = "VAT_Invoice_Processor"

if ($OneFile.IsPresent) {
    $buildMode = "--onefile"
    $distRoot = Join-Path $root "dist"
    $distBase = $distRoot
}
else {
    $buildMode = "--onedir"
    $distRoot = Join-Path $root "dist"
    $distBase = Join-Path $distRoot $distName
}

$exePath = Join-Path $distBase ("{0}.exe" -f $distName)

# Ensure PyInstaller is available
$pyiVersion = & $PythonExe -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller is not installed. Install it first:" -ForegroundColor Yellow
    Write-Host "$PythonExe -m pip install pyinstaller" -ForegroundColor Cyan
    exit 1
}

Push-Location $root
try {
    $cmd = @(
        $PythonExe, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        $buildMode,
        "--name", $distName,
        "--add-data", "config.yaml;.",
        "--add-data", "config_default.yaml;.",
        "VAT_Invoice_Processor.py"
    )

    Write-Host "Running PyInstaller in $buildMode mode..." -ForegroundColor Green
    $argsList = $cmd[1..($cmd.Length - 1)]
    & $PythonExe @argsList
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Ensure config files and required folders sit next to the exe for runtime reads/writes
    New-Item -ItemType Directory -Force -Path $distBase | Out-Null
    Copy-Item -Path (Join-Path $root "config.yaml"), (Join-Path $root "config_default.yaml") -Destination $distBase -Force
    foreach ($folder in @("Source_Data", "Database", "Outputs")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $distBase $folder) | Out-Null
    }

    Write-Host "Build finished." -ForegroundColor Green
    Write-Host "Executable: $exePath" -ForegroundColor Cyan
    Write-Host "Distribute the entire '$distBase' folder (keep config + Source_Data/Database/Outputs alongside the exe)." -ForegroundColor Yellow
}
finally {
    Pop-Location
}
