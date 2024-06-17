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
    run_simulator
    run_output
}

function olstart_slave
{
    run_jackd_dummy
    jack_wait -w
    run_qjackctl --active-patchbay "$env:OL_DIR\config\openlase-netjack.xml"
    run_simulator
}

function olstop
{
    taskkill /im jackd.exe /f
    taskkill /im qjackctl.exe /f
    taskkill /im simulator.exe /f
}

function olbuild
{
    if ($env:OL_BUILD_DIR -And $env:OL_DIR) {
	cd "$env:OL_DIR" -ea 0 | Out-Null
	cmake -S . -B "$env:OL_BUILD_DIR" -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=On -DPython3_ROOT_DIR="$env:OL_PYTHON_DIR" -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"
	ninja -C "$env:OL_BUILD_DIR"
    } else {
	Write-Host "OL_DIR or OL_BUILD_DIR is not defined. Please run openlace.cmd in OpenLase source directory."
    }
}

function olclean
{
    if ($env:OL_BUILD_DIR) {
	md "$env:OL_BUILD_DIR" -ea 0 | Out-Null
	cd "$env:OL_BUILD_DIR"
	cmake --build . --target clean
    } else {
	Write-Host "Please run openlace-dev.cmd in OpenLase source directory."
    }
}

function olinstall
{
    if (Test-Path "$env:OL_BUILD_DIR") {
	olstop 2>&1 | Out-Null
	gsudo cmake --install "$env:OL_BUILD_DIR"
    } else {
	Write-Host "OL_BUILD_DIR is not set. Please run openlace-dev.cmd in OpenLase source directory."
    }
}

Export-ModuleMember -Function ahk, run_jackd_dummy, run_qjackctl, run_simulator, run_output, olstart, olstart_slave, olstop, olbuild, olclean, olinstall
