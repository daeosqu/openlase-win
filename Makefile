# -*- coding: utf-8-unix -*-

SHELL := sh

include $(dir $(abspath $(lastword $(MAKEFILE_LIST))))/common.mk

OL_ROOT      ?= .
OL_BUILD_DIR ?= ./build-$(UNAME)
OL_VENV_DIR  ?= ./venv-$(UNAME)
OL_ROOT      := $(abspath $(OL_ROOT))
OL_BUILD_DIR := $(abspath $(OL_BUILD_DIR))
OL_VENV_DIR  := $(abspath $(OL_VENV_DIR))

default: help

# Windows
ifeq ($(UNAME),Windows)
  #CMAKE_GENERATOR          ?= Ninja
  CMAKE_GENERATOR          ?= Visual Studio 17 2022
  ifneq (,$(findstring Visual Studio,$(CMAKE_GENERATOR)))
    CMAKE_GENERATOR_PLATFORM ?= x64
  endif
  CMAKE_TOOLCHAIN_FILE     ?= $(VCPKG_ROOT)\scripts\buildsystems\vcpkg.cmake
  #CMAKE_TOOLCHAIN_FILE     ?= C:\Program Files\Microsoft Visual Studio\2022\Community\VC\vcpkg\scripts\buildsystems\vcpkg.cmake
  Qt5_DIR                  ?= C:/Qt/Qt5.14.2/5.14.2/msvc2017_64/lib/cmake/Qt5
  PYVER                    ?= 3.12.4
  VENV_PYTHON := $(OL_VENV_DIR)/Scripts/python.exe
  ifneq ($(PYVER),)
    BASE_PYTHON := pyenv exec python
  else
    #BASE_PYTHON := C:/opt/python311/python.exe
    BASE_PYTHON ?= python
  endif
# Posix
else
  CMAKE_GENERATOR ?= Ninja
  BASE_PYTHON ?= python3
  VENV_PYTHON := $(OL_VENV_DIR)/bin/python
endif

export OL_BUILD_DIR
export CMAKE_GENERATOR
export CMAKE_GENERATOR_PLATFORM
export CMAKE_TOOLCHAIN_FILE
export Qt5_DIR

# Windows
ifeq ($(UNAME),Windows)
shell: prep
	@powershell -NoExit -Command "if (Test-Path '$(OL_VENV_DIR)/Scripts/Activate.ps1') { . $(OL_VENV_DIR)/Scripts/Activate.ps1 }; $(OL_ROOT)\scripts\win\openlase_rc.ps1; cd $(abspath .)"
  ifneq ($(PYVER),)
install-python:
	pyenv install $(PYVER)
	pyenv local $(PYVER)
  endif
else
shell: prep
	@bash --rcfile <(echo ". ${HOME}/.bashrc; . venv-Linux/bin/activate; . openlase-win/scripts/unix/openlaserc.sh")

install-python:
endif

help:
	@$(ECHO) "Usage:" >&2
	@$(ECHO) "  make shell        Open a shell with the build environment set up" >&2
	@$(ECHO) "  make build        Build the project" >&2
	@$(ECHO) "  make dist         Create installer" >&2

define diag_cmd
	@p="$$(which $(1) 2>/dev/null)"; \
	if [ -n "$$p" ]; then \
		v="$$( $(1) --version 2>/dev/null | head -n 1 )"; \
		$(ECHO) "  $(1): $$v ($$p)"; \
	else \
		$(ECHO) "  $(1): Not found"; \
	fi
endef

diag:
	@$(ECHO) "Parameters:"
	@$(ECHO) "  UNAME:                    $(UNAME)"
	@$(ECHO) "  OL_ROOT:                  $(OL_ROOT)"
	@$(ECHO) "  OL_BUILD_DIR:             $(OL_BUILD_DIR)"
	@$(ECHO) "  OL_VENV_DIR:              $(OL_VENV_DIR)"
	@$(ECHO) "  CMAKE_GENERATOR:          $(CMAKE_GENERATOR)"
	@$(ECHO) "  CMAKE_GENERATOR_PLATFORM: $(CMAKE_GENERATOR_PLATFORM)"
	@$(ECHO) "  CMAKE_TOOLCHAIN_FILE:     $(CMAKE_TOOLCHAIN_FILE)"
	@$(ECHO) "  Qt5_DIR:                  $(Qt5_DIR)"
	@$(ECHO) "  BASE_PYTHON:              $(BASE_PYTHON)"
	@$(ECHO) "  VENV_PYTHON:              $(VENV_PYTHON)"
	@$(ECHO) ""
	@$(ECHO) "Tools:"
	$(call diag_cmd,cmake)
	$(call diag_cmd,ninja)
	$(call diag_cmd,python)

distclean:
	$(RM) -r $(OL_BUILD_DIR)
	$(RM) -r $(OL_VENV_DIR)
	$(RM) -r python/build

clean:
	cmake --build $(OL_BUILD_DIR) --target clean

prep: prep-venv
prep-venv: $(OL_VENV_DIR)/.done
$(OL_VENV_DIR)/.done:
	$(MAKE) prep-venv-force-$(UNAME)
	$(TOUCH) $@

prep-venv-force-Windows: install-python
	$(RM) -r $(OL_VENV_DIR)
	$(BASE_PYTHON) -m venv $(OL_VENV_DIR)
	$(VENV_PYTHON) -m pip install -r $(OL_ROOT)/requirements.txt

prep-venv-force-MSYS:
	pacman -Syuu
	pacman --needed --noconfirm -S \
	base-devel git wget sed diffutils grep tar unzip \
	${MINGW_PACKAGE_PREFIX}-toolchain \
	${MINGW_PACKAGE_PREFIX}-pkgconf \
	${MINGW_PACKAGE_PREFIX}-cmake \
	${MINGW_PACKAGE_PREFIX}-ninja \
	${MINGW_PACKAGE_PREFIX}-yasm \
	${MINGW_PACKAGE_PREFIX}-freeglut \
	${MINGW_PACKAGE_PREFIX}-ffmpeg \
	${MINGW_PACKAGE_PREFIX}-ncurses \
	${MINGW_PACKAGE_PREFIX}-qt5 \
	${MINGW_PACKAGE_PREFIX}-fdk-aac \
	${MINGW_PACKAGE_PREFIX}-libmodplug \
	${MINGW_PACKAGE_PREFIX}-cython \
	${MINGW_PACKAGE_PREFIX}-python3 \
	${MINGW_PACKAGE_PREFIX}-python \
	${MINGW_PACKAGE_PREFIX}-python-pip \
	${MINGW_PACKAGE_PREFIX}-python-wheel \
	${MINGW_PACKAGE_PREFIX}-python-build \
	${MINGW_PACKAGE_PREFIX}-python-cffi \
	${MINGW_PACKAGE_PREFIX}-python-av \
	${MINGW_PACKAGE_PREFIX}-python-pillow \
	${MINGW_PACKAGE_PREFIX}-python-numpy \
	${MINGW_PACKAGE_PREFIX}-python-click \
	${MINGW_PACKAGE_PREFIX}-python-opencv \
	${MINGW_PACKAGE_PREFIX}-python-qtpy \
	${MINGW_PACKAGE_PREFIX}-python-pyqt5 \
	${MINGW_PACKAGE_PREFIX}-python-ffmpeg-python \
	$(MINGW_PACKAGE_PREFIX)-jack2
	$(RM) -r $(OL_VENV_DIR)
	$(BASE_PYTHON) -m venv  --system-site-packages $(OL_VENV_DIR)
	$(VENV_PYTHON) -m pip install --no-input jaconv yt-dlp tinydb cv2-enumerate-cameras

prep-venv-force-Linux:
	sudo apt-get update
	sudo apt-get install -y \
		build-essential \
		python3 \
		python3-dev \
		cython3 \
		libjack-jackd2-dev \
		libavcodec-dev \
		libavutil-dev \
		libswresample-dev \
		libavformat-dev \
		libswscale-dev \
		libavdevice-dev \
		freeglut3-dev \
		libopenmpt-modplug-dev \
		qtbase5-dev
	sudo apt-get install -y \
		python3-dev \
		python3-setuptools \
		python3-build \
		cython3 \
		python3-click \
		python3-tinydb \
		python3-av \
		python3-pil \
		python3-numpy \
		python3-click \
		python3-opencv \
		python3-qtpy \
		python3-pyqt5 \
		python3-jack-client \
		yt-dlp
	$(RM) -r $(OL_VENV_DIR)
	$(BASE_PYTHON) -m venv --system-site-packages $(OL_VENV_DIR)
	$(VENV_PYTHON) -m pip install build jaconv yt-dlp tinydb cv2-enumerate-cameras ffmpeg-python

build-generator: $(OL_BUILD_DIR)/.generator.done
$(OL_BUILD_DIR)/.generator.done:
	$(MAKE) build-generator-force
	@$(TOUCH) $@

build-generator-force: | prep
	$(RM) -r $(OL_BUILD_DIR)
	cmake -S $(OL_ROOT) -B "$(OL_BUILD_DIR)" \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_SHARED_LIBS=On \
		-DPython3_EXECUTABLE="$(abspath $(VENV_PYTHON))" \
		-DCMAKE_TOOLCHAIN_FILE="$(CMAKE_TOOLCHAIN_FILE)" \

#		--debug-trycompile

build: build-generator
	cmake --build $(OL_BUILD_DIR) --config Release

dist: build
	cd $(OL_BUILD_DIR) && cpack

.PHONY: build dist
