; KeyPulse NSIS installer hooks.
; The stock Tauri uninstaller's "Delete application data" checkbox only
; removes the bundle-id folders under %APPDATA% / %LOCALAPPDATA%. Extend it
; so the portable database folder next to the exe is removed as well when
; the user explicitly opts in. The checkbox defaults to unchecked, so a
; normal uninstall always keeps keypulse-data.

!macro NSIS_HOOK_POSTUNINSTALL
  ${If} $DeleteAppDataCheckboxState = 1
    DetailPrint "Removing keypulse-data (delete application data selected)"
    RmDir /r "$INSTDIR\keypulse-data"
    RmDir "$INSTDIR"
  ${EndIf}
!macroend
