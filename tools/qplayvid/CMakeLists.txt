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

if(Qt5Widgets_FOUND AND FFMPEG_FOUND AND BUILD_TRACER)
  QT5_WRAP_CPP(qplayvid_MOCS qplayvid_gui.h)

  add_executable(qplayvid qplayvid.c qplayvid_gui.cpp ${qplayvid_MOCS})
  if(MSVC)
    target_sources(qplayvid PRIVATE ../../utf8api.manifest)
    target_compile_options(qplayvid PRIVATE /utf-8)
  endif()
  target_compile_features(playvid2 PUBLIC c_std_99)
  #target_include_directories(qplayvid PRIVATE ${THREADS_INCLUDE_DIR})
  target_link_libraries(qplayvid OpenLase::LibOL FFmpeg::avcodec FFmpeg::avdevice FFmpeg::avformat FFmpeg::swscale FFmpeg::swresample FFmpeg::avutil Qt5::Widgets ${THREADS_LIBRARY} ${GETOPT_LIBRARY})

  install(TARGETS qplayvid RUNTIME DESTINATION bin COMPONENT Applications)

  if(MSVC)
    get_target_property(_qmake_executable Qt5::qmake IMPORTED_LOCATION)
    get_filename_component(_qt_bin_dir "${_qmake_executable}" DIRECTORY)
    find_program(WINDEPLOYQT_EXECUTABLE windeployqt HINTS "${_qt_bin_dir}" DOC "Path to the windeployqt utility")

    if(NOT WINDEPLOYQT_EXECUTABLE)
      message(FATAL_ERROR "windeployqt is required to build on Windows")
    else()
      message(STATUS "Using windeployqt: ${WINDEPLOYQT_EXECUTABLE}")
    endif()

    add_custom_command(
      TARGET qplayvid POST_BUILD
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
      --dir "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/" $<TARGET_FILE:qplayvid>
      COMMAND "${CMAKE_COMMAND}" -E copy_directory "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/" $<TARGET_FILE_DIR:qplayvid>
      COMMENT "Deploying Qt libraries using windeployqt for compilation..."
    )

    install(
      DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/qtDeploy/"
      DESTINATION bin COMPONENT Applications)

  endif()

  # # Install DLLs
  # if(MSVC OR MINGW)
  #   install(
  #     CODE "file(GLOB _RUNTIME_DLLS \"${CMAKE_CURRENT_BINARY_DIR}/*.dll\")"
  #     CODE "file(INSTALL \${_RUNTIME_DLLS} DESTINATION \"${CMAKE_INSTALL_PREFIX}/bin\")")
  # endif()

else()
  message(STATUS "Will NOT build qplayvid (Qt5 or FFmpeg or tracer missing)")
endif()
