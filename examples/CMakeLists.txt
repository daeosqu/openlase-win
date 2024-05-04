#         OpenLase - a realtime laser graphics toolkit
#
# Copyright (C) 2009-2011 Hector Martin "marcan" <hector@marcansoft.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 or version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#

include_directories (${CMAKE_SOURCE_DIR}/include ${JACK_INCLUDE_DIR})
link_directories (${CMAKE_BINARY_DIR}/libol)

add_executable(circlescope circlescope.c)
target_link_libraries(circlescope ${JACK_LIBRARIES} ${MATH_LIBRARY})
install(TARGETS circlescope RUNTIME DESTINATION bin)

add_executable(scope scope.c)
target_link_libraries(scope ${JACK_LIBRARIES} ${MATH_LIBRARY})
install(TARGETS scope RUNTIME DESTINATION bin)

add_executable(simple simple.c)
target_link_libraries(simple ol)
install(TARGETS simple RUNTIME DESTINATION bin)

if(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
  add_executable(pong pong.c)
  target_link_libraries(pong ol)
  install(TARGETS pong RUNTIME DESTINATION bin)
else()
  message(STATUS "Will NOT build pong (Not a linux system)")
endif()

if(ALSA_FOUND)
  add_executable(midiview midiview.c)
  target_link_libraries(midiview ol ${ALSA_LIBRARIES})
  install(TARGETS midiview RUNTIME DESTINATION bin)
else()
  message(STATUS "Will NOT build midiview (ALSA missing)")
endif()

add_executable(harp harp.c)
target_link_libraries(harp ol)
install(TARGETS harp RUNTIME DESTINATION bin)

add_subdirectory(27c3_slides)

# Note: this target needs modplug but I'm too lazy to add a module finder for
# it.
add_subdirectory(lase_demo)

# install python scripts

file(GLOB PYTHON_SCRIPTS "*.py")
install(FILES ${PYTHON_SCRIPTS} DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)

