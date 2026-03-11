import os
import sys
import re
import shutil
from pathlib import Path

from setuptools import Extension, setup, find_packages
from setuptools.command.build_ext import build_ext

from Cython.Build import cythonize


DLL_NAME = "ol.dll"

SOURCE_ROOT = os.environ["OPENLASE_SOURCE_DIR"]
BUILD_ROOT = os.environ["OPENLASE_BUILD_DIR"]
CONFIG_INCLUDE_DIR = os.path.join(BUILD_ROOT, "python")
LIBOL_DLL = os.environ.get("LIBOL_DLL")

def _read_version() -> str:
    """Robust version resolver for isolated builds.
    Order:
      1) env PYLASE_VERSION
      2) pylase/_version.py
    """

    env = os.environ.get("PYLASE_VERSION")
    if env:
        m = re.search(r"([0-9][0-9a-zA-Z\.\-\+]+)", env)
        if m:
            ver = m.group(1)
            print(f"[version] from env PYLASE_VERSION={ver}")
            return ver

    try:
        from pylase._version import __version__  # type: ignore
        print(f"[version] from pre-generated pylase/_version.py={__version__}")
        return __version__
    except Exception as e:
        print(f"[version] failed to import pylase._version: {e!r}")

    raise RuntimeError(
        "Could not resolve package version. please set PYLASE_VERSION or "
        "provide a pylase/_version.py."
    )


class CustomBuildExt(build_ext):
    """Custom build_ext to inject library dirs and copy ol.dll next to the pyd."""
    def finalize_options(self):
        # Run default option handling first
        super().finalize_options()

    def build_extensions(self):
        libol_dll = Path(LIBOL_DLL)

        # Add library dir to each extension
        for ext in self.extensions:
            if str(libol_dll.parent) not in ext.library_dirs:
                ext.library_dirs.append(str(libol_dll.parent))

        # Build extensions as usual
        super().build_extensions()

        if os.name == "nt":
            # Copy ol.dll or libol.dll next to each built extension
            for ext in self.extensions:
                ext_path = Path(self.get_ext_fullpath(ext.name))
                ext_path.parent.mkdir(parents=True, exist_ok=True)
                dll_dest = ext_path.parent / libol_dll.name
                if not libol_dll.exists():
                    raise FileNotFoundError(f"Can not find dll {libol_dll}")
                self.announce(f"copying {libol_dll} -> {dll_dest}", level=2)
                shutil.copy2(libol_dll, dll_dest)

extension = Extension(
    "pylase._pylase",
    sources=["pylase/_pylase.pyx"],
    include_dirs = [
        os.path.join(SOURCE_ROOT, "python"),
        CONFIG_INCLUDE_DIR,
        os.path.join(SOURCE_ROOT, "libol", "include"),
        os.path.join(BUILD_ROOT, "libol", "include"),
    ],
    library_dirs=[],
    libraries=["ol"],
    py_limited_api=True,
    define_macros=[("Py_LIMITED_API", "0x030A0000")],  # Python 3.10+
)

setup(
    name="pylase",
    version=_read_version(),
    ext_modules=cythonize(
        [extension],
        include_path=[CONFIG_INCLUDE_DIR],  # resolve `include "config.pxi"`
        language_level="3",
        build_dir=os.environ.get("PYLASE_CYTHON_BUILD_DIR"),
    ),
    cmdclass={"build_ext": CustomBuildExt},
    packages=find_packages(),
    package_data={"pylase": ["*.dll", "*.so", "*.dylib"]},
)
