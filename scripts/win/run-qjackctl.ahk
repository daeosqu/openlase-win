;; run-qjackctl.ahk

;; Author: Daisuke Arai

#NoEnv
#Warn
#SingleInstance ignore
SetBatchLines, -1

#Include %A_ScriptDir%\common.ahk
;;DEBUG := True

wait_invoke := 30.0
wait_exists := 5.0

CloseSubWindows()
{
  start := A_TickCount
  last_close := 0
  P("CloseSubWindows...")
  Loop, 1000
  {
    If (A_TickCount > start + 10000)
    {
      P("Time out for closing all sub windows for qjackctl")
      Return
    }
;;    hwnd := WinExist("^(Patchbay|Messages / Status|Graph|Session)\ -\ QjackCtl$ ahk_exe qjackctl.exe")
    hwnd := WinExist("^(Patchbay|Messages / Status|Session)\ -\ QjackCtl$ ahk_exe qjackctl.exe")
    If hwnd
    {
      P("Found " hwnd)
      WinActivate, ahk_id %hwnd%
      WinWaitActive, ahk_id %hwnd%
      Send, !{F4}
      last_close := A_TickCount
    } Else {
      If (last_close) {
        If (A_TickCount > last_close + 1000) {
          P("No more sub windows")
          Return
        }
      } Else If (A_TickCount > start + 5000) {
        P("Timed out!")
        Return
      }
    }
    Sleep, 100
  }
  P("Looping!")
}

RunQjackCtl(Arguments)
CloseSubWindows()
Restore()

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
