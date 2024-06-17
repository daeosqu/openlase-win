;; run-simulator.ahk

;; Author: Daisuke Arai

#NoEnv
#Warn
#SingleInstance ignore

SetBatchLines, -1

#Include %A_ScriptDir%\common.ahk
;;DEBUG := True

activate := True
hide_consle := True

RunSimulator(Arguments, "", activate, hide_consle)
Restore()

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
