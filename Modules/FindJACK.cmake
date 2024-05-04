# - Try to find JACK
# This will define the following variables:
#
#  JACK_FOUND - system has JACK
#  JACK_INCLUDE_DIRS - the JACK include directories
#  JACK_LIBRARIES - link these to use JACK

include(LibFindMacros)

mark_as_advanced(JACK_LIBRARY JACK_INCLUDE_DIR)

if(JACK_LIBRARY AND JACK_INCLUDE_DIR)

  include(FindPackageHandleStandardArgs)
  find_package_handle_standard_args(JACK REQUIRED_VARS JACK_INCLUDE_DIR JACK_LIBRARY)
  set(JACK_LIBRARIES ${JACK_LIBRARY})
  set(JACK_INCLUDE_DIRS ${JACK_INCLUDE_DIR})

elseif(MSVC OR MINGW OR CYGWIN)

  if (NOT _JACK_root_dir)
      #set(_JACK_root_dir "c:/Program Files (x86)/Jack")
      set(_JACK_root_dir "c:/Program Files/JACK2")
  endif ()

  if (CMAKE_SIZEOF_VOID_P EQUAL 8)
      set(_JACK_LIB_NAME "jack64")
      set(_JACK_LIB_DIR "${_JACK_root_dir}/lib")
  else()
      set(_JACK_LIB_NAME "jack")
      set(_JACK_LIB_DIR "${_JACK_root_dir}/lib32")
  endif()

  if(MSVC)
      set(_JACK_LIB_NAME "lib${_JACK_LIB_NAME}.lib")
  endif()

  FIND_PATH(JACK_INCLUDE_DIR NAMES jack/jack.h
      HINTS
      ${_JACK_root_dir}/includes
      ${_JACK_root_dir}/include
      )

  find_library(JACK_LIBRARY NAMES ${_JACK_LIB_NAME}
      HINTS
      ${_JACK_LIB_DIR}
      NO_DEFAULT_PATH
      NO_CMAKE_FIND_ROOT_PATH
      )

  include(FindPackageHandleStandardArgs)
  find_package_handle_standard_args(JACK DEFAULT_MSG JACK_LIBRARY JACK_INCLUDE_DIR)
  set(JACK_INCLUDE_DIRS ${JACK_INCLUDE_DIR})
  set(JACK_LIBRARIES ${JACK_LIBRARY})

else()

  include(FindPackageHandleStandardArgs)

  find_package(PkgConfig)
  pkg_check_modules(JACK jack)
  set(JACK_DEFINITIONS ${PC_JACK_CFLAGS_OTHER})

  set(_JACK_LIB_NAME jack)
  if((MINGW OR CYGWIN OR MSVC) AND CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(_JACK_LIB_NAME jack64)
  endif()

  if(NOT DEFINED PC_JACK_LIBDIR)
      set(PC_JACK_LIBDIR "C:/Program Files (x86)/Jack/lib")
  endif()
  if(NOT DEFINED PC_JACK_INCLUDEDIR)
      set(PC_JACK_LIBDIR "C:/Program Files (x86)/Jack/includes")
  endif()

  find_library(JACK_LIBRARIES ${_JACK_LIB_NAME}
    HINTS ${PC_JACK_LIBDIR} ${PC_JACK_LIBRARY_DIRS}
  )

  Find_path(JACK_INCLUDE_DIR jack.h
    HINTS ${PC_JACK_INCLUDEDIR} ${PC_JACK_INCLUDE_DIRS}
    PATH_SUFFIXES jack
  )

  find_package_handle_standard_args(JACK "Could not find jack; available at jackaudio.org" JACK_LIBRARIES JACK_INCLUDE_DIR)

  mark_as_advanced(JACK_INCLUDE_DIR JACK_LIBRARIES)

endif()
