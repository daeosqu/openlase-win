from __future__ import annotations

import ctypes
import importlib.machinery
import importlib.util
import os
import platform
import sys
import warnings
from pathlib import Path
from types import ModuleType
from typing import Optional


_IS_IMPORT_DEBUG = os.getenv("OL_IMPORT_DEBUG", "") != ""

# Keep references alive on Windows:
_DLL_REFS: list[ctypes.CDLL] = []


def _debug_print(*args, **kwargs) -> None:
    if _IS_IMPORT_DEBUG:
        msg = " ".join(str(a) for a in args)
        print(f"[pylase._init_debug] {msg}", file=sys.stderr, **kwargs)


def _find_project_root(pkg_dir: Path) -> Optional[Path]:
    """
    Find repo root by walking upward from pkg_dir:
    - wants: <root>/CMakeLists.txt and <root>/libol/
    """
    for p in [pkg_dir, *pkg_dir.parents]:
        if (p / "CMakeLists.txt").exists() and (p / "libol").exists():
            return p
    return None


def _resolve_build_dir(project_root: Optional[Path]) -> Optional[Path]:
    """
    Decide build dir:
    1) OL_BUILD_DIR env if exists
    2) <project_root>/build if exists
    """
    env = os.getenv("OL_BUILD_DIR")
    if env:
        d = Path(env)
        if not d.exists():
            warnings.warn(f"OL_BUILD_DIR is set to {d}, but that path does not exist")
            return None
        return d

    if project_root is None:
        return None

    d = project_root / "build"
    return d if d.exists() else None


def _load_c_extension(modname: str, search_dir: Path, package: str = "pylase") -> ModuleType:
    for suf in importlib.machinery.EXTENSION_SUFFIXES:
        ext_path = search_dir / f"{modname}{suf}"
        if ext_path.exists():
            spec = importlib.util.spec_from_file_location(f"{package}.{modname}", ext_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load spec for {ext_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{package}.{modname}"] = module
            spec.loader.exec_module(module)
            return module
    raise ImportError(f"{modname} not found in {search_dir}")


def load_pylase() -> ModuleType:
    pkg_dir = Path(__file__).resolve().parent

    project_root = _find_project_root(pkg_dir)
    build_dir = _resolve_build_dir(project_root)

    if build_dir:
        pylase_dir = build_dir / "python" / "pylase"
        libol_dir = build_dir / "libol"
    else:
        pylase_dir = pkg_dir
        libol_dir = pkg_dir
        if project_root is None:
            _debug_print("WARNING: Could not determine project root directory.")
        else:
            _debug_print("WARNING: No build directory found. Set OL_BUILD_DIR or build in <root>/build.")

    if platform.system() == "Windows":
        # 1. Load jack library first.
        from ._find_jack_library import find_jack_library
        jack_lib = find_jack_library()
        if jack_lib is None:
            raise OSError("JACK library not found")
        _debug_print(f"Loading JACK library: {jack_lib}")
        _DLL_REFS.append(ctypes.WinDLL(jack_lib))

        # 2. Load ol.dll next.
        ol_dll = str(libol_dir / "ol.dll")
        _debug_print(f"Loading ol.dll from: {ol_dll}")
        _DLL_REFS.append(ctypes.WinDLL(ol_dll))

    # Load pylase extension.
    _debug_print(f"Loading pylase extension from: {pylase_dir}")
    return _load_c_extension("_pylase", pylase_dir)
