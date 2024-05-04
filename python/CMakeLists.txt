find_program(CYTHON_EXECUTABLE cython)

if(NOT Python3_FOUND OR NOT Python3_LIBRARIES OR NOT CYTHON_EXECUTABLE)
  message(STATUS "Will NOT build python3 bindings (python libs or cython missing)")
else()
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.pxi.in ${CMAKE_CURRENT_BINARY_DIR}/config.pxi)

  add_custom_command(OUTPUT pylase.c
    MAIN_DEPENDENCY pylase.pyx
    COMMAND ${CYTHON_EXECUTABLE} -I ${CMAKE_SOURCE_DIR}/include -I ${CMAKE_CURRENT_BINARY_DIR} -o pylase.c "${CMAKE_CURRENT_SOURCE_DIR}/pylase.pyx")
    list(APPEND ADDITIONAL_MAKE_CLEAN_FILES pylase.c)

  add_library(pylase3 MODULE pylase.c)

  execute_process(COMMAND ${Python3_EXECUTABLE} -c "from distutils.sysconfig import get_config_var; print(get_config_var('EXT_SUFFIX'))"
      RESULT_VARIABLE OL_PYTHON3_EXT_SUFFIX_PROCESS
      OUTPUT_VARIABLE OL_PYTHON3_EXT_SUFFIX
      OUTPUT_STRIP_TRAILING_WHITESPACE)

  if (NOT "x${CMAKE_BUILD_TYPE}x" STREQUAL "xReleasex")
    set(OL_PYTHON3_EXT_SUFFIX "_d${OL_PYTHON3_EXT_SUFFIX}")
  endif()

  set_target_properties(pylase3 PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pylase"
    SUFFIX ${OL_PYTHON3_EXT_SUFFIX}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

  target_include_directories(pylase3 PRIVATE ${Python3_INCLUDE_DIRS} ${CMAKE_SOURCE_DIR}/include)
  target_link_directories(pylase3 PRIVATE ${Python3_LIBRARY_DIRS}) # for anaconda
  target_link_libraries(pylase3 ol ${Python3_LIBRARIES})

#  install(FILES ${CMAKE_CURRENT_BINARY_DIR}/pylase${OL_PYTHON3_EXT_SUFFIX} DESTINATION ${Python3_SITELIB})
  install(TARGETS pylase3 LIBRARY DESTINATION bin)

  unset(OL_PYTHON3_EXT_SUFFIX_PROCESS)
  unset(OL_PYTHON3_EXT_SUFFIX)

endif()

if(NOT Python2_FOUND OR NOT Python2_LIBRARIES OR NOT CYTHON_EXECUTABLE)
  message(STATUS "Will NOT build python2 bindings (python libs or cython missing)")
else()
  configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.pxi.in ${CMAKE_CURRENT_BINARY_DIR}/config.pxi)

  add_custom_command(OUTPUT pylase.c
    MAIN_DEPENDENCY pylase.pyx
    COMMAND ${CYTHON_EXECUTABLE} -I ${CMAKE_SOURCE_DIR}/include -I ${CMAKE_CURRENT_BINARY_DIR} -o pylase.c "${CMAKE_CURRENT_SOURCE_DIR}/pylase.pyx")
    list(APPEND ADDITIONAL_MAKE_CLEAN_FILES pylase.c)

  add_library(pylase2 MODULE pylase.c)

  execute_process(COMMAND ${Python2_EXECUTABLE} -c "from distutils.sysconfig import get_config_var; print(get_config_var('SO'))"
      RESULT_VARIABLE OL_PYTHON2_EXT_SUFFIX_PROCESS
      OUTPUT_VARIABLE OL_PYTHON2_EXT_SUFFIX
      OUTPUT_STRIP_TRAILING_WHITESPACE)

  if (NOT "x${CMAKE_BUILD_TYPE}x" STREQUAL "xReleasex")
    set(OL_PYTHON2_EXT_SUFFIX "_d${OL_PYTHON2_EXT_SUFFIX}")
  endif()

  set_target_properties(pylase2 PROPERTIES
    PREFIX ""
    OUTPUT_NAME "pylase"
    SUFFIX ${OL_PYTHON2_EXT_SUFFIX}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})

  target_include_directories(pylase2 PRIVATE ${Python2_INCLUDE_DIRS} ${CMAKE_SOURCE_DIR}/include)
  target_link_directories(pylase2 PRIVATE ${Python2_LIBRARY_DIRS}) # for anaconda
  target_link_libraries(pylase2 ol ${Python2_LIBRARIES})

#  install(FILES ${CMAKE_CURRENT_BINARY_DIR}/pylase${OL_PYTHON2_EXT_SUFFIX} DESTINATION ${Python2_SITELIB})
  install(TARGETS pylase2 LIBRARY DESTINATION bin)

  unset(OL_PYTHON2_EXT_SUFFIX_PROCESS)
  unset(OL_PYTHON2_EXT_SUFFIX)

endif()

install(FILES svg.py DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
