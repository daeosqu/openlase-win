;; run-output.ahk

;; Author: Daisuke Arai

#NoEnv
#Warn
#SingleInstance ignore

SetBatchLines, -1

#Include %A_ScriptDir%\common.ahk
;;DEBUG := True

activate := False
hide_console := True
RunOutput(Arguments, "", activate, hide_console)
Restore()

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
