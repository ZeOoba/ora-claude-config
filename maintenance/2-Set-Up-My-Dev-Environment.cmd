@echo off
REM ============================================================
REM  ORA Desktop Setup -- FULL SETUP
REM
REM  HOW TO USE: double-click this file to actually set up the
REM  oxford-command-center dev environment. It installs any
REM  missing Node / Git (for your user account), configures git,
REM  and installs the project dependencies. It never touches
REM  Claude Code and never deletes anything. Safe to run more
REM  than once -- re-running on a healthy machine does nothing.
REM
REM  TIP: to install Node/Git for the WHOLE machine instead of
REM  just your account (needs an admin prompt), do NOT double-
REM  click -- instead RIGHT-CLICK this file and choose
REM  "Run as administrator". The plain double-click works fine
REM  too; it just installs per-user and tells you if anything
REM  wanted admin.
REM ============================================================
title ORA Desktop Setup - FULL SETUP
echo.
echo   Setting up your oxford-command-center dev environment...
echo   (installs what is missing; safe to run more than once)
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup-desktop-windows.ps1"
echo.
echo ============================================================
echo   Done. Copy the PASS / WARN / FAIL table above and send it
echo   back to Claude so we can tune anything that WARNed.
echo ============================================================
echo.
pause
