# function ahk() { AutoHotkeyU64.exe "$@"; }

function run_qjackctl
{
    qjackctl &
}

function run_simulator
{
    simulator -q $OL_SIMULATOR_ARGS &
}

function run_jackd_dummy
{
    jackd -ddummy -r48000 -p4096 &
}

function jack_load_netmanager
{
    jack_load netmanager -i -c
}

function run_jopa
{
    jopa &
}

function olstart
{
    run_qjackctl
    jack_wait -w
    run_simulator
    if [ -n "${WSL_DISTRO_NAME+1}" ]; then
	run_jopa
    fi
}

function olstart_slave
{
    if [ -n "${WSL_DISTRO_NAME+1}" ]; then
	WSL_IP=$(sed -ne 's,^\s*nameserver\s*\(.*\)$,\1,p' /etc/resolv.conf)
	jackd -d net -a $WSL_IP -n olnet -C 7 -P 7 &
    fi
    jack_wait -w
    run_qjackctl --active-patchbay "$OL_DIR/config/openlase-netjack.xml"
}

function olstop
{
    killall simulator
    if [ -n "${WSL_DISTRO_NAME+1}" ]; then
	killall jopa
    fi
    killall -9 qjackctl
    killall jackd
}
