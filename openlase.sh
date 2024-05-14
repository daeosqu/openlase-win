#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ -e "$SCRIPT_DIR/.env" ]; then
    echo "Loading $SCRIPT_DIR/.env..."
    set -o allexport
    source "$SCRIPT_DIR/.env"
    set +o allexport
fi

if [ -n "$OL_DEVEL" ]; then
    export OL_DIR=$SCRIPT_DIR
    uname=$(uname)
    case "$uname" in
	MINGW64*)
	    name=mingw64;;
	*)
	    name=$uname;;
    esac

    OL_BUILD_DIR=$OL_DIR/build-$name
    PATH=$OL_BUILD_DIR/libol:$PATH
    PATH=$OL_BUILD_DIR/tools:$PATH
    PATH=$OL_BUILD_DIR/tools/qplayvid:$PATH
    PATH=$OL_BUILD_DIR/output:$PATH
    PATH=$OL_BUILD_DIR/examples:$PATH
    PATH=$OL_BUILD_DIR/examples/lase_demo:$PATH
    PATH=$OL_BUILD_DIR/jopa_install/usr/local/bin:$PATH
    PATH=$OL_DIR/scripts:$PATH
    export LD_LIBRARY_PATH=$OL_DIR/build/libol:$LD_LIBRARY_PATH
    export PYTHONPATH=$OL_BUILD_DIR/python:$PYTHONPATH
else
    if [ -e "$HOME/.openlase" ]; then
	echo "Loading $HOME/.openlase..."
	set -o allexport
	source "$HOME/.openlase"
	set +o allexport
    fi
    export OL_DIR=/usr/local/openlase
    unset OL_BUILD_DIR
    PATH=$OL_DIR/bin:$PATH
    export LD_LIBRARY_PATH=$OL_DIR/lib:$LD_LIBRARY_PATH
    export PYTHONPATH=$OL_DIR/bin:$PYTHONPATH
fi

export OL_DATA_DIR=$HOME/.cache/openlase
mkdir -p "$OL_DATA_DIR"

IS_WSL=${WSL_DISTRO_NAME+1}
if [ -n "$IS_WSL" ]; then
    unset LIBGL_ALWAYS_INDIRECT
    # ahkv1_dir=$(powershell.exe -Command 'Get-ChildItem "C:\Program Files\AutohotKey" -Directory | Where-Object -Property Name -like v1.* | Select-Object -First 1 | % { $_.FullName }' | tr -d '\r')
    # if [ -n "$ahkv1_dir" ]; then
    # 	PATH=$(wslpath -u "$ahkv1_dir"):$PATH
    # fi
fi

. $SCRIPT_DIR/scripts/unix/functions.sh

if [ -n "$OL_DEVEL" ]; then
    cd "$OL_DIR"
fi
