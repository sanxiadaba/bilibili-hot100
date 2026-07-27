param(
    [ValidateSet('Start', 'Stop')]
    [string]$Action = 'Start',
    [ValidateSet('all', 'frontend', 'backend')]
    [string]$Mode = 'all',
    [string]$DataDir,
    [switch]$Detached
)

$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectDir 'bilibili-hot100-backend'
$FrontendDir = Join-Path $ProjectDir 'bilibili-hot100-vue3-ts'
$PidDir = Join-Path $ProjectDir '.pids'
$BackendPort = 8000
$FrontendPort = 3000
if (-not $DataDir) { $DataDir = Join-Path $ProjectDir 'data' }
$DataDir = [System.IO.Path]::GetFullPath($DataDir)

function Get-OwnedProcess([string]$Name, [string]$Needle) {
    $pidFile = Join-Path $PidDir "$Name.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { return $null }
    $savedPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($savedPid -notmatch '^\d+$') {
        Remove-Item -LiteralPath $pidFile -Force
        return $null
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$savedPid" -ErrorAction SilentlyContinue
    if (-not $process -or $process.CommandLine -notlike "*$ProjectDir*" -or $process.CommandLine -notlike "*$Needle*") {
        Remove-Item -LiteralPath $pidFile -Force
        return $null
    }
    return $process
}

function Assert-PortAvailable([int]$Port, $OwnedProcess) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $listener) { return }
    if ($OwnedProcess) {
        foreach ($listenerPid in $listener.OwningProcess) {
            if ($listenerPid -eq $OwnedProcess.ProcessId) { return }
            $listenerProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" -ErrorAction SilentlyContinue
            if ($listenerProcess -and $listenerProcess.ParentProcessId -eq $OwnedProcess.ProcessId) { return }
        }
    }
    $owners = ($listener.OwningProcess | Sort-Object -Unique) -join ', '
    throw "Port $Port is already used by another process (PID: $owners). Stop it or choose another port."
}

function Stop-OwnedService([string]$Name, [string]$Needle) {
    $process = Get-OwnedProcess $Name $Needle
    if (-not $process) {
        Write-Host "  $Name is not running."
        return
    }
    & taskkill.exe /PID $process.ProcessId /T /F | Out-Null
    Remove-Item -LiteralPath (Join-Path $PidDir "$Name.pid") -Force -ErrorAction SilentlyContinue
    Write-Host "  Stopped $Name (PID $($process.ProcessId))."
}

function Wait-ForUrl([string]$Name, [string]$Url) {
    $deadline = (Get-Date).AddSeconds(45)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "  $Name is ready: $Url"
                return
            }
        } catch { }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "$Name did not become ready within 45 seconds. Check logs in $PidDir."
}

function Get-Sha256([string]$Path) {
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '')
    } finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

if ($Action -eq 'Stop') {
    Write-Host 'Stopping Bilibili Hot100 services...'
    if ($Mode -ne 'frontend') { Stop-OwnedService 'backend' 'uvicorn main:app' }
    if ($Mode -ne 'backend') { Stop-OwnedService 'frontend' 'vite' }
    if (Test-Path -LiteralPath $PidDir) {
        $remaining = Get-ChildItem -LiteralPath $PidDir -Force -ErrorAction SilentlyContinue
        if (-not $remaining) { Remove-Item -LiteralPath $PidDir -Force }
    }
    exit 0
}

New-Item -ItemType Directory -Path $PidDir, $DataDir -Force | Out-Null
$backendProcess = Get-OwnedProcess 'backend' 'uvicorn main:app'
$frontendProcess = Get-OwnedProcess 'frontend' 'vite'

if ($Mode -ne 'frontend') {
    Assert-PortAvailable $BackendPort $backendProcess
    if (-not $backendProcess) {
        $venvDir = Join-Path $BackendDir '.venv'
        $venvPython = Join-Path $venvDir 'Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $venvPython)) {
            $python = (Get-Command python.exe -ErrorAction Stop).Source
            & $python -m venv $venvDir
        }
        $requirements = Join-Path $BackendDir 'requirements.txt'
        $marker = Join-Path $venvDir '.requirements.sha256'
        $hash = Get-Sha256 $requirements
        $installedHash = if (Test-Path -LiteralPath $marker) { (Get-Content -LiteralPath $marker -Raw).Trim() } else { '' }
        $needsBackendInstall = $hash -ne $installedHash
        if (-not $needsBackendInstall) {
            & $venvPython -c 'import aiofiles, aiohttp, fastapi, pydantic, uvicorn'
            $needsBackendInstall = $LASTEXITCODE -ne 0
        }
        if ($needsBackendInstall) {
            & $venvPython -m pip install -r $requirements
            if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
            Set-Content -LiteralPath $marker -Value $hash -NoNewline
        }
        $env:BILIBILI_DATA_DIR = $DataDir
        $backendProcess = Start-Process -FilePath $venvPython `
            -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port',"$BackendPort" `
            -WorkingDirectory $BackendDir -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $PidDir 'backend.out.log') `
            -RedirectStandardError (Join-Path $PidDir 'backend.err.log') -PassThru
        Set-Content -LiteralPath (Join-Path $PidDir 'backend.pid') -Value $backendProcess.Id -NoNewline
    } else {
        Write-Host "  Backend already running (PID $($backendProcess.ProcessId))."
    }
    Wait-ForUrl 'Backend' "http://127.0.0.1:$BackendPort/api/status"
}

if ($Mode -ne 'backend') {
    Assert-PortAvailable $FrontendPort $frontendProcess
    if (-not $frontendProcess) {
        $lockFile = Join-Path $FrontendDir 'package-lock.json'
        $nodeModules = Join-Path $FrontendDir 'node_modules'
        $frontendMarker = Join-Path $nodeModules '.package-lock.sha256'
        $lockHash = Get-Sha256 $lockFile
        $installedLockHash = if (Test-Path -LiteralPath $frontendMarker) { (Get-Content -LiteralPath $frontendMarker -Raw).Trim() } else { '' }
        if (-not (Test-Path -LiteralPath $nodeModules) -or $lockHash -ne $installedLockHash) {
            Push-Location $FrontendDir
            try { & npm.cmd ci } finally { Pop-Location }
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
            Set-Content -LiteralPath $frontendMarker -Value $lockHash -NoNewline
        }
        $node = (Get-Command node.exe -ErrorAction Stop).Source
        $vite = Join-Path $FrontendDir 'node_modules\vite\bin\vite.js'
        $frontendProcess = Start-Process -FilePath $node `
            -ArgumentList $vite,'--host','127.0.0.1','--port',"$FrontendPort" `
            -WorkingDirectory $FrontendDir -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $PidDir 'frontend.out.log') `
            -RedirectStandardError (Join-Path $PidDir 'frontend.err.log') -PassThru
        Set-Content -LiteralPath (Join-Path $PidDir 'frontend.pid') -Value $frontendProcess.Id -NoNewline
    } else {
        Write-Host "  Frontend already running (PID $($frontendProcess.ProcessId))."
    }
    Wait-ForUrl 'Frontend' "http://127.0.0.1:$FrontendPort"
}

@(
    "Frontend=http://127.0.0.1:$FrontendPort"
    "Backend=http://127.0.0.1:$BackendPort"
    "Docs=http://127.0.0.1:$BackendPort/docs"
) | Set-Content -LiteralPath (Join-Path $PidDir 'services.txt')

Write-Host 'Bilibili Hot100 services started successfully.'
if (-not $Detached) {
    Start-Process "http://127.0.0.1:$FrontendPort"
    Write-Host 'Press Ctrl+C to stop the services.'
    try {
        while ($true) { Start-Sleep -Seconds 1 }
    } finally {
        if ($Mode -ne 'frontend') { Stop-OwnedService 'backend' 'uvicorn main:app' }
        if ($Mode -ne 'backend') { Stop-OwnedService 'frontend' 'vite' }
    }
}
