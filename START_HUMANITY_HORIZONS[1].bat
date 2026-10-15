@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
  echo During installation, enable "Add Python to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating the local Python environment...
  py -m venv .venv
  if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error
if not exist ".venv\hh_requirements_installed.txt" (
  echo Installing required packages. This needs an internet connection the first time...
  py -m pip install --upgrade pip
  if errorlevel 1 goto error
  py -m pip install -r requirements.txt
  if errorlevel 1 goto error
  echo installed> ".venv\hh_requirements_installed.txt"
)
echo Starting Humanity Horizons 360...
py -m streamlit run app.py
if errorlevel 1 goto error
exit /b 0
:error
echo.
echo Startup stopped because an earlier command failed. Read the error above.
pause
exit /b 1
