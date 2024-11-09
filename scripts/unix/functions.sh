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

function olbuild_unix
{
    cmake -S "${OL_SOURCE_DIR}" -B "${OL_BUILD_DIR}" -G 'Ninja' -DCMAKE_BUILD_TYPE=${OL_BUILD_TYPE} -DCMAKE_INSTALL_PREFIX=/usr/local/openlase
    ninja -C "${OL_BUILD_DIR}"
}

function olclean
{
    ninja -C "${OL_BUILD_DIR}" clean
}

function olbuild_debian
{
    echo "Install OpenLase build dependencies..."
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
	${MINGW_PACKAGE_PREFIX}-libmodplug \
	${MINGW_PACKAGE_PREFIX}-python \
	${MINGW_PACKAGE_PREFIX}-python-click \
	${MINGW_PACKAGE_PREFIX}-python-ffmpeg-python \
	${MINGW_PACKAGE_PREFIX}-python-pillow \
	${MINGW_PACKAGE_PREFIX}-python-opencv \

    pip install --no-input jaconv yt-dlp tinydb

    PKG_CONFIG_PATH=/ucrt64/lib/ffmpeg4.4/pkgconfig:$PKG_CONFIG_PATH cmake -S "${OL_SOURCE_DIR}" -B "${OL_BUILD_DIR}" -G 'Ninja' -DCMAKE_BUILD_TYPE=${OL_BUILD_TYPE} -DCMAKE_INSTALL_PREFIX=${MINGW_PREFIX}/local/openlase -DPython3_EXECUTABLE="$(asdf which python3 2>/dev/null)"

    ninja -C "${OL_BUILD_DIR}"
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
