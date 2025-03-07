@echo off
setlocal enabledelayedexpansion

echo [INFO] - Checking cloudflared installed
wsl bash -c "command -v cloudflared > /dev/null 2>&1 && echo Cloudflared installed: $(docker --version) || echo Cloudflared not installed." > temp.txt 2>&1
findstr /C:"Cloudflared installed" temp.txt > nul
if %errorlevel%==0 (
    echo [INFO] - Cloudflared already installed.
    del temp.txt
) else (
    echo [INFO] - Cloudflared not installed.
    call :installCloudflared
)

echo [INFO] - Checking cloudflared cert.pem exists
wsl bash -c "if [ -f ~/.cloudflared/cert.pem ]; then echo Cert.pem found; else echo Cert.pem not found; fi" > temp.txt 2>&1
findstr /C:"Cert.pem found" temp.txt > nul
if %errorlevel%==0 (
    echo [INFO] - Cert.pem already exists.
    del temp.txt
) else (
    echo [INFO] - Cert.pem not found.
    del temp.txt
    call :cloudflaredLogin
)

endlocal
pause


:installCloudflared
    echo [INFO] - Installing cloudflared.
    wsl sudo apt update
    wsl sudo mkdir -p --mode=0755 /usr/share/keyrings
    wsl bash -c "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null"
    wsl bash -c 'echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list'
    wsl sudo apt-get update && wsl sudo apt-get install -y cloudflared
    goto :eof


:cloudflaredLogin
    echo [INFO] - Login to cloudflared account.
    echo [WARNING] - Follow the link and log into your cloudflare account
    wsl cloudflared login
    goto :eof
