@echo off
REM ============================================================
REM  ORA Desktop Setup -- SAFE CHECK (changes nothing)
REM
REM  HOW TO USE: just double-click this file.
REM
REM  It runs a read-only health check of your dev environment
REM  and prints a PASS / WARN / FAIL table showing what is
REM  installed and what is missing. It writes NOTHING and
REM  changes NOTHING on your machine.
REM
REM  When it finishes, copy the table it printed back to Claude.
REM ============================================================
title ORA Desktop Setup - SAFE CHECK (no changes)
echo.
echo   Running a SAFE, read-only check of your dev environment...
echo   This changes nothing on your machine. Please wait.
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup-desktop-windows.ps1" -SkipInstall
echo.
echo ============================================================
echo   Done. Copy the PASS / WARN / FAIL table above and send it
echo   back to Claude. This check made no changes.
echo ============================================================
echo.
pause
