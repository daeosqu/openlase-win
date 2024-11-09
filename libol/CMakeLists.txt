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

#################
##  Variables  ##
#################

set(LIBRARY_NAMESPACE "${PROJECT_NAME}")
set(LIBRARY_VERSION "0.0.2.1")
set(LIBRARY_TARGET_NAME LibOL)
set(LIBRARY_INCLUDE_DIRECTORY_NAME libol)
set(LIBRARY_OUTPUT_NAME ol)
set(export_h_prefix "LIBOL")

if(MSVC AND NOT BUILD_SHARED_LIBS)
  set(LIBRARY_OUTPUT_NAME "${LIBRARY_OUTPUT_NAME}_static")
endif()
set(${LIBRARY_TARGET_NAME}_SRC
  ${CMAKE_CURRENT_SOURCE_DIR}/libol.c
  ${CMAKE_CURRENT_SOURCE_DIR}/text.c
  ${CMAKE_CURRENT_SOURCE_DIR}/ilda.c
  ${CMAKE_CURRENT_BINARY_DIR}/fontdef.c
)
set(${LIBRARY_TARGET_NAME}_HDR
  ${CMAKE_CURRENT_SOURCE_DIR}/include/libol/ilda.h
  ${CMAKE_CURRENT_SOURCE_DIR}/include/libol/libol.h
  ${CMAKE_CURRENT_SOURCE_DIR}/include/libol/libol_compat.h
  ${CMAKE_CURRENT_SOURCE_DIR}/include/libol/text.h
  ${CMAKE_CURRENT_SOURCE_DIR}/include/libol/trace.h
  ${CMAKE_CURRENT_BINARY_DIR}/include/libol/libol_export.h
  ${CMAKE_CURRENT_BINARY_DIR}/include/libol/libol_config.h
)

###############
##  Options  ##
###############

option(LIBOL_INCLUDE_PACKAGING "Include packaging rules for libol" YES)

################
##  Packages  ##
################

find_package(JACK REQUIRED)

###############
##  Library  ##
###############

add_library(${LIBRARY_TARGET_NAME})
add_library(${LIBRARY_NAMESPACE}::${LIBRARY_TARGET_NAME}
  ALIAS ${LIBRARY_TARGET_NAME})

##############
##  Tracer  ##
##############

# for YASM
if(CMAKE_SIZEOF_VOID_P EQUAL 8)
  set(BITS 64)
else()
  set(BITS 32)
endif()

if(NOT DEFINED BUILD_TRACER)
  # Should be "Y" or not
  set(BUILD_TRACER "Y" CACHE BOOL "Build the image tracer" FORCE)
endif()

set(TRACER_SOURCES "")
if(BUILD_TRACER)
  if(MSVC)
	  set(ASM_SRCS imgproc_sse2.asm)

	  # Custom YASM rules since cmake + MSVC + yasm is generally busted
	  # http://www.cmake.org/Bug/print_bug_page.php?bug_id=8170
	  find_program(YASM_EXECUTABLE
		  NAMES yasm yasm-1.2.0-win32 yasm-1.2.0-win64
		  HINTS $ENV{YASM_ROOT} ${YASM_ROOT}
		  PATH_SUFFIXES bin
		)
	  if(YASM_EXECUTABLE)
		  execute_process(COMMAND ${YASM_EXECUTABLE} --version
			  OUTPUT_VARIABLE yasm_version
			  ERROR_QUIET
			  OUTPUT_STRIP_TRAILING_WHITESPACE
			)
		  if(yasm_version MATCHES "^yasm ([0-9\\.]*)")
			  set(YASM_VERSION_STRING "${CMAKE_MATCH_1}")
		  endif()
		  if (YASM_VERSION_STRING VERSION_LESS "1.2.0")
			  message(STATUS "Yasm version ${YASM_VERSION_STRING} is too old. 1.2.0 or later required")
		  else()
			  message(STATUS "Found Yasm ${YASM_VERSION_STRING} to build assembly primitives")
			  #file(APPEND config.h "#define HAVE_MMX 1\n")

			  if (CMAKE_SIZEOF_VOID_P EQUAL 8)
				  set(FLAGS -f win64 -m amd64 -DARCH_X86_64=1 -DHAVE_ALIGNED_STACK=0)
			  else()
				  set(FLAGS -f win32 -DARCH_X86_64=0 -DHAVE_ALIGNED_STACK=0 -DPREFIX)
			  endif()
			  # if (HIGH_BIT_DEPTH)
			  #     set(FLAGS ${FLAGS} -DHIGH_BIT_DEPTH=1 -DBIT_DEPTH=10)
			  # else()
			  #     set(FLAGS ${FLAGS} -DHIGH_BIT_DEPTH=0 -DBIT_DEPTH=8)
			  # endif()
			  foreach(ASM ${ASM_SRCS})
				  set(YASM_SRC ${CMAKE_CURRENT_SOURCE_DIR}/${ASM})
				  set(YASM_SRCS ${YASM_SRCS} ${YASM_SRC})
				  set(YASM_OBJ ${CMAKE_CURRENT_BINARY_DIR}/${ASM}.obj)
				  set(YASM_OBJS ${YASM_OBJS} ${YASM_OBJ})
				  add_custom_command(
					  OUTPUT ${YASM_OBJ}
					  COMMAND ${YASM_EXECUTABLE} ARGS ${FLAGS} -DNO_MINGW=1 -Dprivate_prefix=ol ${YASM_SRC} -o ${YASM_OBJ}
					  DEPENDS ${YASM_SRC})
			  endforeach()
			  source_group(Assembly FILES ${ASM_C} ${YASM_SRCS})
		  endif()
	    set(TRACER_SOURCES trace.c ${YASM_OBJS})
	    set(COMPILED_YASM_OBJS ${YASM_OBJS})
      message(STATUS "Will build tracer (SSE2 version)")
    else()
      message(STATUS "YASM Not Found!")
	  endif()
  else()
    if(${CMAKE_SYSTEM_PROCESSOR} MATCHES "armv7")
      add_compile_options(-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard)
      set(TRACER_SOURCES trace.c imgproc_neon.S)
      enable_language(ASM)
      message(STATUS "Will build tracer (armv7 NEON version)")
    else()
      set(TRACER_SOURCES trace.c imgproc_sse2.asm)
      enable_language(ASM_YASM)
      message(STATUS "Will build tracer (SSE2 version)")
    endif()
  endif()
else()
  message(STATUS "Will NOT build tracer")
endif()

# Compiler options
target_compile_features(${LIBRARY_TARGET_NAME} PRIVATE cxx_std_11)
target_compile_definitions(${LIBRARY_TARGET_NAME} PUBLIC "$<$<NOT:$<BOOL:${BUILD_SHARED_LIBS}>>:${export_h_prefix}_STATIC_DEFINE>")

target_include_directories(${LIBRARY_TARGET_NAME}
  PRIVATE
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>"
  "$<BUILD_INTERFACE:${JACK_INCLUDE_DIR}>"
  PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/include>"
  "$<INSTALL_INTERFACE:include>"
)

target_link_libraries(${LIBRARY_TARGET_NAME} PUBLIC Jack::Jack ${MATH_LIBRARY} PRIVATE ${CMAKE_THREAD_LIBS_INIT})

set_target_properties(${LIBRARY_TARGET_NAME} PROPERTIES
  OUTPUT_NAME "${LIBRARY_OUTPUT_NAME}")

set_target_properties(${LIBRARY_TARGET_NAME} PROPERTIES
  DEBUG_POSTFIX "${CMAKE_DEBUG_POSTFIX}")

set_target_properties(${LIBRARY_TARGET_NAME} PROPERTIES
  POSITION_INDEPENDENT_CODE ON)

target_include_directories(${LIBRARY_TARGET_NAME}
  PUBLIC "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:$<INSTALL_PREFIX>/${CMAKE_INSTALL_INCLUDEDIR}>")

target_sources(${LIBRARY_TARGET_NAME}
  PRIVATE "${${LIBRARY_TARGET_NAME}_SRC}"
  PRIVATE "${TRACER_SOURCES}")

set_target_properties(${LIBRARY_TARGET_NAME} PROPERTIES
  VERSION "${LIBRARY_VERSION}"
  PUBLIC_HEADER "${${LIBRARY_TARGET_NAME}_HDR}")

# libol_export.h

generate_export_header(${LIBRARY_TARGET_NAME} EXPORT_FILE_NAME ./include/libol/libol_export.h)

# libol_config.h

check_include_file(malloc.h HAVE_MALLOC_H)
check_symbol_exists(memalign malloc.h HAVE_MEMALIGN)
check_symbol_exists(posix_memalign stdlib.h HAVE_POSIX_MEMALIGN)
check_symbol_exists(_aligned_malloc malloc.h HAVE_ALIGNED_MALLOC)
configure_file(./include/libol/libol_config.h.in ./include/libol/libol_config.h @ONLY)

# fontdef.c

add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/fontdef.c
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/genfont.py
  MAIN_DEPENDENCY laserfont.svg
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/genfont.py ${CMAKE_CURRENT_SOURCE_DIR}/laserfont.svg ${CMAKE_CURRENT_BINARY_DIR}/fontdef.c default_font)

#################
##  Packaging  ##
#################

if (LIBOL_INCLUDE_PACKAGING)
  add_subdirectory(packaging)
endif ()
