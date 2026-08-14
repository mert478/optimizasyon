<#
.SYNOPSIS
    Ayyildiz Sentinel Pro - Tek Komutla Kurulum Betigi

.DESCRIPTION
    Bu betik, https://github.com/mert478/optimizasyon
    adresindeki acik kaynakli Sentinel Pro uygulamasini indirir ve calistirir.
    Herhangi bir uzak sunucuya veri gondermez, herhangi bir lisans/etkinlestirme
    kirma araci ICERMEZ. Sadece bu projenin kendi Python dosyasini indirip
    calistiran basit bir yukleyicidir.

    Calistirmadan once icerigini incelemenizi tavsiye ederiz:
    https://github.com/mert478/optimizasyon/blob/main/install.ps1

.NOTES
    Kullanim:  irm https://raw.githubusercontent.com/mert478/optimizasyon/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"

$RepoOwner   = "mert478"
$RepoName    = "optimizasyon"
$RepoBranch  = "main"
$ScriptFile  = "sentinel_pro.py"
$InstallDir  = Join-Path $env:LOCALAPPDATA "SentinelPro"
$RawBaseUrl  = "https://raw.githubusercontent.com/$RepoOwner/$RepoName/$RepoBranch"

function Write-Info($msg)  { Write-Host "[Sentinel Pro] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[Sentinel Pro] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "[Sentinel Pro] $msg" -ForegroundColor Yellow }
function Write-Err2($msg)  { Write-Host "[Sentinel Pro] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "===============================================" -ForegroundColor DarkCyan
Write-Host "   Ayyildiz Sentinel Pro - Kurulum Baslatiliyor " -ForegroundColor DarkCyan
Write-Host "===============================================" -ForegroundColor DarkCyan
Write-Host ""

# 1) Python kontrolu
Write-Info "Python kurulumu kontrol ediliyor..."
$pythonCmd = $null
foreach ($candidate in @("python", "py")) {
    try {
        $verOutput = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $verOutput -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 9) {
                $pythonCmd = $candidate
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Err2 "Python 3.9 veya uzeri bulunamadi."
    Write-Warn2 "Lutfen once Python'u yukleyin: https://www.python.org/downloads/windows/"
    Write-Warn2 "Kurulum sirasinda 'Add python.exe to PATH' secenegini isaretlemeyi unutmayin."
    $openDownload = Read-Host "Python indirme sayfasi tarayicida acilsin mi? (E/H)"
    if ($openDownload -match "^[eE]") {
        Start-Process "https://www.python.org/downloads/windows/"
    }
    return
}
Write-Ok "Python bulundu: $pythonCmd"

# 2) Gerekli paket kurulumu
Write-Info "Gerekli Python paketleri kontrol ediliyor (psutil)..."
& $pythonCmd -m pip install --upgrade --quiet psutil
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "pip ile kurulum basarisiz oldu, --user secenegiyle tekrar deneniyor..."
    & $pythonCmd -m pip install --user --upgrade --quiet psutil
}
Write-Ok "Bagimliliklar hazir."

# 3) Kurulum klasoru olustur
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 4) Uygulama dosyasini indir
$targetPath = Join-Path $InstallDir $ScriptFile
$downloadUrl = "$RawBaseUrl/$ScriptFile"
Write-Info "Uygulama indiriliyor: $downloadUrl"

try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $targetPath -UseBasicParsing
    Write-Ok "Indirme tamamlandi: $targetPath"
} catch {
    Write-Err2 "Indirme basarisiz oldu: $_"
    return
}

# 5) Baslat Menusu kisayolu (istege bagli)
$createShortcut = Read-Host "Baslat Menusune kisayol eklensin mi? (E/H)"
if ($createShortcut -match "^[eE]") {
    try {
        $wshell = New-Object -ComObject WScript.Shell
        $startMenuPath = [Environment]::GetFolderPath("StartMenu") + "\Programs\Ayyildiz Sentinel Pro.lnk"
        $shortcut = $wshell.CreateShortcut($startMenuPath)
        $pythonwPath = (Get-Command $pythonCmd).Source -replace "python.exe$", "pythonw.exe"
        if (-not (Test-Path $pythonwPath)) { $pythonwPath = (Get-Command $pythonCmd).Source }
        $shortcut.TargetPath = $pythonwPath
        $shortcut.Arguments = "`"$targetPath`""
        $shortcut.WorkingDirectory = $InstallDir
        $shortcut.IconLocation = $pythonwPath
        $shortcut.Save()
        Write-Ok "Kisayol olusturuldu: $startMenuPath"
    } catch {
        Write-Warn2 "Kisayol olusturulamadi (onemli degil, uygulama yine de calisacak)."
    }
}

# 6) Uygulamayi baslat
Write-Info "Ayyildiz Sentinel Pro baslatiliyor..."
Start-Process $pythonCmd -ArgumentList "`"$targetPath`""

Write-Host ""
Write-Ok "Kurulum tamamlandi! Uygulama klasoru: $InstallDir"
Write-Host ""
