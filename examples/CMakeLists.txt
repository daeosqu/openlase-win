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

include_directories(
    ${CMAKE_SOURCE_DIR}/libol/include
    ${CMAKE_SOURCE_DIR}/include
    ${JACK_INCLUDE_DIR})

add_executable(circlescope circlescope.c)
target_link_libraries(circlescope ${JACK_LIBRARIES} ${MATH_LIBRARY})
install(TARGETS circlescope RUNTIME DESTINATION bin COMPONENT Applications)

add_executable(scope scope.c)
target_link_libraries(scope ${JACK_LIBRARIES} ${MATH_LIBRARY})
install(TARGETS scope RUNTIME DESTINATION bin COMPONENT Applications)

add_executable(simple simple.c)
target_link_libraries(simple OpenLase::LibOL)
install(TARGETS simple RUNTIME DESTINATION bin COMPONENT Applications)

if(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
  add_executable(pong pong.c)
  target_link_libraries(pong OpenLase::LibOL)
  install(TARGETS pong RUNTIME DESTINATION bin COMPONENT Applications)
else()
  message(STATUS "Will NOT build pong (Not a linux system)")
endif()

if(ALSA_FOUND)
  add_executable(midiview midiview.c)
  target_link_libraries(midiview OpenLase::LibOL ${ALSA_LIBRARIES})
  install(TARGETS midiview RUNTIME DESTINATION bin COMPONENT Applications)
else()
  message(STATUS "Will NOT build midiview (ALSA missing)")
endif()

add_executable(harp harp.c)
target_link_libraries(harp OpenLase::LibOL)
install(TARGETS harp RUNTIME DESTINATION bin COMPONENT Applications)

add_subdirectory(27c3_slides)
add_subdirectory(lase_demo)

# install python scripts

file(GLOB PYTHON_SCRIPTS "*.py")
install(FILES ${PYTHON_SCRIPTS} DESTINATION bin COMPONENT Applications)
