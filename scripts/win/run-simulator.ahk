;; run-simulator.ahk

;; Author: Daisuke Arai

;DllCall("AllocConsole")

SetBatchLines, -1
#NoEnv
#Warn
#SingleInstance ignore

#Include %A_ScriptDir%\functions.ahk

Arguments := ""
for Key, Value in A_Args
  Arguments .= Value . " "

RunSimulator(Arguments, "", True, False)

; WinActivate, ahk_id %old_hwnd%
; WinWaitActive, ahk_id %old_hwnd%
; ExitApp

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
