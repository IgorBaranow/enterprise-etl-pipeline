@echo off
TITLE Enterprise ETL Suite - Emergency Reset
color 4F
cd /d "%~dp0"

echo ========================================================
echo       DANGER ZONE: APPLICATION FACTORY RESET
echo ========================================================
echo WARNING: This tool will wipe the local application state:
echo  - The Virtual Environment (.venv) will be deleted.
echo  - Browser profiles and cached security tokens will be wiped.
echo  - Your saved passwords will be reset (a backup will be created).
echo.
echo NOTE: Global System Python installations will NOT be affected.
echo.

choice /C YN /M "Are you absolutely sure you want to proceed?"
if errorlevel 2 goto Cancel
if errorlevel 1 goto Proceed

:Proceed
echo.
echo ========================================================
echo         SYSTEM CLEANUP IN PROGRESS...
echo ========================================================
timeout /t 2 >nul

:: Fetch the actual user profile path, ensuring correct resolution even if the script is run as Administrator
set "REAL_USERPROFILE=%HOMEDRIVE%%HOMEPATH%"

echo [1/4] Closing isolated Python processes...
:: Safely terminate ONLY the Python processes spawned from our isolated .venv directory!
:: This prevents killing unrelated background Python scripts running on the user's machine.
wmic process where "executablepath like '%%\\.venv\\Scripts\\python%%'" call terminate >nul 2>&1

echo [2/4] Backing up and resetting local credential vaults...
if exist "%REAL_USERPROFILE%\system_secrets.json" (
    move /y "%REAL_USERPROFILE%\system_secrets.json" "%REAL_USERPROFILE%\system_secrets.bak" >nul 2>&1
    echo  - Credentials safely backed up to system_secrets.bak
)

echo [3/4] Wiping browser automation profiles and cached security cookies...
for /d %%x in ("%REAL_USERPROFILE%\EdgeProfile_*_Automation") do rmdir /s /q "%%x" >nul 2>&1

echo [4/4] Destroying virtual environment...
if exist "..\.venv" rmdir /s /q "..\.venv" >nul 2>&1
if exist ".venv" rmdir /s /q ".venv" >nul 2>&1

echo.
color 2F
echo ========================================================
echo [SUCCESS] Application state has been completely reset!
echo ========================================================
echo You can now safely run the Launcher to rebuild a fresh environment.
pause
exit

:Cancel
color 0F
echo.
echo Reset cancelled. No files or directories were modified.
pause
exit