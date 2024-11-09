#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. $SCRIPT_DIR/scripts/unix/openlaserc.sh

if [ -n "$OL_DEVEL" ]; then
    cd "$OL_DIR"
fi
