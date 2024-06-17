#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ -z "${OL_DEVEL+1}" ]; then
    if [ -d "${OL_DIR}/.git" ]; then
	OL_DEVEL=""
    fi
fi

. $SCRIPT_DIR/scripts/unix/openlaserc.sh

if [ -n "$OL_DEVEL" ]; then
    cd "$OL_DIR"
fi
