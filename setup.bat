@echo off
rem Shu's LaunchBox 4K CRT Build - opens the setup wizard. Installs Python first if this PC doesn't have it.
cd /d "%~dp0"
set "PYL=%LOCALAPPDATA%\Programs\Python\Launcher"

where py >nul 2>nul && goto havepy
if exist "%PYL%\py.exe" goto addpath

echo Python 3 is needed and isn't installed on this PC.
where winget >nul 2>nul || goto manual
choice /c YN /m "Install Python 3.12 now from the official Python package (winget)"
if errorlevel 2 goto manual
winget install --id Python.Python.3.12 --source winget --scope user --silent --accept-package-agreements --accept-source-agreements
if exist "%PYL%\py.exe" goto addpath
where py >nul 2>nul && goto havepy
echo The install didn't finish.

:manual
echo Opening the Python download page. Tick "Add python.exe to PATH" when you install it, then run setup.bat again.
start "" https://www.python.org/downloads/
pause
exit /b

:addpath
rem a fresh install isn't on this window's PATH yet
set "PATH=%PYL%;%PATH%"

:havepy
py -c "import PIL, numpy, yaml" 2>nul || py -m pip install --user pillow numpy pyyaml
py -c "import PIL, numpy, yaml" 2>nul || goto pipfail
start "" pyw tools\setup_wizard.py
exit /b

:pipfail
echo.
echo Couldn't install the Python libraries the wizard needs (Pillow, NumPy, PyYAML).
echo Check your internet connection, then run setup.bat again.
pause
