@echo off
title KM Bridge Client - Share Keyboard ^& Mouse
cd /d "%~dp0"
python -m desktop.main %*
pause

