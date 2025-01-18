!define APP_NAME "SPCserver"
!define APP_EXE "flask_app.exe"
!define INSTALL_DIR "$APPDATA\${APP_NAME}"
!define UNINSTALL_EXE "uninstall.exe"

SetCompressor lzma
Name "${APP_NAME} Installer"
OutFile "SPCS-Installer.exe"

InstallDir "${INSTALL_DIR}"

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "dist\*.*"
    WriteUninstaller "$INSTDIR\${UNINSTALL_EXE}"

    CreateDirectory "$INSTDIR\_internal\repos"

    FileOpen $0 "$INSTDIR\_internal\accounts.json" w
    FileWrite $0 "{}"
    FileClose $0

    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\${UNINSTALL_EXE}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    RMDIR /r "$INSTDIR"
    CreateDirectory $INSTDIR
SectionEnd
