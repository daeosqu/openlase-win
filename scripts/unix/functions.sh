# function ahk() { AutoHotkeyU64.exe "$@"; }

IS_WSL=${WSL_DISTRO_NAME+1}

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
    if [ -n "$IS_WSL" ]; then
	run_jopa
    fi
}

function olstart_slave
{
    run_jackd_dummy
    jack_wait -w
    run_qjackctl --active-patchbay "$OL_DIR/config/openlase-netjack.xml"
    run_simulator
}

function olstop
{
    killall simulator
    if [ -n "$IS_WSL" ]; then
	killall jopa
    fi
    killall -9 qjackctl
    killall jackd
}

function olbuild_unix
{
    cd "$OL_BUILD_DIR"
    cmake .. -G 'Ninja' -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local/openlase
    ninja clean && ninja
}

function olbuild_debian
{
    sudo apt-get install -y python3 python3-dev cython3 libjack-jackd2-dev libavcodec-dev libavutil-dev libswresample-dev libavformat-dev libswscale-dev libavdevice-dev freeglut3-dev libopenmpt-modplug-dev qtbase5-dev
    olbuild_unix
}

function olbuild_mingw
{
    pacman -Syuu
    pacman --needed --noconfirm -S \
	base-devel git wget sed diffutils grep tar unzip \
	${MINGW_PACKAGE_PREFIX}-toolchain \
	${MINGW_PACKAGE_PREFIX}-pkgconf \
	${MINGW_PACKAGE_PREFIX}-cmake \
	${MINGW_PACKAGE_PREFIX}-ninja \
	${MINGW_PACKAGE_PREFIX}-yasm \
	${MINGW_PACKAGE_PREFIX}-freeglut \
	${MINGW_PACKAGE_PREFIX}-ffmpeg4.4 \
	${MINGW_PACKAGE_PREFIX}-python3 \
	${MINGW_PACKAGE_PREFIX}-python3-pip \
	${MINGW_PACKAGE_PREFIX}-cython \
	${MINGW_PACKAGE_PREFIX}-ncurses \
	${MINGW_PACKAGE_PREFIX}-qt5 \
	${MINGW_PACKAGE_PREFIX}-fdk-aac \
	${MINGW_PACKAGE_PREFIX}-libmodplug
    cd "$OL_BUILD_DIR"
    PKG_CONFIG_PATH=/ucrt64/lib/ffmpeg4.4/pkgconfig:$PKG_CONFIG_PATH cmake .. -G 'Ninja' -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${MINGW_PREFIX}/local/openlase
    ninja clean && ninja
}

function olbuild
{
    if [ -n "$OL_BUILD_DIR" ]; then
	mkdir -p "$OL_BUILD_DIR"
	cd "$OL_BUILD_DIR"
	name=$(cat /etc/os-release | sed -e 's/^NAME\s*=\s*//')
	case "$name" in
	    *MSYS*)
		olbuild_mingw;;
	    *Ubuntu*|*Debian*)
		olbuild_debian;;
	    *)
		olbuild_unix;;
	esac
    else
	echo "Please load openlace.sh in OpenLase source directory."
    fi
}

function olinstall
{
    if [ -n "$OL_BUILD_DIR" ]; then
	mkdir -p "$OL_BUILD_DIR"
	cd "$OL_BUILD_DIR"
	case "$(uname)" in
	    MINGW*)
		ninja install;;
	    *)
		sudo ninja install;;
	esac
    else
	echo "Please load openlace.sh in OpenLase source directory."
    fi
}
