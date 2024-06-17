#         OpenLase-win - a realtime laser graphics toolkit for windows
#
# Copyright (C) 2024 Daisuke Arai <daisuke.qu@gmail.com>
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

# Install

install(FILES ../openlase.sh DESTINATION bin COMPONENT Applications)
install(FILES ../openlase.cmd DESTINATION bin COMPONENT Applications)
install(DIRECTORY ../scripts DESTINATION bin COMPONENT Applications)
install(FILES
  ../VERSION
  ../res/laser.ico
  ../test_patterns/ILDA12K.ild
  ../config/openlase-laserdock.xml
  ../config/openlase-netjack.xml
  DESTINATION share/openlase COMPONENT Applications)

# Install DLLs

if (MSVC)
  install(
    CODE "message(\"Finding DLLs in ${CMAKE_CURRENT_BINARY_DIR}/../{tools,examples,output}...\")"
    CODE "file(GLOB_RECURSE ALL_RUNTIME_DLL LIST_DIRECTORIES Off
      ${CMAKE_CURRENT_BINARY_DIR}/../tools/*.dll
      ${CMAKE_CURRENT_BINARY_DIR}/../examples/*.dll
      ${CMAKE_CURRENT_BINARY_DIR}/../output/*.dll
    )"
    CODE "list(FILTER ALL_RUNTIME_DLL EXCLUDE REGEX \"/(_CPack_Packages|vcpkg_installed|imageformats|platforms|styles|qtDeploy)/.*\")"
    CODE "message(\"Copying DLLs into \${CMAKE_INSTALL_PREFIX}/bin...\")"
    CODE "file(INSTALL \${ALL_RUNTIME_DLL} DESTINATION \"\${CMAKE_INSTALL_PREFIX}/bin\")" COMPONENT Applications)
endif()

# Export

write_basic_package_version_file(
  ${PROJECT_NAME}ConfigVersion.cmake
  COMPATIBILITY SameMajorVersion)

configure_package_config_file(${PROJECT_NAME}Config.cmake.in
  "${PROJECT_NAME}Config.cmake"
  INSTALL_DESTINATION "${INSTALL_CMAKEDIR}"
)

install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}Config.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}ConfigVersion.cmake
  DESTINATION ${INSTALL_CMAKEDIR}
  COMPONENT ${LIBOL_COMPONENT_NAME})

# set(CPACK_INSTALL_PREFIX "${CPACK_PACKAGING_INSTALL_PREFIX}")
set(CPACK_PACKAGE_CONTACT "daisuke.qu@gmail.com")
set(CPACK_PACKAGE_VENDOR "OpenLase-win")

if (NOT CPACK_GENERATOR)
  if (MSVC)
    set(CPACK_GENERATOR "ZIP")

    find_program(ISCC_EXECUTABLE iscc.exe)
    if(NOT CPACK_WIX_ROOT)
      string(REPLACE "\\" "/" CPACK_WIX_ROOT "$ENV{WIX}")
    endif()

    find_program(CPACK_WIX_CANDLE_EXECUTABLE candle
      PATHS "${CPACK_WIX_ROOT}" PATH_SUFFIXES "bin")
    find_program(CPACK_WIX_LIGHT_EXECUTABLE light
      PATHS "${CPACK_WIX_ROOT}" PATH_SUFFIXES "bin")
    if (CPACK_WIX_CANDLE_EXECUTABLE AND CPACK_WIX_LIGHT_EXECUTABLE)
      list(APPEND CPACK_GENERATOR "WIX")
      set(CPACK_WIX_VERSION 3)
    else()
      message("Skip WIX package (candle.exe is not installed)")
    endif()

    find_program(CPACK_INNOSETUP_EXECUTABLE iscc)
    if (CPACK_INNOSETUP_EXECUTABLE)
      list(APPEND CPACK_GENERATOR "INNOSETUP")
    else()
      message("Skip INNOSETUP package (iscc.exe is not installed)")
      # find_program(CPACK_NSIS_EXECUTABLE makensis)
      # if (CPACK_NSIS_EXECUTABLE)
      # 	list(APPEND CPACK_GENERATOR "NSIS")
      # else()
      # 	message("Skip INNOSETUP and NSIS package (iscc.exe or makensis.exe is not installed)")
      # endif()
    endif()

  else()
    set(CPACK_GENERATOR "TGZ")
    if (NOT CPACK_PACKAGING_INSTALL_PREFIX)
      set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local/openlase")
    endif()
    find_program(RPM_EXECUTABLE rpm)
    find_program(DPKG_DEB_EXECUTABLE dpkg-deb)
    if (RPM_EXECUTABLE)
      list(APPEND CPACK_GENERATOR "RPM")
    else()
      message("Skip RPM package (rpm is not installed)")
    endif()
    if (DPKG_DEB_EXECUTABLE)
      list(APPEND CPACK_GENERATOR "DEB")
    endif()
  endif()
endif()

set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/../LICENSE.txt")
set(CPACK_PACKAGE_DESCRIPTION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../README.md")
set(CPACK_SOURCE_IGNORE_FILES "${PROJECT_BINARY_DIR};/.git/;.gitignore")
#set(CPACK_PACKAGE_ICON "${CMAKE_CURRENT_SOURCE_DIR}/../res/laser.ico")

set(CPACK_WIX_LIGHT_EXTENSIONS WixUtilExtension)
set(CPACK_WIX_PRODUCT_ICON "${CMAKE_CURRENT_SOURCE_DIR}/../res/laser.ico")
set(CPACK_WIX_UI_BANNER "${CMAKE_CURRENT_SOURCE_DIR}/../res/wix-banner.bmp")
set(CPACK_WIX_UI_DIALOG "${CMAKE_CURRENT_SOURCE_DIR}/../res/wix-ui-dialog.bmp")
set(CPACK_WIX_PATCH_FILE "${CMAKE_CURRENT_SOURCE_DIR}/cpack-wix-patch.xml")

set(CPACK_INNOSETUP_ICON_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../res/laser.ico")

# TODO https://stackoverflow.com/questions/28768417/how-to-set-an-icon-in-nsis-install-cmake
#set(CPACK_NSIS_MUI_ICON "")

set(__cpack_system_name ${CMAKE_SYSTEM_NAME})
if(__cpack_system_name MATCHES "Windows")
  if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(__cpack_system_name win64)
  else()
    set(__cpack_system_name win32)
  endif()
endif()

set(package_file_name "${PROJECT_NAME_LOWER}-${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH}")
set(CPACK_PACKAGE_NAME "${PROJECT_NAME}")
set(CPACK_PACKAGE_FILE_NAME "${package_file_name}-${__cpack_system_name}")
set(CPACK_PACKAGE_INSTALL_DIRECTORY "${package_file_name}")
set(CPACK_PACKAGE_INSTALL_REGISTRY_KEY "${package_file_name}")
#set(CPACK_INSTALL_ROOT "C:")

include(CPack)
