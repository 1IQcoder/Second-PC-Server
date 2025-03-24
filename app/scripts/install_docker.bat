@echo off
setlocal enabledelayedexpansion

echo [INFO] - Checking docker installed
wsl bash -c "command -v docker > /dev/null 2>&1 && echo Docker installed: $(docker --version) || echo Docker not installed." > temp.txt 2>&1
findstr /C:"Docker installed" temp.txt > nul
if %errorlevel%==0 (
    echo [INFO] - Docker already installed.
    del temp.txt
) else (
    echo [INFO] - Docker not installed.
    call installDocker
)

endlocal
pause


@REM Add Docker's official GPG key:
:installDocker
    echo [INFO] - Installing Docker Engine
    wsl for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

    wsl sudo apt-get update
    wsl sudo apt-get install ca-certificates curl
    wsl sudo install -m 0755 -d /etc/apt/keyrings
    wsl sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    wsl sudo chmod a+r /etc/apt/keyrings/docker.asc

    wsl sudo sh -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"${UBUNTU_CODENAME:-$VERSION_CODENAME}\") stable" > /etc/apt/sources.list.d/docker.list && apt-get update'

    wsl sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    wsl docker -v
    echo [INFO] - Docker installed successfully.
    goto :eof