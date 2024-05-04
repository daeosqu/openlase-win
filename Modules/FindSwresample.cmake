# Locate libswresample (part of ffmpeg)
#
#  SWRESAMPLE_FOUND - system has swresample
#  SWRESAMPLE_INCLUDE_DIR - the swresample include directory
#  SWRESAMPLE_LIBRARIES - the libraries needed to use swresample
#  SWRESAMPLE_DEFINITIONS - Compiler switches required for using swresample

# Copyright (c) 2010, Maciej Mrozowski <reavertm@gmail.com>
#
# Redistribution and use is allowed according to the terms of the BSD license.
# For details see the accompanying COPYING-CMAKE-SCRIPTS file.

include(FindPackageHandleStandardArgs)

if(NOT MSVC)
	find_package(PkgConfig)
	pkg_check_modules(PC_SWRESAMPLE libswresample)
	set(SWRESAMPLE_DEFINITIONS ${PC_SWRESAMPLE_CFLAGS_OTHER})
endif()

find_library(SWRESAMPLE_LIBRARIES swresample
    HINTS ${PC_SWRESAMPLE_LIBDIR} ${PC_SWRESAMPLE_LIBRARY_DIRS}
)

find_path(SWRESAMPLE_INCLUDE_DIR swresample.h
    HINTS ${PC_SWRESAMPLE_INCLUDEDIR} ${PC_SWRESAMPLE_INCLUDE_DIRS}
    PATH_SUFFIXES libswresample
)

find_package_handle_standard_args(Swresample "Could not find libswresample; available at www.ffmpeg.org" SWRESAMPLE_LIBRARIES SWRESAMPLE_INCLUDE_DIR)

mark_as_advanced(SWRESAMPLE_INCLUDE_DIR SWRESAMPLE_LIBRARIES)
