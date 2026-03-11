function ahk
{
    AutoHotkeyU64.exe $args
}

function run_jackd_dummy
{
    wt.exe cmd /c jackd -ddummy -r48000 -p4096
}

function run_qjackctl
{
    ahk $PSScriptRoot\run-qjackctl.ahk "$env:OL_QJACKCTL_ARGS" $args
}

function run_simulator
{
    ahk $PSScriptRoot\run-simulator.ahk "$env:OL_SIMULATOR_ARGS" $args
}

function run_output
{
    ahk $PSScriptRoot\run-output.ahk "$env:OL_OUTPUT_ARGS" $args
}

function olstart
{
    run_qjackctl
    jack_wait -w
    $arguments = "-q $env:OL_SIMULATOR_ARGS"
    Start-Process "simulator.exe" -ArgumentList $arguments
    if (-Not $env:OL_NO_RUN_OUTPUT) {
	$arguments = "-q $env:OL_OUTPUT_ARGS"
	Start-Process "output.exe" -ArgumentList $arguments
    }
}

function olstart_slave
{
    run_jackd_dummy
    jack_wait -w
    run_qjackctl --active-patchbay "$env:OL_DIR/config/openlase-netjack.xml"
    run_simulator
}

function olstop
{
    taskkill /im jackd.exe /f
    taskkill /im qjackctl.exe /f
    taskkill /im simulator.exe /f
}

Export-ModuleMember -Function ahk, run_jackd_dummy, run_qjackctl, run_simulator, run_output, olstart, olstart2, olstart_slave, olstop
