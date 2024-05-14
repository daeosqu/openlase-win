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
    run_qjackctl --active-patchbay "$env:OL_DIR/config/openlase-netjack.xml"
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
    if ($env:OL_BUILD_DIR) {
	md "$env:OL_BUILD_DIR" -ea 0 | Out-Null
	cd "$env:OL_BUILD_DIR"
	cmake .. -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DPython3_ROOT_DIR=$env:OL_PYTHON_DIR -DCMAKE_TOOLCHAIN_FILE="$env:USERPROFILE/scoop/apps/vcpkg/current/scripts/buildsystems/vcpkg.cmake" -DCMAKE_PREFIX_PATH="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64"
	cmake --build . --config Release
    } else {
	Write-Host "Please run openlace-dev.cmd in OpenLase source directory."
    }
}

function olinstall
{
    if ($env:OL_BUILD_DIR) {
	olstop 2>&1 | Out-Null
	md "$env:OL_BUILD_DIR" -ea 0 | Out-Null
	cd "$env:OL_BUILD_DIR"
	gsudo cmake --build . --config Release --target install
    } else {
	Write-Host "Please run openlace-dev.cmd in OpenLase source directory."
    }
}

Export-ModuleMember -Function ahk, run_jackd_dummy, run_qjackctl, run_simulator, olstart, olstart_slave, olstop, olbuild, olinstall
