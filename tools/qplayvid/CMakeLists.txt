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

cmake_policy(SET CMP0020 NEW)

if(Qt5Widgets_FOUND AND FFMPEG_FOUND AND BUILD_TRACER)
  QT5_WRAP_CPP(qplayvid_MOCS qplayvid_gui.h)

  add_executable(qplayvid qplayvid.c qplayvid_gui.cpp ${qplayvid_MOCS})
if(MSVC)
  target_sources(qplayvid PRIVATE ../../utf8api.manifest)
  target_compile_options(qplayvid PRIVATE /utf-8)
endif()
  target_include_directories(qplayvid PRIVATE ${FFMPEG_INCLUDE_DIRS} ${THREADS_INCLUDE_DIR})
  target_compile_options(qplayvid PUBLIC ${FFMPEG_CFLAGS_OTHER})
  target_link_directories(qplayvid PRIVATE ${FFMPEG_LIBRARY_DIRS})
  target_link_options(qplayvid PRIVATE ${FFMPEG_LDFLAGS_OTHER})
  target_link_libraries(qplayvid ol ${FFMPEG_LIBRARIES} Qt5::Widgets ${THREADS_LIBRARY})

  install(TARGETS qplayvid RUNTIME DESTINATION bin)

  if(MSVC)
      # # copy pthreadXXX.dll
      # add_custom_command(TARGET qplayvid POST_BUILD
      #     COMMAND ${CMAKE_COMMAND} -E copy_if_different
      #     $<$<CONFIG:Debug>:${THREADS_LIBRARY_DEBUG_DLL}>
      #     $<$<CONFIG:Release>:${THREADS_LIBRARY_RELEASE_DLL}>
      #     $<TARGET_FILE_DIR:qplayvid>)

      # Install Qt5 DLLs
      if (CMAKE_BUILD_TYPE STREQUAL "Debug")
	        find_program(WINDEPLOYQT NAMES windeployqt.debug.bat NO_CACHE)
      else()
	        find_program(WINDEPLOYQT NAMES windeployqt.exe NO_CACHE)
      endif()
      add_custom_command(
          TARGET qplayvid POST_BUILD
          COMMAND ${WINDEPLOYQT} $<TARGET_FILE:qplayvid>
      )

      #TODO MINGW?

      # Install Qt5 Platform plugin DLL (platforms/qwindows.dll)
      install(
          FILES "$<TARGET_FILE:Qt5::QWindowsIntegrationPlugin>"
          DESTINATION bin/platforms
      )
  endif()
else()
  message(STATUS "Will NOT build qplayvid (Qt5 or FFmpeg or tracer missing)")
endif()
