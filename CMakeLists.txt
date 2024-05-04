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

set(Python3_FIND_REGISTRY NEVER)  # Dont find anaconda in registry
set(Python2_FIND_REGISTRY NEVER)  # Dont find anaconda in registry

cmake_minimum_required(VERSION 3.12)

# vcpkg

# if(CMAKE_GENERATOR MATCHES "^Visual Studio")
#   if(NOT DEFINED VCPKG_ROOT)
#     if (DEFINED ENV{VCPKG_ROOT})
#       set(VCPKG_ROOT $ENV{VCPKG_ROOT})
#     else()
#       #set(VCPKG_ROOT "C:/vcpkg")
#       set(VCPKG_ROOT "$ENV{USERPROFILE}/scoop/apps/vcpkg/current")
#     endif()
#   endif()
#   if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
#     set(CMAKE_TOOLCHAIN_FILE "${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
#         CACHE STRING "")
#   endif()
# endif()

# project

project(openlase)

include(CheckSymbolExists)

if(CMAKE_C_FLAGS STREQUAL "")
    set(CMAKE_C_FLAGS "-O3 -g")
endif()

if(MSVC)
    set(CMAKE_EXE_LINKER_FLAGS "/DYNAMICBASE:NO")
    add_definitions(-DFREEGLUT_LIB_PRAGMAS=0)
endif()

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

if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(BITS 64)
else()
    set(BITS 32)
endif()

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/Modules/")

if(CYGWIN)
    # add .lib for find libjack64.lib (FindJack.cmake)
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".dll.a" ".a" ".lib")
endif()

# Thrads

if(MSVC)
    include(FindPackageHandleStandardArgs)

    # private pthreads4w build directory (not a vcpkg)
    #set(PThreads4W_DIR ${CMAKE_CURRENT_LIST_DIR}/3rdparty/pthreads4w)

    if(EXISTS "${PThreads4W_DIR}")
        # see c:/vcpkg/installed/x64-windows/share/pthread/vcpkg-cmake-wrapper.cmake

        include(SelectLibraryConfigurations)

        set(PThreads4W_INC_DIR ${PThreads4W_DIR})
        set(PThreads4W_LIB_DIR ${PThreads4W_DIR})
        set(PThreads4W_DLL_DIR ${PThreads4W_DIR})

        find_path(PThreads4W_INCLUDE_DIR NAMES pthread.h
            HINTS ${PThreads4W_INC_DIR} NO_DEFAULT_PATH)
        find_library(PThreads4W_LIBRARY_RELEASE NAMES pthreadVC3
            HINTS ${PThreads4W_LIB_DIR} NO_DEFAULT_PATH)
        find_library(PThreads4W_LIBRARY_DEBUG NAMES pthreadVC3d
            HINTS ${PThreads4W_LIB_DIR} NO_DEFAULT_PATH)

        select_library_configurations(PThreads4W)
        find_package_handle_standard_args(PThreads4W "Could not find pthreads; please build pthreads4w in 3rdparty/pthreads4w" PThreads4W_LIBRARY PThreads4W_INCLUDE_DIR)
        mark_as_advanced(PThreads4W_INCLUDE_DIR PThreads4W_LIBRARY)

        find_file(PThreads4W_LIBRARY_RELEASE_DLL NAMES pthreadVC3.dll PATHS ${PThreads4W_DLL_DIR})
        find_file(PThreads4W_LIBRARY_DEBUG_DLL NAMES pthreadVC3d.dll PATHS ${PThreads4W_DLL_DIR})
    else()
        find_package(PTHREADS)
        if(NOT PThreads4W_FOUND)
            message("Could not find PThreads4W; please install pthreads with vcpkg or build it manually in ${PThreads4W_DIR}.")
        endif()
    endif()
    set(THREADS_FOUND ${PThreads4W_FOUND})
    if(THREADS_FOUND)
        set(THREADS_INCLUDE_DIR ${PThreads4W_INCLUDE_DIR})
        set(THREADS_LIBRARY ${PThreads4W_LIBRARY})
        set(THREADS_LIBRARY_RELEASE_DLL ${PThreads4W_LIBRARY_RELEASE_DLL})
        set(THREADS_LIBRARY_DEBUG_DLL ${PThreads4W_LIBRARY_DEBUG_DLL})
        message(STATUS "Found pthread library for windows")
        message("THREADS_INCLUDE_DIR         : ${THREADS_INCLUDE_DIR}")
        message("THREADS_LIBRARY             : ${THREADS_LIBRARY}")
        message("THREADS_LIBRARY_RELEASE_DLL : ${THREADS_LIBRARY_RELEASE_DLL}")
        message("THREADS_LIBRARY_DEBUG_DLL   : ${THREADS_LIBRARY_DEBUG_DLL}")
    else()
        message("Could not find pthread library for windows")
    endif()
else()
  find_package(Threads)
endif()

# JACK

find_package(JACK)

# Python

find_package(Python3 COMPONENTS Interpreter Development)
find_package(Python2 COMPONENTS Interpreter Development)
find_package(Python REQUIRED COMPONENTS Interpreter)

foreach(_pkg Python2 Python3)
  if(NOT ${_pkg}_FOUND)
    message(STATUS "Please check ${_pkg} enironment")
    foreach(_key ROOT_DIR EXECUTABLE INCLUDE_DIR LIBRARY)
      message("  ${_pkg}_${_key} is ${${_pkg}_${_key}}")
    endforeach()
  endif()
endforeach()

# Qt

if(MSVC)
    if(NOT DEFINED QTDIR)
        if(DEFINED ENV{QTDIR})
            set(QTDIR $ENV{QTDIR})
        else()
            # https://stackoverflow.com/questions/15639781/how-to-find-the-qt5-cmake-module-on-windows
            GET_FILENAME_COMPONENT(QT_BIN [HKEY_CURRENT_USER\\Software\\Classes\\Applications\\QtProject.QtCreator.cpp\\shell\\Open\\Command] PATH)
            STRING(REPLACE "/Tools" ";" QT_BIN "${QT_BIN}")
            LIST(GET QT_BIN 0 QT_BIN)
            FILE(GLOB QT_VERSIONS "${QT_BIN}/5.*")
            LIST(SORT QT_VERSIONS)
            LIST(REVERSE QT_VERSIONS)
            LIST(GET QT_VERSIONS 0 QT_VERSION)
            STRING(REPLACE "//" "/"  QT_VERSION "${QT_VERSION}")
            IF(MSVC_VERSION LESS 1900)
                SET(QT_MSVC 2013)
            ELSEIF(MSVC_VERSION LESS 1910)
                SET(QT_MSVC 2015)
            ELSEIF(MSVC_VERSION LESS 1920)
                SET(QT_MSVC 2017)
            ELSE()
                SET(QT_MSVC 2019)
            ENDIF()
            IF(CMAKE_SIZEOF_VOID_P EQUAL 8)
                SET(QT_MSVC "${QT_MSVC}_64")
            ENDIF()
            SET(QTDIR_GUESS "${QT_VERSION}/msvc${QT_MSVC}")
            find_path(QTDIR bin/qmake.exe PATHS ${QTDIR_GUESS} NO_DEFAULT_PATH)
            message(STATUS "Found Qt5 Directory: ${QTDIR}")
        endif()
    endif()
    set(CMAKE_PREFIX_PATH ${QTDIR} ${CMAKE_PREFIX_PATH})
endif()

find_package(Qt5Widgets)
if(Qt5Widgets_FOUND)
	message(STATUS "Found Qt5: ${Qt5Widgets_PRIVATE_INCLUDE_DIRS}")
endif()

# FFmpeg

find_package(FFmpeg COMPONENTS AVCODEC AVFORMAT AVDEVICE AVUTIL SWSCALE SWRESAMPLE)
if(FFMPEG_LIBRARIES AND FFMPEG_INCLUDE_DIRS)
  set(FFMPEG_FOUND TRUE)
endif()

# OpenGL / GLUT / ALSA

find_package(OpenGL)
if(OPENGL_FOUND)
	message(STATUS "OpenGL (Win32): ${OPENGL_LIBRARY} ${OPENGL_INCLUDE_DIR}")
endif()

# GLUT
if(MSVC)
  find_path(FreeGLUT_INCLUDE_DIR NAMES GL/freeglut.h)
  find_library(FreeGLUT_LIBRARY freeglut)
	find_package_handle_standard_args(FreeGLUT REQUIRED_VARS FreeGLUT_INCLUDE_DIR FreeGLUT_LIBRARY)
	set(GLUT_INCLUDE_DIR ${FreeGLUT_INCLUDE_DIR})
	set(GLUT_LIBRARY ${FreeGLUT_LIBRARY})
	find_package_handle_standard_args(GLUT REQUIRED_VARS GLUT_INCLUDE_DIR GLUT_LIBRARY)
else()
	find_package(GLUT)
endif()

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
        set(CURSES_INCLUDE_DIR ${_NCURSES_INCLUDE_DIR})
    endif()
  endif()
endif()

# modplug

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

# getopt (MSVC)

if(MSVC)
    find_path(GETOPT_INCLUDE_DIR NAMES getopt.h)
    find_library(GETOPT_LIBRARY getopt)
    find_package_handle_standard_args(GETOPT "Could not find getopt; please install getopt with vcpkg" GETOPT_LIBRARY GETOPT_INCLUDE_DIR)
endif()

# unbuffered

if(MINGW)
  add_library(unbuffered STATIC common/mingw_unbuffered.c)
  set(COMMON_LIBRARIES unbuffered)
endif()

# Visual Studio

if(MSVC)
    SET( CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
    SET( CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
    SET( CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
    SET( CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
    SET( CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG "${OUTPUT_DIRECTORY}")
    SET( CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${OUTPUT_DIRECTORY}")
endif()

# Compiler options

if (CMAKE_C_FLAGS STREQUAL "")
  if ("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    set(CMAKE_C_FLAGS "-O3 -g")
  endif()
endif()

if(MSVC)
  add_compile_options(/W1)
else()
  add_compile_options(-Wall)
  if("Ninja" STREQUAL ${CMAKE_GENERATOR})
    add_compile_options (-fdiagnostics-color=always)
  endif()
endif()

if(NOT DEFINED BUILD_TRACER)
  set(BUILD_TRACER "Y" CACHE BOOL "Build the image tracer (x86 only)" FORCE)
endif()

include_directories("common")
include_directories(${JACK_INCLUDE_DIR})
if(MSVC)
  add_definitions(-DNOMINMAX)
  add_definitions(-D_USE_MATH_DEFINES)
endif()

add_subdirectory (include)
add_subdirectory (libol)
add_subdirectory (output)
add_subdirectory (tools)
add_subdirectory (python)
add_subdirectory (examples)

# install

if(MSVC)
install(
    CODE "file(GLOB_RECURSE ALL_RUNTIME_DLL \"${CMAKE_CURRENT_BINARY_DIR}/*.dll\")"
    CODE "file(INSTALL \${ALL_RUNTIME_DLL} DESTINATION \"${CMAKE_INSTALL_PREFIX}/bin\")")
endif()

install(FILES ${CMAKE_CURRENT_LIST_DIR}/test_patterns/ILDA12K.ild DESTINATION ${CMAKE_INSTALL_PREFIX}/test_patterns)
