@echo off
set CONTAINER_NAME=%1

for /f "delims=" %%i in ('docker ps --filter "name=%CONTAINER_NAME%" --filter "status=running" --format "{{.Names}}"') do set OUTPUT=%%i

if "%OUTPUT%"=="%CONTAINER_NAME%" (
    echo Container %CONTAINER_NAME% is running
    exit /b 0
) else (
    echo Error: Running container %CONTAINER_NAME% not found or name does not match
    exit /b 1
)
