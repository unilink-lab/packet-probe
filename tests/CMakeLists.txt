add_executable(test_hex_dump test_hex_dump.cpp)
target_link_libraries(test_hex_dump PRIVATE packet_probe::core)
add_test(NAME test_hex_dump COMMAND test_hex_dump)

add_executable(test_jsonl_recorder test_jsonl_recorder.cpp)
target_link_libraries(test_jsonl_recorder PRIVATE packet_probe::core)
add_test(NAME test_jsonl_recorder COMMAND test_jsonl_recorder)
