add_executable(demo demo.c trace.c)
target_include_directories(demo PRIVATE ${JACK_INCLUDE_DIR} ${MODPLUG_INCLUDE_DIRS})
target_link_libraries(demo OpenLase::LibOL ${MODPLUG_LIBRARIES} ${JACK_LIBRARY} ${COMMON_LIBRARIES})

install(TARGETS demo RUNTIME DESTINATION bin COMPONENT Applications)
foreach(name GLOS-pope.xm euskal18.ild lase_title.ild)
    install(FILES ${CMAKE_CURRENT_LIST_DIR}/${name} DESTINATION bin COMPONENT Applications)
endforeach()
