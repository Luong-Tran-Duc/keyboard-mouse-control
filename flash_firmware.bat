@echo off
chcp 65001 >nul
title "ESP32-S3 Firmware Build and Flash Tool"

:: Set essential tool paths to PATH for all child processes (including bootloader subproject cmd.exe)
set "PATH=C:\Espressif\tools\ninja\1.12.1;C:\Espressif\tools\cmake\4.0.3\bin;C:\Espressif\tools\xtensa-esp-elf\esp-15.2.0_20251204\xtensa-esp-elf\bin;C:\Espressif\tools\python\v6.0.2\venv\Scripts;%PATH%"
set "IDF_TOOLS_PATH=C:\Espressif\tools"
set "IDF_PATH=D:\esp\v6.0.2\esp-idf"
set "IDF_PYTHON_ENV_PATH=C:\Espressif\tools\python\v6.0.2\venv"
set "IDF_CCACHE_ENABLE=0"
set "CMAKE_MAKE_PROGRAM=C:\Espressif\tools\ninja\1.12.1\ninja.exe"

cls
echo ====================================================
echo      ESP32-S3 Firmware Build and Flash Tool
echo ====================================================
echo [1] Build + Flash Firmware
echo [2] Flash Only (Skip Build)
echo [3] Exit
echo ====================================================
choice /c 123 /n /m "Select option (1, 2, 3): "
set "MENU_CHOICE=%ERRORLEVEL%"

if "%MENU_CHOICE%"=="1" (
    set "FLASH_MODE=BuildAndFlash"
) else if "%MENU_CHOICE%"=="2" (
    set "FLASH_MODE=FlashOnly"
) else (
    echo Exiting...
    exit /b 0
)

:: Clear previous build log if building from scratch
if "%FLASH_MODE%"=="BuildAndFlash" (
    if exist "%~dp0firmware\build.txt" del /f /q "%~dp0firmware\build.txt" >nul 2>&1
    if exist "%~dp0build.txt" del /f /q "%~dp0build.txt" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0flash_firmware.ps1" -Mode %FLASH_MODE%
pause
