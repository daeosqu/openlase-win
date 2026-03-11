"""Python package wrapper for the pylase extension.
"""

from __future__ import annotations
import os
import platform as _platform

_IS_OL_DEVEL = os.getenv("OL_DEVEL", "").lower() not in ("", "0", "no", "false")

if _IS_OL_DEVEL:
    from ._load_pylase import load_pylase
    load_pylase()
elif _platform.system() == "Windows":
    cand = ["JACK_DLL_DIR", "SystemRoot", "WINDIR"]
    jack_dll_dir = next((v for k in cand if (v := os.environ.get(k))), None)
    if jack_dll_dir is None:
        msg = f"Could not determine environment variable: {', '.join(cand)}"
        raise RuntimeError(msg)

    os.add_dll_directory(jack_dll_dir)

from ._pylase import *
