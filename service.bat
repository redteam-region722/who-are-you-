@echo off
setlocal

:: --- Configuration ---
set "TOOL_NAME=ClientMonitor"
set "EXE_FILENAME=client.exe"
set "INSTALL_DIR=C:\ProgramData\%TOOL_NAME%"
set "VBS_FILENAME=launch_silent_%TOOL_NAME%.vbs"
set "TASK_NAME=%TOOL_NAME%_Startup"

:: --- YOUR CLIENT.EXE ARGUMENTS ---
set "SERVER_HOST=192.168.1.100"  :: <--- REPLACE WITH YOUR SERVER IP ADDRESS
set "SERVER_PORT=12345"         :: <--- REPLACE WITH YOUR SERVER PORT

:: --- Check for Administrator Privileges ---
:: This check is crucial for creating system-level scheduled tasks and writing to ProgramData.
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO ERROR: This script must be run with Administrator privileges.
    ECHO Please right-click the batch file and select "Run as administrator".
    ECHO.
    PAUSE
    EXIT /B 1
)


echo Setting up persistent and silent execution for %EXE_FILENAME% with arguments...

:: --- 1. Create Installation Directory ---
echo Creating installation directory: %INSTALL_DIR%
md "%INSTALL_DIR%" >nul 2>&1

:: --- 2. Copy the Executable ---
:: Make sure your EXE_FILENAME is in the same directory as this batch script,
:: or provide a full path to it.
echo Copying %EXE_FILENAME% to %INSTALL_DIR%
copy "%~dp0%EXE_FILENAME%" "%INSTALL_DIR%\" >nul || (
    echo ERROR: Failed to copy %EXE_FILENAME%. Make sure it exists in the script's directory.
    pause
    exit /b 1
)

:: --- 3. Create the VBScript for Silent Launch with Arguments ---
echo Creating VBScript for silent launch: %INSTALL_DIR%\%VBS_FILENAME%
(
    echo Set WshShell = CreateObject("WScript.Shell")
    echo WshShell.Run """%INSTALL_DIR%\%EXE_FILENAME% --server-host %SERVER_HOST% --server-port %SERVER_PORT%""", 0, False
    echo Set WshShell = Nothing
) > "%INSTALL_DIR%\%VBS_FILENAME%"

:: Explanation of VBScript parameters:
:: """%INSTALL_DIR%\%EXE_FILENAME% --server-host %SERVER_HOST% --server-port %SERVER_PORT%"""
::    - This entire string is the command that WshShell.Run will execute.
::    - The triple quotes are essential to correctly handle spaces in the path to the executable and to enclose the entire command string.
:: 0 - Specifies the window style. 0 means the window is hidden.
:: False - Specifies whether the script should wait for the program to finish. False means it runs in the background immediately.

:: --- 4. Create the Scheduled Task for Persistence ---
echo Creating Scheduled Task: %TASK_NAME%
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe //B //Nologo \"%INSTALL_DIR%\%VBS_FILENAME%\"" /sc ONSTART /ru SYSTEM /rl HIGHEST /f

:: Explanation of schtasks parameters:
:: /create - Creates a new scheduled task.
:: /tn "%TASK_NAME%" - Specifies the name of the task.
:: /tr "wscript.exe //B //Nologo \"%INSTALL_DIR%\%VBS_FILENAME%\"" - Specifies the program to run.
::    wscript.exe: Windows Script Host executable.
::    //B: Run script in batch mode (suppresses script errors/prompts).
::    //Nologo: Suppresses banner display.
::    "%INSTALL_DIR%\%VBS_FILENAME%": Path to the VBScript.
:: /sc ONSTART - Specifies the schedule type: runs at system startup.
:: /ru SYSTEM - Specifies the user account under which the task runs. 'SYSTEM' is a built-in account with extensive privileges and runs without a logged-in user.
:: /rl HIGHEST - Specifies that the task will run with "highest privileges".
:: /f - Forces the creation of the task if a task with the same name already exists.

echo.
echo Setup complete.
echo Your executable "%EXE_FILENAME%" is configured to start silently after reboot with the specified arguments.
echo.
echo To verify, you can check Task Scheduler (taskschd.msc) for "%TASK_NAME%".
echo.
pause
endlocal
