@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Run the setup commands from the AI4DOS installation guide first.
  exit /b 1
)
".venv\Scripts\python.exe" -c "import httpx, openai" >nul 2>&1
if errorlevel 1 (
  echo Gateway dependencies are missing. Run the dependency setup commands from the AI4DOS installation guide.
  exit /b 1
)
set "PYTHONPATH=%CD%\server\src"
".venv\Scripts\python.exe" -m ai4dos.server %*
exit /b %ERRORLEVEL%
