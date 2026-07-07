@echo off
REM ============================================================
REM  ORA Desktop Setup -- RESTORE a MISSING settings.json
REM
REM  HOW TO USE: double-click this file.
REM
REM  The setup checker found that oxford-command-center's
REM  .claude\settings.json is MISSING (the .claude folder exists,
REM  the file inside it does not). This restores it from git
REM  history using "git checkout" -- the exact command the setup
REM  script itself recommends when it sees this WARN.
REM
REM  SAFE BY DESIGN: if the file already exists, this tool does
REM  NOTHING and exits -- it never overwrites an existing file.
REM  It only acts when the file is genuinely absent.
REM ============================================================
title ORA - Restore missing .claude\settings.json
set "PROJECT=C:\Users\Owner\oxford-command-center"
set "TARGET=%PROJECT%\.claude\settings.json"

if exist "%TARGET%" (
    echo.
    echo   %TARGET%
    echo   already exists -- nothing to do. This tool never overwrites
    echo   an existing file.
    echo.
    pause
    exit /b 0
)

echo.
echo   settings.json is missing. Restoring it from git history...
echo   Project: %PROJECT%
echo.
git -C "%PROJECT%" checkout -- .claude/settings.json
if errorlevel 1 (
    echo.
    echo   FAILED -- see the message above. Common causes: git is not
    echo   installed yet ^(double-click 2-Set-Up-My-Dev-Environment.cmd
    echo   first^), or the project folder is not a git checkout.
    echo.
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo.
    echo   Restored successfully:
    echo   %TARGET%
) else (
    echo.
    echo   git checkout ran with no error, but the file is still
    echo   missing. This can mean it is not tracked in git at that
    echo   path. Copy this window's text and send it back to Claude.
)
echo.
pause
