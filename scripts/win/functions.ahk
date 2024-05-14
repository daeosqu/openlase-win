;; raise.ahk

;; Raise window

;; Author: Daisuke Arai

#NoEnv

SetBatchLines, -1
SetKeyDelay, -1
SetMouseDelay, -1
DetectHiddenWindows, Off
SetTitleMatchMode, RegEx
SetControlDelay, -1
SendMode, Input

CoordMode, ToolTip, Window
CoordMode, Pixel, Window
CoordMode, Mouse, Window
CoordMode, Caret, Window
CoordMode, Menu, Window

DEBUG := 0


old_hwnd := WinExist("A")
KeyWait, Shift
KeyWait, Alt
KeyWait, Ctrl

GroupAdd, ConsoleWindowGroup, ahk_class ConsoleWindowClass
GroupAdd, ConsoleWindowGroup, ahk_class CASCADIA_HOSTING_WINDOW_CLASS

RunSimulator(arguments="", runparams="", activate=True, hide_console=False, minimize_console=True)
{
  cmd_name := "simulator.exe"
  cmd := cmd_name . " " . arguments
  hwnd := ActivateOrStartProgram("^OpenLase Simulator$", cmd, activate, runparams, cmd_name, minimize_console, hide_console)
  Return, hwnd
}

RunOutput(arguments="", runparams="", activate=True, hide_console=False, minimize_console=True)
{
  cmd_name := "output.exe"
  cmd := cmd_name . " " . arguments
  hwnd := ActivateOrStartProgram("^Laser output configuration$", cmd, activate, runparams, cmd_name, minimize_console, hide_console)
  Return, hwnd
}

RunQjackCtl(arguments="", runparams="", activate=True)
{
  cmd_name = "qjackctl.exe"
  cmd := cmd_name . " " . arguments
  hwnd := ActivateOrStartProgram("^JACK Audio Connection Kit .* - QjackCtl$", cmd, activate, runparams, "\\qjackctl.exe$", False, False)
  Return, hwnd
}

;;; 関数

ActivateOrStartProgram(windowTitle, programName, activate=False, options="", console_title="", minimize_console=True, hide_console=False)
{
  hwnd := WinExist(windowTitle)
  If !hwnd
  {
    StartProgram(programName, options)
    hwnd := ActivateWindow(windowTitle, 4.0)
  } else if activate {
    hwnd := ActivateWindow(windowTitle, 2.0)
  }
  If console_title
  {
    WinWait, %console_title% ahk_group ConsoleWindowGroup, , 2.0
    If hide_console
    {
      WinHide, %console_title% ahk_group ConsoleWindowGroup
    }
    Else If minimize_console
    {
      WinMinimize, %console_title% ahk_group ConsoleWindowGroup
    }
  }
  Return, hwnd
}

StartProgram(programName, options="")
{
  P("starting program " programName)
  Run, %programName%, , UseErrorLevel %options%
  If (ErrorLevel == "ERROR" || ErrorLevel <> 0)
  {
    Abort("プログラムを起動できません: " programName)
  }
}

ActivateWindow(windowName, timeout=2.0)
{
  hwnd := _ActivateWindow(windowName, timeout)
  If (NOT hwnd > 0)
  {
    Abort("ウィンドウをアクティブ化できませんでした: " windowName)
  }
  Return, hwnd
}

_ActivateWindow(windowName, timeout=2.0)
{
  If (windowName == "") {
    Abort("ILLEGAL_ARGUMENT: ActivateWindow: windowName is empty")
  }
  WinWait, %windowName%, , %timeout%
  If ErrorLevel <> 0
  {
    P("_ActivateWindow: Can not find window: " windowName)
    Return, -1
  }
  hwnd := WinExist(windowName)
  If (NOT hwnd > 0)
  {
    P("_ActivateWindow: Can not get window handle: " windowName)
    Return, -1
  }
  While (timeout > 0) {
    WinActivate, ahk_id %hwnd%
    WinWaitActive, ahk_id %hwnd%, , 1
    If (ErrorLevel == 0)
    {
      Return, hwnd
    }
    timeout -= 1.0
  }
  Return, -1
}

WinToClient(hwnd, ByRef x, ByRef y)
{
    WinGetPos, wx, wy,,, ahk_id %hwnd%
    VarSetCapacity(pt, 8)
    NumPut(x + wx, pt, 0)
    NumPut(y + wy, pt, 4)
    DllCall("ScreenToClient", "uint", hwnd, "uint", &pt)
    x := NumGet(pt, 0, "int")
    y := NumGet(pt, 4, "int")
}

GetClientXY(hwnd, ByRef X, ByRef Y)
{
    VarSetCapacity(rc,16)
    DllCall("GetClientRect", "Uint", hwnd, "Uint", &rc)
    X:=NumGet(rc,0,"Int")
    Y:=NumGet(rc,4,"Int")
}

Abort(mess)
{
  ShowMessage(mess)
  ExitApp, 1
}

PDebugInfo()
{
  P(DebugInfo())
}

DebugInfo()
{
  title := WinGetActiveTitle()
  info =
(
--- DebugInfo  ---
  Title      : %title%
  ErrorLevel : %ErrorLevel%
)
  Return, info
}

ShowMessage(mess)
{
  Global DEBUG
  If DEBUG
  {
    FileAppend, %mess%`n, *
  } Else {
    MsgBox, %mess%
  }
}

WinGetActiveTitle()
{
  WinGetTitle, title, A
  Return, title
}

PActive()
{
  P(WinGetActiveTitle())
}

P(mess)
{
  Global DEBUG
  If DEBUG
    DllCall("AllocConsole")
  FileAppend, %mess%`n, *
  OutputDebug, %mess%
}

; Local Variables:
; coding: utf-8-with-signature-dos
; End:
