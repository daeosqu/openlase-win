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

if(Qt5Widgets_FOUND)

  QT5_WRAP_UI(output_UIS_H output_settings.ui)
  QT5_WRAP_CPP(output_MOCS output_settings.h)

  add_executable(output output.cpp output_settings.cpp ${output_UIS_H} ${output_MOCS})
  target_include_directories(output PRIVATE ${CMAKE_SOURCE_DIR}/libol/include ${CMAKE_SOURCE_DIR}/common ${CMAKE_CURRENT_BINARY_DIR} ${JACK_INCLUDE_DIR})
  target_link_libraries(output ${JACK_LIBRARIES} Qt5::Widgets)

  install(TARGETS output RUNTIME DESTINATION bin COMPONENT Applications)

  if(MSVC)
    # Qt

    #https://gitee.com/self49/vnote/blob/master/Packaging.cmake
    get_target_property(_qmake_executable Qt5::qmake IMPORTED_LOCATION)
    get_filename_component(_qt_bin_dir "${_qmake_executable}" DIRECTORY)
    find_program(WINDEPLOYQT_EXECUTABLE windeployqt HINTS "${_qt_bin_dir}" DOC "Path to the windeployqt utility")

    add_custom_command(
      TARGET output POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E remove_directory "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/"
      COMMAND "${CMAKE_COMMAND}" -E
      env PATH="${_qt_bin_dir}" "${WINDEPLOYQT_EXECUTABLE}"
      $<$<CONFIG:Debug>:--debug>
      $<$<CONFIG:Release>:--release>
      --verbose 0
      --no-compiler-runtime
      --no-system-d3d-compiler
      --no-svg
      --no-angle
      --no-opengl
      --no-opengl-sw
      --no-webkit2
      --no-quick-import
      --no-translations
      --dir "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/" $<TARGET_FILE:output>
      COMMAND "${CMAKE_COMMAND}" -E copy_directory "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/" $<TARGET_FILE_DIR:output>
      COMMENT "Deploying Qt libraries using windeployqt for compilation..."
    )

    install(
      DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/"
      DESTINATION bin COMPONENT Applications)

  endif()

  # if(MSVC OR MINGW)
  #   # Install DLLs
  #   install(
  #     CODE "file(GLOB _RUNTIME_DLLS \"${CMAKE_CURRENT_BINARY_DIR}/*.dll\")"
  #     CODE "file(INSTALL \${_RUNTIME_DLLS} DESTINATION \"${CMAKE_INSTALL_PREFIX}/bin\")")
  # endif()

else()

  message(STATUS "Will NOT build output (Qt5Widgets missing)")

endif()
