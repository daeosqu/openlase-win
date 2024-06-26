################
##  Settings  ##
################

if (NOT DEFINED LibOL_INSTALL_CMAKEDIR)
    set(LibOL_INSTALL_CMAKEDIR "${CMAKE_INSTALL_LIBDIR}/cmake"
        CACHE STRING "Path to LibOL CMake files")
endif ()

###############
##  Install  ##
###############

install(TARGETS ${LIBRARY_TARGET_NAME}
    EXPORT ${LIBRARY_TARGET_NAME}_Targets
    RUNTIME COMPONENT ${LIBOL_COMPONENT_NAME}
    LIBRARY COMPONENT ${LIBOL_COMPONENT_NAME}
    NAMELINK_COMPONENT ${LIBOL_COMPONENT_NAME}
    ARCHIVE COMPONENT ${LIBOL_COMPONENT_NAME}
    PUBLIC_HEADER DESTINATION include/libol COMPONENT ${LIBOL_COMPONENT_NAME}
)

############
##  DLLs  ##
############

install(FILES $<TARGET_RUNTIME_DLLS:${LIBRARY_TARGET_NAME}> TYPE BIN COMPONENT ${LIBRARY_TARGET_NAME} COMPONENT ${LIBOL_COMPONENT_NAME})

##############
##  Export  ##
##############

install(EXPORT ${LIBRARY_TARGET_NAME}_Targets
  FILE ${LIBRARY_NAMESPACE}${LIBRARY_TARGET_NAME}Targets.cmake
  NAMESPACE ${LIBRARY_NAMESPACE}::
  DESTINATION ${LibOL_INSTALL_CMAKEDIR}
  COMPONENT ${LIBOL_COMPONENT_NAME})

export(EXPORT ${LIBRARY_TARGET_NAME}_Targets
  FILE "${CMAKE_CURRENT_BINARY_DIR}/cmake/${LIBRARY_NAMESPACE}${LIBRARY_TARGET_NAME}Targets.cmake"
  NAMESPACE ${LIBRARY_NAMESPACE}::
)
