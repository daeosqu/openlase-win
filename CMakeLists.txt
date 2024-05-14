#         OpenLase - a realtime laser graphics toolkit
#
# Copyright (C) 2009-2011 Hector Martin "marcan" <hector@marcansoft.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 or version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#

cmake_minimum_required(VERSION 3.12)

include(FindPackageHandleStandardArgs)

project(openlase)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/Modules/")

include(CheckSymbolExists)

if (UNIX)
  if(CMAKE_HOST_SYSTEM_VERSION MATCHES "microsoft-standard-WSL2$")
    set(wsl 2)
  elseif(CMAKE_HOST_SYSTEM_VERSION MATCHES "-Microsoft$")
    set(wsl 1)
  elseif(NOT HAVE_SYS_UTSNAME)
    set(wsl -1)
  else()
    set(wsl 0)
  endif()
else()
  set(wsl 0)
endif()

# Set compiler options

include_directories("common")
add_definitions(-DNOMINMAX)
add_definitions(-D_USE_MATH_DEFINES)

if(MSVC)
  set(CMAKE_C_FLAGS "/W1")
  set(CMAKE_C_FLAGS_RELEASE "/MD /Ox /DNDEBUG")
  set(CMAKE_CXX_FLAGS_RELEASE ${CMAKE_C_FLAGS_RELEASE})
  set(CMAKE_CXX_FLAGS_RELEASE ${CMAKE_CXX_FLAGS_RELEASE})
  set(CMAKE_EXE_LINKER_FLAGS "/DYNAMICBASE:NO")
  add_definitions(-DFREEGLUT_LIB_PRAGMAS=0)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
  set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
  set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
  set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
  set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
else()
  set(CMAKE_C_FLAGS_RELEASE "-O3")
  set(CMAKE_CXX_FLAGS_RELEASE "-O3")
  add_compile_options (-fdiagnostics-color=always)
endif()

# Set default install prefix

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  if(NOT MSVC)
    set(_DEFAULT_PREFIX)
    if(MINGW AND ENV{MINGW_PREFIX})
      set(_DEFAULT_PREFIX $ENV{MINGW_PREFIX}/local/openlase)
    else()
      set(_DEFAULT_PREFIX /usr/local/openlase)
    endif()
    if(_DEFAULT_PREFIX)
      set(CMAKE_INSTALL_PREFIX ${_DEFAULT_PREFIX} CACHE PATH "Install path prefix, prepended onto install directories." FORCE)
      message(STATUS "CMAKE_INSTALL_PREFIX is ${CMAKE_INSTALL_PREFIX}")
    endif()
    unset(_DEFAULT_PREFIX)
  endif()
endif()

# Find Thread library

if(MSVC)
    find_package(PTHREADS)
    set(THREADS_FOUND ${PThreads4W_FOUND})
    set(THREADS_INCLUDE_DIR ${PThreads4W_INCLUDE_DIR})
    set(THREADS_LIBRARY ${PThreads4W_LIBRARY})
    set(THREADS_LIBRARY_RELEASE_DLL ${PThreads4W_LIBRARY_RELEASE_DLL})
    set(THREADS_LIBRARY_DEBUG_DLL ${PThreads4W_LIBRARY_DEBUG_DLL})
    find_package_handle_standard_args(THREADS "Could not find PThreads4W" THREADS_LIBRARY THREADS_INCLUDE_DIR THREADS_LIBRARY_RELEASE_DLL THREADS_LIBRARY_DEBUG_DLL)
else()
  find_package(Threads)
endif()

# Find Libraries

find_package(JACK)
set(Python3_FIND_REGISTRY NEVER)
find_package(Python3 COMPONENTS Interpreter Development)
find_package(Qt5Widgets)
find_package(FFmpeg COMPONENTS AVCODEC AVFORMAT AVDEVICE AVUTIL SWSCALE SWRESAMPLE)
find_package(OpenGL)
find_package(GLUT)
find_package(ALSA)

# Curses

if(MSVC)
  find_path(CURSES_INCLUDE_DIR NAMES curses.h)
  find_library(CURSES_LIBRARY pdcurses)
  find_package_handle_standard_args(CURSES "Could not find pdcurses; please install pdcurses with vcpkg" CURSES_LIBRARY CURSES_INCLUDE_DIR)
else()
  find_package(Curses)
  if(MINGW)
    find_path(_NCURSES_INCLUDE_DIR curses.h
        HINTS ${CURSES_INCLUDE_DIR}/ncurses NO_DEFAULT_PATH)
    if(_NCURSES_INCLUDE_DIR)
        add_compile_options(-DNCURSES_STATIC)
        set(CURSES_INCLUDE_DIR ${_NCURSES_INCLUDE_DIR})
    endif()
  endif()
endif()

# ModPlug

if(MSVC)
    find_path(MODPLUG_INCLUDE_DIRS NAMES modplug.h PATH_SUFFIXES libmodplug)
    find_library(MODPLUG_LIBRARIES modplug)
    find_package_handle_standard_args(MODPLUG "Could not find libmodplug; please install libmodplug with vcpkg" MODPLUG_LIBRARIES MODPLUG_INCLUDE_DIRS)
else()
    find_package(PkgConfig)
    pkg_check_modules(MODPLUG libmodplug)
    if(MODPLUG_FOUND)
      set(MODPLUG_INCLUDE_DIRS ${MODPLUG_INCLUDEDIR}/libmodplug)
      set(MODPLUG_LIBRARY_DIRS ${MODPLUG_LIBDIR})
    endif()
    find_package_handle_standard_args(MODPLUG "Could not find libmodplug; please install libmodplug" MODPLUG_INCLUDE_DIRS MODPLUG_LIBRARY_DIRS MODPLUG_LIBRARIES)
    set(MATH_LIBRARY "m")
endif()

# GetOpt

if(MSVC)
    find_path(GETOPT_INCLUDE_DIR NAMES getopt.h)
    find_library(GETOPT_LIBRARY getopt)
    find_package_handle_standard_args(GETOPT "Could not find getopt; please install getopt with vcpkg" GETOPT_LIBRARY GETOPT_INCLUDE_DIR)
endif()

# Unbuffered STDIO library for MinGW

if(MINGW)
  add_library(unbuffered STATIC common/mingw_unbuffered.c)
  set(COMMON_LIBRARIES unbuffered)
endif()

if(NOT DEFINED BUILD_TRACER)
  set(BUILD_TRACER "Y" CACHE BOOL "Build the image tracer (x86 only)" FORCE)
endif()

# Add subdirectory

add_subdirectory (include)
add_subdirectory (libol)
add_subdirectory (output)
add_subdirectory (tools)
add_subdirectory (python)
add_subdirectory (examples)

# Jack Over PulseAudio for WSL

if (wsl)
  include(ExternalProject)

  set(jopa_DESTDIR ${CMAKE_CURRENT_BINARY_DIR}/jopa_install)

  ExternalProject_Add(jopa
    GIT_REPOSITORY https://github.com/m13253/jack-over-pulseaudio.git
    GIT_TAG master  # 5d0514b
    BUILD_IN_SOURCE TRUE
    CONFIGURE_COMMAND ""
    BUILD_COMMAND make
    UPDATE_COMMAND ""
    INSTALL_DIR ${CMAKE_CURRENT_BINARY_DIR}/install
    INSTALL_COMMAND make DESTDIR=${jopa_DESTDIR} install
  )
  install(
    DIRECTORY ${jopa_DESTDIR}/
    DESTINATION "/"
    USE_SOURCE_PERMISSIONS
  )
endif()

# Install

install(FILES ${CMAKE_CURRENT_LIST_DIR}/test_patterns/ILDA12K.ild DESTINATION ${CMAKE_INSTALL_PREFIX}/test_patterns)
install(FILES openlase.cmd DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
install(FILES openlase.sh DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
install(DIRECTORY scripts DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
install(DIRECTORY config DESTINATION ${CMAKE_INSTALL_PREFIX})
install(FILES res/laser.ico DESTINATION ${CMAKE_INSTALL_PREFIX}/res)

if (MSVC)

  # Install DLLs

  install(
    CODE "file(GLOB_RECURSE ALL_RUNTIME_DLL \"${CMAKE_CURRENT_BINARY_DIR}/*.dll\")"
    CODE "file(INSTALL \${ALL_RUNTIME_DLL} DESTINATION \"${CMAKE_INSTALL_PREFIX}/bin\")")

  # Install start menu shortcut

  set (cs_cmd powershell.exe)

  # Install openlase terminal command
  install(FILES openlase.cmd DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
  set (cs_arg "../scripts/win/create-shortcut.ps1 'openlase.lnk' '\"${CMAKE_INSTALL_PREFIX}/bin/openlase.cmd\"' '${CMAKE_INSTALL_PREFIX}/res/laser.ico' '${CMAKE_INSTALL_PREFIX}/bin'")
  install(CODE "execute_process(COMMAND ${cs_cmd} ${cs_arg})")

  # Install openlase-dev terminal command
  file(READ openlase-dev.cmd.in FILE_CONTENTS)
  string(REPLACE "__OL_SOURCE_DIR__" "${CMAKE_SOURCE_DIR}" FILE_CONTENTS "${FILE_CONTENTS}")
  file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/openlase-dev.cmd" ${FILE_CONTENTS})
  install(FILES "${CMAKE_CURRENT_BINARY_DIR}/openlase-dev.cmd" DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)

  set (cs_arg "../scripts/win/create-shortcut.ps1 'openlase-dev.lnk' '\"${CMAKE_INSTALL_PREFIX}/bin/openlase-dev.cmd\"' '${CMAKE_INSTALL_PREFIX}/res/laser.ico' '${CMAKE_INSTALL_PREFIX}/bin'")
  install(CODE "execute_process(COMMAND ${cs_cmd} ${cs_arg})")

  install(FILES tools/oldownload.ps1 DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
  install(FILES tools/oldownload.py DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
else()
  install(FILES tools/oldownload DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
endif()
