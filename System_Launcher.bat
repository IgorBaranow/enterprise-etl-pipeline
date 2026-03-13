@echo off
TITLE Enterprise ETL Suite - System Launcher
color 0F
:: Ensure execution context is set to the script's actual directory
cd /d "%~dp0"

:: Initialize local logging directory for deployment diagnostics
set "LOGDIR=logs\launcher"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

:: Set up path for deployment logs
set "LOGFILE=%LOGDIR%\launcher_log.txt"
echo [%DATE% %TIME%] --- LAUNCHER INITIALIZED --- > "%LOGFILE%"

echo ========================================================
echo       ENTERPRISE COMMAND CENTER - INITIALIZING...
echo ========================================================
echo.
echo [SYSTEM] Performing background health check...
echo [%DATE% %TIME%] Performing quick health check... >> "%LOGFILE%"

:: ========================================================
:: PHASE 1: FAST PATH (SILENT HEALTH CHECK)
:: ========================================================
:: Validates if the virtual environment exists and core dependencies are intact.
:: This ensures a zero-friction startup for returning users.
if not exist ".venv\Scripts\python.exe" goto FirstTimeSetup

".venv\Scripts\python.exe" -c "import tkinter, pandas, playwright" >nul 2>&1
if not errorlevel 1 (
    echo [OK] Core libraries verified.
    echo [OK] Virtual environment is stable.
    echo [%DATE% %TIME%] Health check passed. Launching UI. >> "%LOGFILE%"
    echo.
    echo ^> Starting user interface...
    timeout /t 1 >nul
    :: Launch the application without keeping the console window locked
    start "" ".venv\Scripts\pythonw.exe" main.py
    exit
) else (
    echo [!] Health check failed: Libraries are missing or corrupted.
    echo [%DATE% %TIME%] Health check failed. Entering Recovery Mode. >> "%LOGFILE%"
    echo [SYSTEM] Entering Self-Healing Recovery Mode...
    timeout /t 2 >nul
    goto RecoverySetup
)

:FirstTimeSetup
echo [!] Virtual environment not found.
echo [%DATE% %TIME%] Venv not found. Initiating first-time setup. >> "%LOGFILE%"
echo [SYSTEM] Entering First-Time Configuration Mode...
timeout /t 2 >nul

:RecoverySetup
:: ========================================================
:: PHASE 2: ENVIRONMENT DEPLOYMENT & RECOVERY
:: ========================================================
color 1F
cls
echo ========================================================
echo       SYSTEM VERIFICATION ^& AUTOMATIC DEPLOYMENT
echo ========================================================
echo Please wait while we configure your local environment.
echo This is a one-time process and may take a few minutes.
echo.

:: Purge the corrupted environment to ensure a clean slate
if exist ".venv" (
    echo [!] Cleaning up broken environment...
    echo [%DATE% %TIME%] Wiping broken venv... >> "%LOGFILE%"
    rmdir /s /q ".venv" >nul 2>&1
)

:: Step 1: Detect Base System Python
echo [1/4] Verifying Base Python Installation...
echo [%DATE% %TIME%] Verifying Python... >> "%LOGFILE%"
call :DetectPython

if not "%PYTHON_CMD%"=="NONE" goto PythonFound

color 4F
echo.
echo [!] CRITICAL ERROR: Python interpreter is not installed.
echo [%DATE% %TIME%] Python not installed. Redirecting to MS Store... >> "%LOGFILE%"
echo.
echo Opening Microsoft Store... 
echo 1. Click "Get" or "Install" in the Store window.
echo 2. Please wait. DO NOT close this command window.
echo.
echo [SYSTEM] Actively scanning for Python installation... ^(Auto-resuming when detected^)
explorer "ms-windows-store://pdp/?ProductId=9NCVDN91XZQP"

:WaitForPython
:: Polling loop to wait for the user to finish the MS Store installation
timeout /t 5 >nul
call :DetectPython
if "%PYTHON_CMD%"=="NONE" goto WaitForPython

color 1F
echo.
echo  - SUCCESS: Python installation detected! Resuming deployment...
echo [%DATE% %TIME%] Python installed successfully. >> "%LOGFILE%"

:PythonFound
echo  - OK: Python detected as %PYTHON_CMD%.
echo [%DATE% %TIME%] Python found: %PYTHON_CMD% >> "%LOGFILE%"

:: Step 2: Provision Virtual Environment
echo.
echo [2/4] Provisioning Isolated Environment (.venv)...
echo [%DATE% %TIME%] Configuring venv... >> "%LOGFILE%"
if not exist ".venv\Scripts\python.exe" (
    echo  - Creating a fresh sandbox ^(this keeps your OS clean^)...
    "%PYTHON_CMD%" -m venv .venv
    if errorlevel 1 (
        echo [%DATE% %TIME%] Failed to create venv. >> "%LOGFILE%"
        echo [!] Failed to create virtual environment. Check logs\launcher\launcher_log.txt
        pause
        exit
    )
) else (
    echo  - OK: Environment sandbox is ready.
)

:: Step 3: Resolve Python Dependencies
echo.
echo [3/4] Resolving Application Dependencies...
echo [%DATE% %TIME%] Installing libraries via pip... >> "%LOGFILE%"
echo  - Downloading packages... ^(Please do not close this window^)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] Error resolving dependencies. >> "%LOGFILE%"
    echo [!] Failed to install libraries. Check logs\launcher\launcher_log.txt for details.
    pause
    exit
)
echo  - OK: All dependencies resolved successfully.

:: Step 4: Configure Web Automation Binaries
echo.
echo [4/4] Configuring Web Automation Engines (Microsoft Edge)...
echo [%DATE% %TIME%] Priming Playwright browsers... >> "%LOGFILE%"
echo  - Linking browser profiles and downloading binaries... 
".venv\Scripts\python.exe" -m playwright install msedge >> "%LOGFILE%" 2>&1
echo  - OK: Automation engines are primed.

echo.
echo ========================================================
echo       ALL SYSTEMS GO! LAUNCHING APPLICATION...
echo ========================================================
echo [%DATE% %TIME%] Deployment complete. Launching app. >> "%LOGFILE%"
timeout /t 3 >nul
start "" ".venv\Scripts\pythonw.exe" main.py
exit

:: ========================================================
:: HELPER FUNCTION: System Python Locator
:: ========================================================
:DetectPython
:: Attempts to locate the Python executable across various standard Windows paths
python --version >nul 2>&1 && (set "PYTHON_CMD=python" & exit /b)
py --version >nul 2>&1 && (set "PYTHON_CMD=py" & exit /b)
for %%f in ("%LOCALAPPDATA%\Microsoft\WindowsApps\python*.exe") do (
    "%%f" --version >nul 2>&1 && (set "PYTHON_CMD="%%f"" & exit /b)
)
set "PYTHON_CMD=NONE"
exit /b