outFile "identicurse-0.8-dev_setup.exe"
 
InstallDir $PROGRAMFILES\IdentiCurse
Name "IdentiCurse 0.8-dev"

section

setOutPath $INSTDIR
file dist\identicurse.exe
file dist\README
file dist\config.json

createShortCut "$SMPROGRAMS\IdentiCurse.lnk" "$INSTDIR\identicurse.exe"

writeUninstaller $INSTDIR\uninstall.exe
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IdentiCurse" \
                 "DisplayName" "IdentiCurse"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IdentiCurse" \
                 "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
 
sectionEnd
 

section "Uninstall"
 
delete $INSTDIR\identicurse.exe
delete $INSTDIR\README
delete $INSTDIR\config.json
delete $INSTDIR\uninstall.exe
RMDir $INSTDIR

delete $SMPROGRAMS\IdentiCurse.lnk

DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\IdentiCurse"
 
sectionEnd