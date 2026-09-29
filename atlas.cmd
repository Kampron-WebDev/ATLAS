@echo off
rem Lets you type `atlas` from cmd.exe or PowerShell when this folder is on PATH.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0atlas.ps1" %*
