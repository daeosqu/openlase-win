;; run-output.ahk

;; Author: Daisuke Arai

#Warn
#SingleInstance ignore

#Include %A_ScriptDir%\functions.ahk

Arguments := ""
for Key, Value in A_Args
  Arguments .= Value . " "

;DllCall("AllocConsole")

RunOutput(Arguments)

; WinActivate, ahk_id %old_hwnd%
; WinWaitActive, ahk_id %old_hwnd%
; ExitApp

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
