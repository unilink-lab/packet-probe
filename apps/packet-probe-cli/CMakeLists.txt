add_executable(packet-probe main.cpp)

target_compile_features(packet-probe PRIVATE cxx_std_17)
target_link_libraries(packet-probe PRIVATE packet_probe::capture)
set_target_properties(packet-probe PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
