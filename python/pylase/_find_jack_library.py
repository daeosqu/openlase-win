import platform
import os
from pathlib import Path
from ctypes.util import find_library as _find_library
from typing import Optional


def _resolve_package_library(search_dir: Path, *names: str) -> Optional[str]:
    """Return the first existing file path among `names` inside _DLL_DIR."""
    for name in names:
        candidate = search_dir / name
        if candidate.is_file():
            return str(candidate)
    return None


def find_jack_library() -> str:
    """Resolve a JACK client library suitable for ctypes loading."""
    system = platform.system()

    if system == "Windows":
        arch, _ = platform.architecture()
        if arch == "64bit":
            local_preference = ("libjack64.dll", "libjack.dll", "jack.dll")
            lookup_names = ("libjack64", "libjack", "jack")
        else:
            local_preference = ("libjack.dll", "jack.dll")
            lookup_names = ("libjack", "jack")

        libname = None
        # 1) Prefer a library bundled alongside the extension.
        win_dir = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
        win_dir = Path(win_dir)
        libname = _resolve_package_library(win_dir, *local_preference)

        # 2) Otherwise try platform lookup.
        if libname is None:
            for name in lookup_names:
                libname = _find_library(name)
                if libname:
                    break

        if libname:
            return libname

    elif system == "Darwin":
        libname = _find_library("jack")
        if libname:
            return libname
        # Homebrew default on Apple Silicon
        if platform.machine() == "arm64":
            libname = "/opt/homebrew/lib/libjack.dylib"
            if Path(libname).is_file():
                return libname

    else:
        # Linux and other Unixes
        libname = _find_library("jack")
        if libname:
            return libname

    return None

