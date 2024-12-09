@echo off
if "%~1"=="" (
    echo Error: path not exsist
    exit /b 1
)

rmdir /s /q "%~1"
if errorlevel 1 (
    echo Can not delete folder "%~1".
    exit /b 1
) else (
    echo Folder "%~1" success deleted.
)
