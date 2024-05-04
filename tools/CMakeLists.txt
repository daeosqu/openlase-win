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

include_directories (${CMAKE_SOURCE_DIR}/include ${JACK_INCLUDE_DIR})
link_directories (${CMAKE_BINARY_DIR}/libol)

add_executable(playilda playilda.c)
target_link_libraries(playilda ${JACK_LIBRARIES})
install(TARGETS playilda RUNTIME DESTINATION bin)

add_executable(invert invert.c)
target_link_libraries(invert ${JACK_LIBRARIES})
install(TARGETS invert RUNTIME DESTINATION bin)

add_executable(cal cal.c)
target_link_libraries(cal ${JACK_LIBRARIES} ${MATH_LIBRARY})
install(TARGETS cal RUNTIME DESTINATION bin)

if(FFMPEG_FOUND AND BUILD_TRACER)
 #include_directories(${FFMPEG_INCLUDE_DIR})
 add_executable(playvid playvid.c)
 target_include_directories(playvid PRIVATE ${FFMPEG_INCLUDE_DIRS})
 target_compile_options(playvid PRIVATE ${FFMPEG_CFLAGS_OTHER})
 target_link_directories(playvid PRIVATE ${FFMPEG_LIBRARY_DIRS})
 target_link_options(playvid PRIVATE ${FFMPEG_LDFLAGS_OTHER})
 target_link_libraries(playvid ol ${FFMPEG_LIBRARIES} ${GETOPT_LIBRARY})
 install(TARGETS playvid RUNTIME DESTINATION bin)
else()
  message(STATUS "Will NOT build playvid (FFmpeg or tracer missing)")
endif()

if(OPENGL_FOUND AND GLUT_FOUND)
  add_executable(simulator simulator.c)
  include_directories(${OPENGL_INCLUDE_DIRS} ${GLUT_INCLUDE_DIR})
  target_link_libraries(simulator ${MATH_LIBRARY} ${OPENGL_LIBRARIES} ${GLUT_LIBRARY} ${JACK_LIBRARIES} ${GETOPT_LIBRARY} ${COMMON_LIBRARY})
  #install(TARGETS simulator RUNTIME DESTINATION bin)
  install(TARGETS simulator
      RUNTIME DESTINATION bin
      LIBRARY DESTINATION bin)
else()
  message(STATUS "Will NOT build simulator (OpenGL or GLUT missing)")
endif()

add_subdirectory(qplayvid)

# Python scripts

file(GLOB PYTHON_SCRIPTS "*.py")
install(FILES ${PYTHON_SCRIPTS} DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
