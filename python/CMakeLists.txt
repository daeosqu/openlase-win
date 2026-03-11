cmake_minimum_required(VERSION 3.15)

# ============================================================
# Python bindings (pylase)
# ============================================================

set(Python3_FIND_STRATEGY LOCATION)
find_package(Python3 COMPONENTS Interpreter REQUIRED)

# Directory where ol.dll are located for build wheel
set(LIBOL_LIBRARY_DIR "$<TARGET_FILE_DIR:OpenLase::LibOL>")

# ------------------------------------------------------------
# Locate config.pxi.in (adjust this if your repo layout differs)
# ------------------------------------------------------------
# Expected layout (recommended):
#   <repo>/python/CMakeLists.txt          (this file)
#   <repo>/python/pylase/config.pxi.in
set(_config_in "${CMAKE_CURRENT_SOURCE_DIR}/pylase/config.pxi.in")

if(NOT EXISTS "${_config_in}")
  message(FATAL_ERROR
    "config.pxi.in not found: ${_config_in}\n"
    "Fix _config_in to match your repo layout."
  )
endif()

if(NOT Python3_FOUND OR NOT Python3_LIBRARIES)

  message(STATUS "Will NOT build python3 bindings (python or python libraries missing)")

else()

  # Generate config.pxi for Cython include ("include \"config.pxi\"")
  configure_file(
    "${_config_in}"
    "${CMAKE_CURRENT_BINARY_DIR}/config.pxi"
    @ONLY
  )

  # ------------------------------------------------------------
  # Build extension (.pyd) via setup.py for development (no wheel)
  #
  # Purpose:
  #   Build the Cython extension module directly into the build tree
  #   so that Python code can be executed from the source/build
  #   directory without installing a wheel.
  # ------------------------------------------------------------
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" -c "import Cython"
    RESULT_VARIABLE PYLASE_CYTHON_IMPORT_RESULT
    OUTPUT_QUIET
    ERROR_QUIET
  )

  if(NOT PYLASE_CYTHON_IMPORT_RESULT EQUAL 0)
    message(FATAL_ERROR
      "Cython is required, but it was not found in ${Python3_EXECUTABLE}. "
      "Install it with: ${Python3_EXECUTABLE} -m pip install Cython"
    )
  endif()

  add_custom_target(pylase_pyd ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}"
    COMMAND ${CMAKE_COMMAND} -E env
    "PYLASE_VERSION=${OPENLASE_VERSION}"
    "LIBOL_DLL=$<TARGET_FILE:OpenLase::LibOL>"
    "OPENLASE_BUILD_DIR=${CMAKE_BINARY_DIR}"
    "OPENLASE_SOURCE_DIR=${CMAKE_SOURCE_DIR}"
    ${Python3_EXECUTABLE} setup.py
    build_ext
    --build-lib "${CMAKE_CURRENT_BINARY_DIR}"
    --build-temp "${CMAKE_CURRENT_BINARY_DIR}/_setuptools/temp"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Building pylase extension via setup.py"
  )

  # Ensure OpenLase core library is built first (setup.py links against it)
  # Note: OpenLase::LibOL must be defined by the parent CMake project.
  add_dependencies(pylase_pyd OpenLase::LibOL)

  # ------------------------------------------------------------
  # Build wheel (.whl) via python -m build
  # ------------------------------------------------------------
  add_custom_target(pylase_wheel ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}"
    COMMAND ${CMAKE_COMMAND} -E env
    "PYLASE_VERSION=${OPENLASE_VERSION}"
    "LIBOL_DLL=$<TARGET_FILE:OpenLase::LibOL>"
    "OPENLASE_BUILD_DIR=${CMAKE_BINARY_DIR}"
    "OPENLASE_SOURCE_DIR=${CMAKE_SOURCE_DIR}"
    ${Python3_EXECUTABLE} -m build --wheel --outdir "${CMAKE_BINARY_DIR}/dist"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Building pylase extension via setup.py"
  )

  # avoid parallel build issues
  add_dependencies(pylase_wheel pylase_pyd)

  # ------------------------------------------------------------
  # Install helpers
  # ------------------------------------------------------------
  install(FILES svg.py DESTINATION bin COMPONENT Applications)

endif()
