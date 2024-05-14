;; run-qjackctl.ahk

;; Author: Daisuke Arai

SetBatchLines, -1

#NoEnv
#Warn
#SingleInstance ignore

;DllCall("AllocConsole")

#Include %A_ScriptDir%\functions.ahk

CloseSubWindows()
{
  start := A_TickCount
  last_close := A_TickCount
  Loop, 1000
  {
    If (A_TickCount > start + 10000)
    {
      P("Time out for closing all sub windows for qjackctl")
      Return
    }
    hwnd := WinExist("^(Patchbay|Messages / Status|Graph|Session)\ -\ QjackCtl$ ahk_exe qjackctl.exe")
    If hwnd
    {
      P("Found " hwnd)
      WinActivate, ahk_id %hwnd%
      WinWaitActive, ahk_id %hwnd%
      Send, !{F4}
      last_close := A_TickCount
    } Else If (A_TickCount > start + 500 && A_TickCount > last_close + 500) {
      P("No more sub windows")
      Return
    } Else {
      P("Try finding sub windows...")
    }
    Sleep, 100
  }
}

Arguments := ""
for Key, Value in A_Args
  Arguments .= Value . " "

RunQjackCtl(Arguments)
CloseSubWindows()

Sleep, 3000

; WinActivate, ahk_id %old_hwnd%
; WinWaitActive, ahk_id %old_hwnd%
; ExitApp

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
