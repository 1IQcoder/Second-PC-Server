@echo off
setlocal enabledelayedexpansion

echo [INFO] - Checking docker installed
wsl bash -c "command -v docker > /dev/null 2>&1 && echo Docker installed: $(docker --version) || echo Docker not installed." > temp.txt 2>&1
findstr /C:"Docker installed" temp.txt > nul
if %errorlevel%==0 (
    echo [INFO] - Detected docker installed.
    del temp.txt
) else (
    echo [INFO] - Docker not installed.
    goto :endProgram
)

echo [INFO] - Uninstalling docker
wsl sudo apt-get remove -y docker docker-engine docker.io containerd runc
wsl sudo apt-get purge -y docker-ce docker-ce-cli containerd.io
wsl sudo rm -rf /var/lib/docker /etc/docker
wsl sudo rm -rf /var/run/docker.sock
wsl sudo rm -rf ~/.docker
echo [INFO] - Docker uninstalled

:endProgram
endlocal
pause