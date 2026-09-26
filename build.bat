@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Build CertEditor_Portable.exe
cd /d "%~dp0"
set "ROOT=%~dp0"
set "VENV=%ROOT%.buildenv"
set "WORK=%ROOT%.buildwork"

echo ============================================================
echo   Build CertEditor_Portable.exe  (PyInstaller onefile, console)
echo ============================================================

rem ---- 1. Python ----------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo [ERROR] Python not found. Install Python 3.9+ from python.org ^(tick "Add to PATH"^).
  goto :fail
)

rem ---- 2. isolated build venv (.buildenv) ---------------------------------
if not exist "%VENV%\Scripts\python.exe" (
  echo [1/5] Creating build venv .buildenv ...
  %PY% -m venv "%VENV%" || goto :fail
)
set "VPY=%VENV%\Scripts\python.exe"
echo [2/5] Installing build requirements ...
"%VPY%" -m pip install --disable-pip-version-check -q --upgrade pip || goto :fail
"%VPY%" -m pip install --disable-pip-version-check -q -r "%ROOT%requirements-build.txt" || goto :fail

rem ---- 3. tests -------------------------------------------------------------
echo [3/5] Running tests ...
"%VPY%" -m unittest discover -s "%ROOT%tests" || (echo [ERROR] Tests failed, build aborted. & goto :fail)

rem ---- 4. version info + PyInstaller ---------------------------------------
echo [4/5] Building ...
for /f "delims=" %%v in ('call "%VPY%" "%ROOT%scripts\make_version_info.py" "%WORK%\version_info.txt"') do set "VER=%%v"
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --console ^
  --name CertEditor_Portable ^
  --paths "%ROOT%src" ^
  --add-data "%ROOT%src\certeditor\web;certeditor\web" ^
  --version-file "%WORK%\version_info.txt" ^
  --workpath "%WORK%" --specpath "%WORK%" --distpath "%ROOT%dist" ^
  "%ROOT%CertEditor.py" || goto :fail

rem ---- 5. copy next to Result/ --------------------------------------------
echo [5/5] Copying exe ...
copy /y "%ROOT%dist\CertEditor_Portable.exe" "%ROOT%CertEditor_Portable.exe" >nul || goto :fail

echo.
echo Done: CertEditor_Portable.exe  v%VER%
echo Double-click it: a console window opens and the editor opens in your browser.
if /i not "%~1"=="--no-pause" pause
exit /b 0

:fail
echo.
echo BUILD FAILED
if /i not "%~1"=="--no-pause" pause
exit /b 1
