param(
    [ValidateSet("BuildAndFlash", "FlashOnly", "")]
    [string]$Mode = ""
)

# ESP32-S3 Firmware Build & Flash Script
# Auto-detects ESP32 COM port (filters Bluetooth), waits for device, builds & flashes

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "ESP32-S3 Auto Build & Flash Tool"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "      ESP32-S3 Auto Build & Flash Tool              " -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($Mode)) {
    Write-Host "`nSelect Flash Mode:" -ForegroundColor Cyan
    Write-Host "  [1] Build and Flash" -ForegroundColor White
    Write-Host "  [2] Flash Only (Skip Build)" -ForegroundColor White
    $choice = Read-Host "Enter option (1/2, default 1)"
    if ($choice -eq "2") {
        $Mode = "FlashOnly"
    } else {
        $Mode = "BuildAndFlash"
    }
}

# 0. Clean old build.txt immediately on launch
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$firmwareDir = $scriptDir
if (Test-Path (Join-Path $scriptDir "firmware")) {
    $firmwareDir = Join-Path $scriptDir "firmware"
}
$buildLogPath = Join-Path $firmwareDir "build.txt"
if (Test-Path $buildLogPath) {
    Remove-Item -Path $buildLogPath -Force -ErrorAction SilentlyContinue
}

# 1. Load official ESP-IDF PowerShell profile if present
$espProfile = "C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1"
if (Test-Path $espProfile) {
    . $espProfile
}

# 2. Sanitize and prepend critical ESP-IDF tool directories to PATH
$toolPaths = @(
    "C:\Espressif\tools\ninja\1.12.1",
    "C:\Espressif\tools\cmake\4.0.3\bin",
    "C:\Espressif\tools\idf-exe\1.0.3",
    "C:\Espressif\tools\xtensa-esp-elf\esp-15.2.0_20251204\xtensa-esp-elf\bin",
    "C:\Espressif\tools\python\v6.0.2\venv\Scripts"
)
$sanitizedList = @()
foreach ($item in ($env:PATH -split ';')) {
    $trimmed = $item.Trim().TrimEnd('\')
    if ($trimmed -and -not ($sanitizedList -contains $trimmed)) {
        $sanitizedList += $trimmed
    }
}
$cleanPath = ($toolPaths + $sanitizedList) -join ";"
$env:PATH = $cleanPath
[System.Environment]::SetEnvironmentVariable("PATH", $cleanPath, "Process")

# Guarantee environment variables in Win32 Process Block
$env:IDF_TOOLS_PATH = "C:\Espressif\tools"
$env:IDF_COMPONENT_LOCAL_STORAGE_URL = "file://C:\Espressif\tools"
$env:IDF_PATH = "D:\esp\v6.0.2\esp-idf"
$env:ESP_ROM_ELF_DIR = "C:\Espressif\tools\esp-rom-elfs\20241011/"
$env:OPENOCD_SCRIPTS = "C:\Espressif\tools\openocd-esp32\v0.12.0-esp32-20260424/openocd-esp32/share/openocd/scripts"
$env:IDF_PYTHON_ENV_PATH = "C:\Espressif\tools\python\v6.0.2\venv"
$env:ESP_CLANG_LIBS_PATH = "C:\Espressif\tools\esp-clang-libs\esp-20.1.1_20250829/esp-clang/lib"
$env:IDF_CCACHE_ENABLE = "0"
$env:ESP_IDF_VERSION = "6.0"

[System.Environment]::SetEnvironmentVariable("IDF_TOOLS_PATH", "C:\Espressif\tools", "Process")
[System.Environment]::SetEnvironmentVariable("IDF_COMPONENT_LOCAL_STORAGE_URL", "file://C:\Espressif\tools", "Process")
[System.Environment]::SetEnvironmentVariable("IDF_PATH", "D:\esp\v6.0.2\esp-idf", "Process")
[System.Environment]::SetEnvironmentVariable("ESP_ROM_ELF_DIR", "C:\Espressif\tools\esp-rom-elfs\20241011/", "Process")
[System.Environment]::SetEnvironmentVariable("OPENOCD_SCRIPTS", "C:\Espressif\tools\openocd-esp32\v0.12.0-esp32-20260424/openocd-esp32/share/openocd/scripts", "Process")
[System.Environment]::SetEnvironmentVariable("IDF_PYTHON_ENV_PATH", "C:\Espressif\tools\python\v6.0.2\venv", "Process")
[System.Environment]::SetEnvironmentVariable("ESP_CLANG_LIBS_PATH", "C:\Espressif\tools\esp-clang-libs\esp-20.1.1_20250829/esp-clang/lib", "Process")
[System.Environment]::SetEnvironmentVariable("IDF_CCACHE_ENABLE", "0", "Process")
[System.Environment]::SetEnvironmentVariable("ESP_IDF_VERSION", "6.0", "Process")

$idfPython = "C:\Espressif\tools\python\v6.0.2\venv\Scripts\python.exe"
$idfScript = "D:\esp\v6.0.2\esp-idf\tools\idf.py"

# 3. Prepare fresh build.txt
Set-Location $firmwareDir
"=== ESP32-S3 BUILD LOG $(Get-Date) ===" | Out-File -FilePath $buildLogPath -Force -Encoding utf8

function Run-Idf {
    param([string[]]$Arguments)
    $argStr = ($Arguments | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join " "
    $displayCmd = "idf.py $argStr"
    Write-Host "`n>>> $displayCmd" -ForegroundColor Cyan
    "`n>>> $displayCmd" | Out-File -FilePath $buildLogPath -Append -Encoding utf8

    cmd /c "`"$idfPython`" `"$idfScript`" $argStr" 2>&1 | ForEach-Object {
        $line = $_.ToString()
        Write-Host $line
        $line | Out-File -FilePath $buildLogPath -Append -Encoding utf8
    }
    return $LASTEXITCODE
}

# 4. Handle build phase according to chosen Mode
if ($Mode -eq "FlashOnly") {
    Write-Host "`n[*] Selected Mode: Flash Only (skipping build phase)..." -ForegroundColor Yellow
    $buildDir = Join-Path $firmwareDir "build"
    $binFile = Join-Path $buildDir "km_bridge_firmware.bin"
    $flasherArgs = Join-Path $buildDir "flasher_args.json"

    if (-not (Test-Path $buildDir) -or (-not (Test-Path $binFile) -and -not (Test-Path $flasherArgs))) {
        Write-Host "`n[ERROR] Previous build files not found in '$buildDir'!" -ForegroundColor Red
        Write-Host "[INFO] Please run 'Build and Flash' first to compile the firmware." -ForegroundColor Yellow
        Read-Host "Press Enter to exit..."
        exit 1
    }
    Write-Host "[OK] Existing firmware binary verified. Ready to flash." -ForegroundColor Green
} else {
    Write-Host "[*] Cleaning previous build directory..." -ForegroundColor Yellow
    if (Test-Path "build") {
        Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 300
    }
    Write-Host "[OK] Build directory cleaned successfully!" -ForegroundColor Green

    Write-Host "[*] Building firmware..." -ForegroundColor Cyan
    $buildRet = Run-Idf @("build")
    if ($buildRet -ne 0) {
        Write-Host "`n[X] BUILD FAILED! Check details in: $buildLogPath" -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit $buildRet
    }
    Write-Host "[OK] Firmware build finished successfully!" -ForegroundColor Green
}

# 6. Intelligent auto-detection of ESP32 COM port (Filtering Bluetooth out)
function Find-Esp32Port {
    try {
        $pnpPorts = Get-CimInstance Win32_PnPEntity -Filter "ClassGuid = '{4d36e978-e325-11ce-bfc1-08002be10318}'" -ErrorAction SilentlyContinue | Where-Object {
            $_.DeviceID -notlike "BTHENUM*" -and $_.Name -notlike "*Bluetooth*"
        }
        foreach ($p in $pnpPorts) {
            if ($p.Name -match '\((COM\d+)\)') {
                return [PSCustomObject]@{
                    Port = $matches[1]
                    Name = $p.Name
                }
            }
        }
    } catch {}

    # Fallback to serial ports
    try {
        $sPorts = Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue | Where-Object {
            $_.Description -notlike "*Bluetooth*"
        }
        if ($sPorts) {
            $first = $sPorts | Select-Object -First 1
            return [PSCustomObject]@{
                Port = $first.DeviceID
                Name = "$($first.DeviceID) - $($first.Description)"
            }
        }
    } catch {}

    return $null
}

# Try sending Wi-Fi remote reboot packet (0xAA) to port 9876 (broadcast + unicast)
try {
    $udpClient = New-Object System.Net.Sockets.UdpClient
    $udpClient.EnableBroadcast = $true
    $rebootPkt = [byte[]]@(0xAA)
    $broadcastEp = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Broadcast, 9876)
    $udpClient.Send($rebootPkt, $rebootPkt.Length, $broadcastEp) | Out-Null
    $unicastEp = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Parse("192.168.1.216"), 9876)
    $udpClient.Send($rebootPkt, $rebootPkt.Length, $unicastEp) | Out-Null
    $udpClient.Close()
} catch {}

Write-Host "`n[*] Dang tu dong tim cong COM cua ESP32 (da bo qua Bluetooth)..." -ForegroundColor Yellow

$espInfo = Find-Esp32Port
$waitCount = 0

while ($null -eq $espInfo) {
    if ($waitCount -eq 0) {
        Write-Host ">>> Chua thay ESP32 o che do COM. Vui long Giu BOOT + Nhan RST de vao Download Mode..." -ForegroundColor Magenta
    }
    Start-Sleep -Milliseconds 800
    $espInfo = Find-Esp32Port
    $waitCount++
    if ($waitCount % 10 -eq 0) {
        Write-Host "    [Dang doi ket noi...]" -ForegroundColor DarkGray
    }
}

$selectedPort = $espInfo.Port
Write-Host "`n[TU DONG PHAT HIEN] Tim thay ESP32 tai: $($espInfo.Name)" -ForegroundColor Green
Write-Host "[*] Tien hanh nap firmware vao $selectedPort..." -ForegroundColor Green
Start-Sleep -Seconds 1

# 7. Flash firmware and log output
$flashRet = Run-Idf @("-p", $selectedPort, "flash")
if ($flashRet -eq 0) {
    Write-Host "`n====================================================" -ForegroundColor Green
    Write-Host "   NAP FIRMWARE THANH CONG 100%!                    " -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Green
} else {
    Write-Host "`n[X] NAP FIRMWARE THAT BAI! Xem chi tiet trong: $buildLogPath" -ForegroundColor Red
}

