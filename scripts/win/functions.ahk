;; functions.ahk

;; QJackCtl and OpenLase application control library

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
wait_invoke := 8.0
wait_exists := 4.0
wait_console := 4.0


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
  hwnd := ActivateOrStartProgram("^JACK Audio Connection Kit .* - QjackCtl$", cmd, activate, runparams, "", False, False)
  Return, hwnd
}

;;; Function

ActivateOrStartProgram(windowTitle, programName, activate=False, options="", console_title="", minimize_console=True, hide_console=False)
{
  global wait_invoke, wait_exists, wait_console
  hwnd := WinExist(windowTitle)
  If !hwnd
  {
    StartProgram(programName, options)
    wait_window := wait_invoke
  } else if activate {
    wait_window := wait_exists
  }
  If (activate)
  {
    hwnd := ActivateWindow(windowTitle, wait_window)
  }
  If (console_title AND (hide_console OR minimize_console))
  {
    P("Waiting console: console_title=" console_title)
    WinWait, %console_title% ahk_group ConsoleWindowGroup, , wait_console
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
    Abort("Can not start program: " programName)
  } Else {
    P("started")
  }
}

ActivateWindow(windowName, timeout=2.0)
{
  hwnd := _ActivateWindow(windowName, timeout)
  If (NOT hwnd > 0)
  {
    Abort("Can not activate window: " windowName)
  }
  Return, hwnd
}

_ActivateWindow(windowName, timeout=2.0)
{
  If (windowName == "") {
    Abort("ILLEGAL_ARGUMENT: ActivateWindow: windowName is empty")
  }
  P("WinWait...")
  WinWait, %windowName%, , %timeout%
  If ErrorLevel <> 0
  {
    P("_ActivateWindow: Can not find window: " windowName)
    Return, -1
  }
  P("WinWait...done")
  hwnd := WinExist(windowName)
  If (NOT hwnd > 0)
  {
    P("_ActivateWindow: Can not get window handle: " windowName)
    Return, -1
  }
  P("Activating Window...")
  While (timeout > 0) {
    WinActivate, ahk_id %hwnd%
    WinWaitActive, ahk_id %hwnd%, , 1
    If (ErrorLevel == 0)
    {
      P("Activating Window...done")
      Return, hwnd
    }
    timeout -= 1.0
    P("Activating Window...retry")
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
