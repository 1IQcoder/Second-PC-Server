!define APP_NAME "SPCserver"          ; Define the application name
!define APP_EXE "flask_app.exe"       ; Define the executable file of the app
!define INSTALL_DIR "$APPDATA\${APP_NAME}" ; Define the installation directory in %APPDATA%
!define UNINSTALL_EXE "uninstall.exe"  ; Define the uninstaller executable name
!define CLOUDFLARE_URL "https://1111-releases.cloudflareclient.com/win/latest" ; Define Cloudflare installer URL
!define CLOUDFLARE_INSTALLER "Cloudflare_WARP_2024.12.554.0.msi" ; Define local filename for Cloudflare MSI installer

SetCompressor lzma                    ; Set the compression type (LZMA is used for smaller size)
Name "${APP_NAME} Installer"          ; Define the installer name
OutFile "SPCS-Installer.exe"          ; Output installer file name

InstallDir "${INSTALL_DIR}"            ; Set the default installation directory

Page directory                       ; Directory selection page for the user
Page instfiles                       ; File installation progress page
UninstPage uninstConfirm             ; Uninstall confirmation page
UninstPage instfiles                 ; Uninstall progress page

Section "Install"                     ; Define the main installation section
    SetOutPath "$INSTDIR"             ; Set the output path for installed files

    ; Check if Cloudflare is already installed by looking at the registry
    ReadRegStr $0 HKLM "Software\Cloudflare" "InstallPath"
    IfFileExists "$0\cloudflare.exe" 0 +3   ; If Cloudflare is installed, skip the installation
        MessageBox MB_OK "Cloudflare is already installed!"  ; Notify the user
        Goto Done                        ; Skip the rest of the installation process

    ; Download and install Cloudflare if not found
    MessageBox MB_OK "Cloudflare is not found. Starting download..."
    NSISdl::Download "${CLOUDFLARE_URL}" "$TEMP\${CLOUDFLARE_INSTALLER}"  ; Download Cloudflare MSI installer
    ExecWait 'msiexec /i "$TEMP\${CLOUDFLARE_INSTALLER}" /quiet /norestart' ; Install MSI silently
    MessageBox MB_OK "Cloudflare has been installed!"  ; Notify the user that Cloudflare is installed

Done:
    ; Continue with the installation of the main application
    File /r "dist\*.*"                  ; Copy all files from the dist directory into the installation directory
    WriteUninstaller "$INSTDIR\${UNINSTALL_EXE}" ; Create uninstaller executable

    ; Create internal folders and files for the application
    CreateDirectory "$INSTDIR\_internal\repos"  ; Create the "repos" folder inside the "_internal" directory

    ; Create an empty accounts.json file in the "_internal" folder
    FileOpen $0 "$INSTDIR\_internal\accounts.json" w
    FileWrite $0 "{}"                    ; Write an empty JSON object
    FileClose $0                         ; Close the file

    ; Create shortcuts for the user on the Desktop and in Start Menu
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"  ; Shortcut on the Desktop
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\${UNINSTALL_EXE}"  ; Uninstall shortcut in Start Menu
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"  ; Shortcut to the app in Start Menu

SectionEnd                             ; End of the main installation section

Section "Uninstall"                     ; Define the uninstallation section
    ; Delete shortcuts from the Desktop and Start Menu
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    
    ; Remove the application folder and its contents
    RMDir "$SMPROGRAMS\${APP_NAME}"       ; Remove the Start Menu folder
    RMDIR /r "$INSTDIR"                   ; Remove the entire installation directory and its contents

    ; Recreate the installation directory (in case the user wants to reinstall later)
    CreateDirectory $INSTDIR
SectionEnd
