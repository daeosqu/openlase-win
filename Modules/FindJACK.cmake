# - Try to find JACK
# This will define the following variables:
#
#  JACK_FOUND - system has JACK
#  JACK_INCLUDE_DIRS - the JACK include directories
#  JACK_LIBRARIES - link these to use JACK
#  JACK_LIBRARIES_DLL - JACK DLL files (MSVC only)

include(LibFindMacros)

mark_as_advanced(JACK_INCLUDE_DIR JACK_LIBRARIES JACK_LIBRARIES_DLL)

# if(JACK_LIBRARY AND JACK_INCLUDE_DIR)

#   include(FindPackageHandleStandardArgs)
#   find_package_handle_standard_args(JACK REQUIRED_VARS JACK_INCLUDE_DIR JACK_LIBRARY)
#   set(JACK_LIBRARIES ${JACK_LIBRARY})
#   set(JACK_INCLUDE_DIRS ${JACK_INCLUDE_DIR})

#if(MSVC OR MINGW OR CYGWIN)
if(MSVC)

  if (NOT _JACK_root_dir)
      set(_JACK_root_dir "c:/Program Files/JACK2")
  endif ()

  if (CMAKE_SIZEOF_VOID_P EQUAL 8)
      set(_JACK_BASE_NAME "jack64")
      set(_JACK_LIB_DIR "${_JACK_root_dir}/lib")
  else()
      set(_JACK_BASE_NAME "jack")
      set(_JACK_LIB_DIR "${_JACK_root_dir}/lib32")
  endif()

  if(MSVC)
      set(_JACK_DLL_NAME "lib${_JACK_BASE_NAME}.dll")
      set(_JACK_LIB_NAME "lib${_JACK_BASE_NAME}.lib")
  endif()

  find_path(JACK_INCLUDE_DIR NAMES jack/jack.h
      HINTS
      ${_JACK_root_dir}/includes
      ${_JACK_root_dir}/include
      )

  find_library(JACK_LIBRARY NAMES ${_JACK_LIB_NAME}
      HINTS ${_JACK_LIB_DIR}
      NO_DEFAULT_PATH
      NO_CMAKE_FIND_ROOT_PATH
      )

  find_file(JACK_LIBRARY_DLL NAMES ${_JACK_DLL_NAME}
      HINTS $ENV{windir}
      NO_DEFAULT_PATH
      NO_CMAKE_FIND_ROOT_PATH
      )

  set(JACK_LIBRARIES ${JACK_LIBRARY})
  set(JACK_LIBRARIES_DLL ${JACK_LIBRARY_DLL})

  include(FindPackageHandleStandardArgs)
  find_package_handle_standard_args(JACK DEFAULT_MSG JACK_LIBRARIES JACK_LIBRARIES_DLL JACK_INCLUDE_DIR)

else()

  include(FindPackageHandleStandardArgs)

  find_package(PkgConfig)
  pkg_check_modules(JACK jack)
  set(JACK_DEFINITIONS ${PC_JACK_CFLAGS_OTHER})

  find_library(JACK_LIBRARIES jack
    HINTS ${PC_JACK_LIBDIR} ${PC_JACK_LIBRARY_DIRS}
  )

  find_path(JACK_INCLUDE_DIR jack.h
    HINTS ${PC_JACK_INCLUDEDIR} ${PC_JACK_INCLUDE_DIRS}
    PATH_SUFFIXES jack
  )

  find_package_handle_standard_args(JACK "Could not find jack; available at jackaudio.org" JACK_LIBRARIES JACK_INCLUDE_DIR)

endif()
