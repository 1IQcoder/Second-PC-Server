RequestExecutionLevel admin

!define APP_NAME "SPCserver"          ; Define the application name
!define INSTALL_DIR "$APPDATA\${APP_NAME}" ; Define the installation directory in %APPDATA%
!define UNINSTALL_EXE "uninstall.exe"  ; Define the uninstaller executable name

SetCompressor lzma                    ; Set the compression type (LZMA is used for smaller size)
Name "${APP_NAME} Installer"          ; Define the installer name
OutFile "SPCS-Installer.exe"          ; Output installer file name

InstallDir "${INSTALL_DIR}"            ; Set the default installation directory

Page directory                       ; Directory selection page for the user
Page instfiles                       ; File installation progress page
UninstPage uninstConfirm             ; Uninstall confirmation page
UninstPage instfiles                 ; Uninstall progress page

Section "Install"                     ; Define the main installation section
    SetOutPath "$INSTDIR\scripts"
    File /r "..\app\scripts\*"

    SetOutPath "$INSTDIR\cli"
    File /r "..\build\cli\*"

    SetOutPath "$INSTDIR\server"
    File /r "..\build\server\*"

    ; append app to Windows programs list
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\${UNINSTALL_EXE}"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" '"$INSTDIR\cli\cli.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "Your Company Name"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1

    WriteUninstaller "$INSTDIR\${UNINSTALL_EXE}" ; Create uninstaller executable

    ; Create bin folder
    ExecWait '"$INSTDIR\scripts\bin_creator.bat"'
    ; append app dir to PATH
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$INSTDIR\bin;$%Path%"

SectionEnd

Section "Uninstall"
    ; delete app from Windows programs list
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

    RMDIR /r "$INSTDIR"                   ; Remove the entire installation directory and its contents
SectionEnd
