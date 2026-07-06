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
REM
REM  WHY THE PATH REFRESH BELOW: if Git was JUST installed by
REM  2-Set-Up-My-Dev-Environment.cmd in a different window, THIS
REM  window may still be running on an older, cached copy of PATH
REM  (Windows Explorer does not always notice a PATH change until
REM  you sign out/in or reboot). Re-reading PATH from the registry
REM  here, for this window only, means you do not have to reboot
REM  just to use a git that is already installed. This never
REM  writes anything back to the registry.
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

set "MPATH="
set "UPATH="
for /f "usebackq tokens=1,2,*" %%A in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul`) do (
    if /i "%%A"=="Path" set "MPATH=%%C"
)
for /f "usebackq tokens=1,2,*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do (
    if /i "%%A"=="Path" set "UPATH=%%C"
)
if defined MPATH if defined UPATH set "PATH=%MPATH%;%UPATH%;%PATH%"
if defined MPATH if not defined UPATH set "PATH=%MPATH%;%PATH%"
if not defined MPATH if defined UPATH set "PATH=%UPATH%;%PATH%"

where git >nul 2>nul
if errorlevel 1 (
    echo.
    echo   git is still not found, even after refreshing this window's
    echo   view of PATH from the registry. Easiest fix: sign out of
    echo   Windows and back in ^(or restart your PC^), then double-click
    echo   this file again. If git was never installed yet, double-click
    echo   2-Set-Up-My-Dev-Environment.cmd first.
    echo.
    pause
    exit /b 1
)

echo.
echo   settings.json is missing. Restoring it from git history...
echo   Project: %PROJECT%
echo.
git -C "%PROJECT%" checkout -- .claude/settings.json
if errorlevel 1 (
    echo.
    echo   FAILED -- see the message above. Common cause: the project
    echo   folder is not a git checkout, or the file is not tracked at
    echo   that path.
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
