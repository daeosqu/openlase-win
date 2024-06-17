cmake_minimum_required(VERSION 3.21)
project(example LANGUAGES CXX)

enable_testing()

set(CMAKE_PREFIX_PATH ${LibOL_ROOT}/lib/cmake)

find_package(LibOL CONFIG REQUIRED ${example_LibOL_components})

add_executable(main main.cpp)

target_link_libraries(main PRIVATE LibOL::LibOL)

add_test(NAME libol_version_is_0 COMMAND main)
set_tests_properties(libol_version_is_0 PROPERTIES
  PASS_REGULAR_EXPRESSION "LIBOL_VERSION is 0"
  ENVIRONMENT "PATH=$<TARGET_FILE_DIR:LibOL::LibOL>")
