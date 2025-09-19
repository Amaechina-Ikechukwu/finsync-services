@echo off
REM Wrapper to run functions-framework using the repo's venv Python
setlocal
set VENV_PY="%~dp0venv\Scripts\python.exe"
if exist %VENV_PY% (
  %VENV_PY% -m functions_framework %*
  exit /b %errorlevel%
) else (
  echo [ERROR] venv Python not found at %VENV_PY%
  echo Create it with: py -m venv venv && venv\Scripts\pip install -r requirements.txt
  exit /b 1
)
endlocal
