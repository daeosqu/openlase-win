#!/usr/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export OL_BUILD_DIR=$(readlink -f ${OL_BUILD_DIR:-./build})

OL_DIR=${SCRIPT_DIR}/../..
if [ -f "${OL_DIR}/CMakeLists.txt" ]; then
    echo "Using source directory: ${OL_DIR}" >&2
    OL_SOURCE_DIR=$(readlink -f ${OL_SOURCE_DIR:-${OL_DIR}})
    OL_DIR=${OL_SOURCE_DIR}
else
    OL_INSTALLED_DIR=$(readlink -f ${SCRIPT_DIR}/..)
    OL_DIR=${OL_INSTALLED_DIR}
fi

if [ -n "${OL_SOURCE_DIR:-}" ]; then
    OPENLASE_RC="${OL_SOURCE_DIR}/.openlaserc"
else
    OPENLASE_RC="$HOME/.openlaserc"
fi

if [ -e "${OPENLASE_RC}" ]; then
    echo "Loading ${OPENLASE_RC}..."
    set -o allexport
    source "${OPENLASE_RC}"
    set +o allexport
fi

if [ -n "${OL_SOURCE_DIR:-}" ]; then
    uname=$(uname)
    case "$uname" in
	MINGW64*)
	    name=MINGW;;
	*)
	    name=$uname;;
    esac

    PATH=$OL_DIR/examples:$PATH
    PATH=$OL_DIR/tools:$PATH
    PATH=$OL_DIR/scripts/unix:$PATH

    if [ -n "${OL_BUILD_DIR:-}" ]; then
	PATH=$OL_BUILD_DIR/libol:$PATH
	PATH=$OL_BUILD_DIR/tools:$PATH
	PATH=$OL_BUILD_DIR/tools/qplayvid:$PATH
	PATH=$OL_BUILD_DIR/output:$PATH
	PATH=$OL_BUILD_DIR/examples:$PATH
	PATH=$OL_BUILD_DIR/examples/lase_demo:$PATH
	PATH=$OL_BUILD_DIR/jopa_install/usr/local/bin:$PATH
	export LD_LIBRARY_PATH=$OL_DIR/build/libol:$LD_LIBRARY_PATH
	export PYTHONPATH=$OL_BUILD_DIR/python:$PYTHONPATH
    else
	echo "WARNING: OL_BUILD_DIR is not set, skipping build directory setup"
    fi
else
    PATH=$OL_INSTALLED_DIR/bin:$PATH
    export LD_LIBRARY_PATH=$OL_INSTALLED_DIR/lib:$LD_LIBRARY_PATH
fi

export OL_DATA_DIR=${OL_DATA_DIR:-$HOME/.cache/openlase}
#mkdir -p "$OL_DATA_DIR"

if [ -n "${WSL_DISTRO_NAME+1}" ]; then
    unset LIBGL_ALWAYS_INDIRECT
    # ahkv1_dir=$(powershell.exe -Command 'Get-ChildItem "C:\Program Files\AutohotKey" -Directory | Where-Object -Property Name -like v1.* | Select-Object -First 1 | % { $_.FullName }' | tr -d '\r')
    # if [ -n "$ahkv1_dir" ]; then
    # 	PATH=$(wslpath -u "$ahkv1_dir"):$PATH
    # fi
fi

. $SCRIPT_DIR/functions.sh
