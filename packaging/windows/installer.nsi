Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
Name "Christ Church Video Cleanup"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\CCSVideoCleanup"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ICON "${PAYLOAD}/app/windows/church.ico"
!define MUI_UNICON "${PAYLOAD}/app/windows/church.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\runtime\pythonw.exe"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApplication
!define MUI_FINISHPAGE_RUN_TEXT "Open Christ Church Video Cleanup"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
VIProductVersion "1.2.0.0"
VIAddVersionKey "ProductName" "Christ Church Video Cleanup"
VIAddVersionKey "FileDescription" "Church sermon video preparation installer"
VIAddVersionKey "FileVersion" "1.2.0"
VIAddVersionKey "LegalCopyright" "Private church-use application; see included rights and dependency notices"

Function LaunchApplication
  Exec '"$INSTDIR\runtime\pythonw.exe" "$INSTDIR\app\windows\launcher.py" --open'
FunctionEnd

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "This installer requires 64-bit Windows on an Intel or AMD PC." /SD IDOK
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "This application requires Windows 10 or Windows 11." /SD IDOK
    Abort
  ${EndIf}
  SetShellVarContext current
FunctionEnd

Section "Application"
  IfFileExists "$INSTDIR\app\windows\launcher.py" 0 copy_files
  ExecWait '"$INSTDIR\runtime\python.exe" "$INSTDIR\app\windows\launcher.py" --shutdown' $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Finish the current sermon processing job before updating the application." /SD IDOK
    Abort
  ${EndIf}
  ; Allow the stopped server to finish releasing embedded runtime DLLs.
  Sleep 1000
copy_files:
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}/*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Christ Church Video Cleanup"
  CreateShortCut "$SMPROGRAMS\Christ Church Video Cleanup\Christ Church Video Cleanup.lnk" "$INSTDIR\runtime\pythonw.exe" '"$INSTDIR\app\windows\launcher.py" --open' "$INSTDIR\app\windows\church.ico"
  CreateShortCut "$DESKTOP\Christ Church Video Cleanup.lnk" "$INSTDIR\runtime\pythonw.exe" '"$INSTDIR\app\windows\launcher.py" --open' "$INSTDIR\app\windows\church.ico"
  CreateShortCut "$SMPROGRAMS\Christ Church Video Cleanup\Video files and evidence.lnk" "$INSTDIR\runtime\pythonw.exe" '"$INSTDIR\app\windows\launcher.py" --data' "$INSTDIR\app\windows\church.ico"
  CreateShortCut "$SMPROGRAMS\Christ Church Video Cleanup\Setup log.lnk" "$INSTDIR\runtime\pythonw.exe" '"$INSTDIR\app\windows\launcher.py" --logs'
  CreateShortCut "$SMPROGRAMS\Christ Church Video Cleanup\Quick start instructions.lnk" "$WINDIR\system32\notepad.exe" '"$INSTDIR\app\windows\QUICK-START.txt"'
  CreateShortCut "$SMPROGRAMS\Christ Church Video Cleanup\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "DisplayName" "Christ Church Video Cleanup"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "DisplayVersion" "1.2.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "DisplayIcon" "$INSTDIR\app\windows\church.ico"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  ExecWait '"$INSTDIR\runtime\python.exe" "$INSTDIR\app\windows\launcher.py" --shutdown' $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Finish the current sermon processing job before uninstalling. Your video files will be preserved." /SD IDOK
    Abort
  ${EndIf}
  Delete "$DESKTOP\Christ Church Video Cleanup.lnk"
  RMDir /r "$SMPROGRAMS\Christ Church Video Cleanup"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\CCSVideoCleanup"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\runtime"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ; The separate LocalAppData\CCSVideoCleanup data directory is deliberately retained.
SectionEnd
