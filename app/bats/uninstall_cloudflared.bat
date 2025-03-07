@echo off
setlocal enabledelayedexpansion

echo [INFO] - Checking cloudflared installed
wsl bash -c "command -v cloudflared > /dev/null 2>&1 && echo Cloudflared installed: $(docker --version) || echo Cloudflared not installed." > temp.txt 2>&1
findstr /C:"Cloudflared installed" temp.txt > nul
if %errorlevel%==0 (
    echo [INFO] - Detected cloudflared installed.
    del temp.txt
) else (
    echo [INFO] - Cloudflared not installed.
    del temp.txt
    goto :endProgram
)

echo [INFO] - Uninstalling cloudflared.
wsl sudo apt remove --purge cloudflared
wsl sudo apt autoremove
wsl sudo rm /etc/apt/sources.list.d/cloudflare-cloudflared.list
wsl sudo rm /usr/share/keyrings/cloudflare-archive-keyring.gpg
wsl sudo rm -rf ~/.cloudflared
echo [INFO] - Cloudflared uninstalled.

:endProgram
endlocal
pause