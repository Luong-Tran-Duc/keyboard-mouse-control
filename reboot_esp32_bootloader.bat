@echo off
title Reboot ESP32 into Bootloader Mode
cd /d "%~dp0"
python -m desktop.main --reboot-bootloader
pause

