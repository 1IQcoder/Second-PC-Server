@echo off
set IMAGE_NAME=%1

docker image inspect %IMAGE_NAME% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Image %IMAGE_NAME% not found
    exit /b 1
)

echo Image %IMAGE_NAME% exists
exit /b 0
