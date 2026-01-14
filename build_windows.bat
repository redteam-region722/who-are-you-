@echo off
REM Build script for Windows
echo Building Remote Desktop Viewer for Windows...

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Generate certificates if they don't exist
if not exist "certs\server.crt" (
    echo Generating certificates...
    python certs\generate_certs.py
)

REM Create executables using PyInstaller
echo Building executables...
pip install pyinstaller

REM Build client
pyinstaller --onefile --windowed --console --name client.exe --icon=client.ico client\client.py
if errorlevel 1 (
    echo Client build failed!
    exit /b 1
)

REM Build server
pyinstaller --onefile --name server.exe --icon=NONE server\server.py
if errorlevel 1 (
    echo Server build failed!
    exit /b 1
)

REM Copy certificates to dist
if exist "certs" (
    xcopy /E /I /Y certs dist\certs >nul 2>&1
)

REM Copy configuration example if it exists
if exist "client_config.ini.example" (
    if not exist "dist\client_config.ini" (
        copy client_config.ini.example dist\client_config.ini >nul
    )
)

echo.
echo Build complete!
echo Executables are in the 'dist' folder:
echo   - dist\client.exe (client)
echo   - dist\server.exe (viewer/server)
if exist "dist\client_config.ini" (
    echo   - dist\client_config.ini (edit to set server IP)
)
echo.
echo For two-machine testing:
echo   1. Find server IP on Machine 1: ipconfig
echo   2. On Machine 1, run: dist\server.exe --host 0.0.0.0 --port 8443
echo   3. On Machine 2, run: dist\client.exe --server-host ^<SERVER_IP^> --server-port 8443
echo   4. Or edit dist\client_config.ini and run: dist\client.exe
echo.
echo To install client as service:
echo   Set: setx RDS_SERVER_HOST "SERVER_IP"
echo   Then: python client\install_service.py install
