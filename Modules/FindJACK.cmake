# - Try to find JACK
# This will define the following variables:
#
#  JACK_FOUND - system has JACK
#  JACK_INCLUDE_DIRS - the JACK include directories
#  JACK_LIBRARIES - link these to use JACK
#
# User variables:
#
#  JACK_NO_PROGRAM_FILES - Ignore windows program files folder
#  JACK_PROGRAM_FILES_DIR - Default is "c:/Program Files/JACK2"

include(FindPackageHandleStandardArgs)
find_package(PkgConfig)

if (WIN32 AND CMAKE_SIZEOF_VOID_P EQUAL 8)
  set(_JACK_NAME jack64)
else()
  set(_JACK_NAME jack)
endif()

# Find jack for windows installer version

if (MSVC AND NOT JACK_NO_PROGRAM_FILES)
  if (NOT JACK_PROGRAM_FILES_DIR)
    set(JACK_PROGRAM_FILES_DIR "c:/Program Files/JACK2")
  endif ()

  file(TO_CMAKE_PATH "${JACK_PROGRAM_FILES_DIR}" JACK_PROGRAM_FILES_DIR)

  if (NOT EXISTS ${JACK_PROGRAM_FILES_DIR})
    message(STATUS "warning: Can not find directory ${JACK_PROGRAM_FILES_DIR}")
    message(STATUS "  Please set JACK_PROGRAM_FILES_DIR.")
  else()
    if (EXISTS "${JACK_PROGRAM_FILES_DIR}/include/jack/jack.h")
      set(JACK_INC "${JACK_PROGRAM_FILES_DIR}/include")
    endif()
    set(JACK_LIB "${JACK_PROGRAM_FILES_DIR}/lib/lib${_JACK_NAME}.lib")
    file(TO_CMAKE_PATH "$ENV{windir}/lib${_JACK_NAME}.dll" JACK_DLL)
    if (NOT EXISTS "${JACK_LIB}")
      unset(JACK_LIB)
    endif()
    if (NOT EXISTS "${JACK_DLL}")
      unset(JACK_DLL)
    endif()

    if (JACK_INC OR JACK_LIB OR JACK_DLL)
      if (JACK_INC AND JACK_LIB AND JACK_DLL)
	set(JACK_FOUND 1)
	set(JACK_INCLUDE_DIR ${JACK_INC})
	set(JACK_LIBRARY ${JACK_LIB})
	set(JACK_LIBRARIES ${JACK_LIB})
	set(JACK_LIBRARY_DLL ${JACK_DLL})
	set(_JACK_EXTRA_INFO "Windows package version")
      else()
	message(STATUS "Jack is not installed correctly.")
	message(STATUS " - INCLUDE : ${JACK_INC}")
	message(STATUS " - LIBRARY : ${JACK_LIB}")
	message(STATUS " - DLL     : ${JACK_DLL}")
      endif()
    endif()
  endif()
endif()

# Find by pkgconfig

if (NOT JACK_FOUND AND NOT MSVC)
  if (MSVC AND VCPKG_TOOLCHAIN)
    message("warning: You are trying to find jack with VCPKG. recomended way is install jack with windows installation")
  endif()

  pkg_check_modules(PC_JACK jack)
  if(PC_JACK_FOUND)
    set(JACK_FOUND YES)
    set(JACK_VERSION ${PC_JACK_VERSION})
    set(_JACK_EXTRA_INFO "version ${PC_JACK_VERSION}")
    find_path(JACK_INCLUDE_DIR jack/jack.h HINTS ${PC_JACK_INCLUDEDIR})
    find_library(JACK_LIBRARY NAMES ${_JACK_NAME} jack HINTS ${PC_JACK_LIBDIR})
  endif()
endif()

if (JACK_FOUND)
  set(JACK_INCLUDE_DIRS ${JACK_INCLUDE_DIR})
  set(JACK_LIBRARIES ${JACK_LIBRARY})

  find_package_handle_standard_args(JACK "Could not find jack; available at jackaudio.org" JACK_INCLUDE_DIR JACK_LIBRARY)

  if (NOT JACK_FOUND_SHOWED)
    set(JACK_FOUND_SHOWED)
    message(STATUS "  - ${JACK_LIBRARIES} ${_JACK_EXTRA_INFO}")
  endif()

  if(JACK_FOUND)
    set(JACK_INCLUDE_DIRS ${JACK_INCLUDE_DIR})

    if(NOT JACK_LIBRARIES)
      set(JACK_LIBRARIES ${JACK_LIBRARY})
    endif()

    if(NOT TARGET Jack::Jack)
      add_library(Jack::Jack UNKNOWN IMPORTED)

      set_target_properties(Jack::Jack PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${JACK_INCLUDE_DIRS}")

      if(JACK_LIBRARY_RELEASE)
        set_property(TARGET Jack::Jack APPEND PROPERTY
          IMPORTED_CONFIGURATIONS RELEASE)
        set_target_properties(Jack::Jack PROPERTIES
          IMPORTED_LOCATION_RELEASE "${JACK_LIBRARY_RELEASE}")
      endif()

      if(JACK_LIBRARY_DEBUG)
        set_property(TARGET Jack::Jack APPEND PROPERTY
          IMPORTED_CONFIGURATIONS DEBUG)
        set_target_properties(Jack::Jack PROPERTIES
          IMPORTED_LOCATION_DEBUG "${JACK_LIBRARY_DEBUG}")
      endif()

      if(NOT JACK_LIBRARY_RELEASE AND NOT JACK_LIBRARY_DEBUG)
        set_property(TARGET Jack::Jack APPEND PROPERTY
          IMPORTED_LOCATION "${JACK_LIBRARY}")
      endif()

    endif()
  endif()
else()
  if (JACK_FIND_REQUIRED)
    message(FATAL_ERROR "Jack not found; available at jackaudio.org")
  endif()
endif()
