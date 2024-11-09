if(NOT Python3_FOUND OR NOT Python3_LIBRARIES)
  message(STATUS "Will NOT build python3 bindings (python or python libraries missing)")
else()
  execute_process(COMMAND ${Python3_EXECUTABLE} -m cython --version RESULT_VARIABLE rv OUTPUT_QUIET ERROR_QUIET)
  if(NOT rv STREQUAL "0")
    message(FATAL_ERROR "Cython not found. please install cython:\n ${Python3_EXECUTABLE} -m pip install cython")
  endif()

  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.pxi.in ${CMAKE_CURRENT_BINARY_DIR}/config.pxi)

  add_custom_command(OUTPUT pylase.c
    MAIN_DEPENDENCY pylase.pyx
    COMMAND ${Python3_EXECUTABLE} -m cython -I ${CMAKE_CURRENT_BINARY_DIR} -o pylase.c "${CMAKE_CURRENT_SOURCE_DIR}/pylase.pyx")
  list(APPEND ADDITIONAL_MAKE_CLEAN_FILES pylase.c)

  add_library(pylase3 MODULE pylase.c)

  if ("x${CMAKE_BUILD_TYPE}x" STREQUAL "xReleasex")
    set(_python_executable "${Python3_EXECUTABLE}")
  else()
    if (${Python3_EXECUTABLE_DEBUG})
      set(_python_executable "${Python3_EXECUTABLE_DEBUG}")
    else()
      string(REGEX REPLACE [[(\.([eE][xX][eE]|[bB][aA][tT]|[cC][mM][dD]|$))]] [[_d\1]] _python_executable "${Python3_EXECUTABLE}")
    endif()
  endif()

  execute_process(COMMAND ${_python_executable} -c "from distutils.sysconfig import get_config_var; print(get_config_var('EXT_SUFFIX'))"
    RESULT_VARIABLE OL_PYTHON3_EXT_SUFFIX_PROCESS
    OUTPUT_VARIABLE OL_PYTHON3_EXT_SUFFIX
    OUTPUT_STRIP_TRAILING_WHITESPACE)

  set_target_properties(pylase3 PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pylase"
    SUFFIX ${OL_PYTHON3_EXT_SUFFIX}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

  target_include_directories(pylase3 PRIVATE ${Python3_INCLUDE_DIRS})
  target_link_directories(pylase3 PRIVATE ${Python3_LIBRARY_DIRS})
  target_link_libraries(pylase3 OpenLase::LibOL ${Python3_LIBRARIES})

  if (MSVC)
    # for development.
    # copy ol.dll and libjack*.dll.
    # for reason, see https://docs.python.org/ja/3/whatsnew/3.8.html#ctypes
    add_custom_command(TARGET pylase3 POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different
      $<TARGET_FILE:OpenLase::LibOL> ${JACK_LIBRARY_DLL}
      ${CMAKE_CURRENT_BINARY_DIR}
      COMMAND_EXPAND_LISTS)
  endif()

  # Do not install to the python site module path
  # install(FILES ${CMAKE_CURRENT_BINARY_DIR}/pylase${OL_PYTHON3_EXT_SUFFIX} DESTINATION ${Python3_SITELIB})

  # Install to bin of the install destination instead
  install(TARGETS pylase3 LIBRARY DESTINATION bin COMPONENT Applications)

  unset(OL_PYTHON3_EXT_SUFFIX_PROCESS)
  unset(OL_PYTHON3_EXT_SUFFIX)

endif()

install(FILES svg.py DESTINATION bin COMPONENT Applications)
