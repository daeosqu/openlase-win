#!/usr/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

OL_DIR=${SCRIPT_DIR}/../..
if [ -d "${OL_DIR}/.git" ]; then
    if [ -z "${OL_DEVEL+1}" ]; then
	OL_DEVEL=1
    fi
    OL_SOURCE_DIR=${OL_DIR}
else
    OL_DIR=${SCRIPT_DIR}/..
fi
export OL_DIR=$(readlink -f "$OL_DIR")
export OL_BUILD_TYPE=${OL_BUILD_TYPE:-Release}

if [ -z "${OL_PYTHON_DIR}" ] && which asdf 2>/dev/null 2>&1; then
    export OL_PYTHON_DIR=$(asdf where python 2>/dev/null | sed 's/.*System version.*//')
fi
export OL_PYTHON=$(asdf which python3 2>/dev/null || which python3 2>/dev/null)

if [ -n "$OL_DEVEL" ]; then

    if [ -e "$SCRIPT_DIR/.openlaserc" ]; then
	echo "Loading $SCRIPT_DIR/.openlaserc..."
	set -o allexport
	source "$SCRIPT_DIR/.openlaserc"
	set +o allexport
    fi

    uname=$(uname)
    case "$uname" in
	MINGW64*)
	    name=MINGW;;
	*)
	    name=$uname;;
    esac

    export OL_BUILD_DIR=$OL_DIR/build-$OL_BUILD_TYPE.$name
    PATH=$OL_BUILD_DIR/libol:$PATH
    PATH=$OL_BUILD_DIR/tools:$PATH
    PATH=$OL_BUILD_DIR/tools/qplayvid:$PATH
    PATH=$OL_BUILD_DIR/output:$PATH
    PATH=$OL_BUILD_DIR/examples:$PATH
    PATH=$OL_BUILD_DIR/examples/lase_demo:$PATH
    PATH=$OL_BUILD_DIR/jopa_install/usr/local/bin:$PATH
    PATH=$OL_DIR/examples:$PATH
    PATH=$OL_DIR/tools:$PATH
    PATH=$OL_DIR/scripts/unix:$PATH
    if [ -n "$OL_PYTHON_DIR" ]; then
	PATH=$OL_PYTHON_DIR/bin:$PATH
    fi
    export LD_LIBRARY_PATH=$OL_DIR/build/libol:$LD_LIBRARY_PATH
    export PYTHONPATH=$OL_BUILD_DIR/python:$PYTHONPATH
else
    if [ -e "$HOME/.openlase" ]; then
	echo "Loading $HOME/.openlase..."
	set -o allexport
	source "$HOME/.openlase"
	set +o allexport
    fi
    unset OL_BUILD_DIR
    PATH=$OL_DIR/bin:$PATH
    export LD_LIBRARY_PATH=$OL_DIR/lib:$LD_LIBRARY_PATH
    export PYTHONPATH=$OL_DIR/bin:$PYTHONPATH
fi

export OL_DATA_DIR=$HOME/.cache/openlase
mkdir -p "$OL_DATA_DIR"

if [ -n "${WSL_DISTRO_NAME+1}" ]; then
    unset LIBGL_ALWAYS_INDIRECT
    # ahkv1_dir=$(powershell.exe -Command 'Get-ChildItem "C:\Program Files\AutohotKey" -Directory | Where-Object -Property Name -like v1.* | Select-Object -First 1 | % { $_.FullName }' | tr -d '\r')
    # if [ -n "$ahkv1_dir" ]; then
    # 	PATH=$(wslpath -u "$ahkv1_dir"):$PATH
    # fi
fi

. $SCRIPT_DIR/functions.sh
