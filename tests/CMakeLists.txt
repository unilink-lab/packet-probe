add_executable(test_hex_dump test_hex_dump.cpp)
target_link_libraries(test_hex_dump PRIVATE packet_probe::core)
add_test(NAME test_hex_dump COMMAND test_hex_dump)

add_executable(test_jsonl_recorder test_jsonl_recorder.cpp)
target_link_libraries(test_jsonl_recorder PRIVATE packet_probe::core)
add_test(NAME test_jsonl_recorder COMMAND test_jsonl_recorder)

add_executable(test_latency_tracker test_latency_tracker.cpp)
target_link_libraries(test_latency_tracker PRIVATE packet_probe::core)
add_test(NAME test_latency_tracker COMMAND test_latency_tracker)

add_executable(test_packet_event_direction test_packet_event_direction.cpp)
target_link_libraries(test_packet_event_direction PRIVATE packet_probe::core)
add_test(NAME test_packet_event_direction COMMAND test_packet_event_direction)

add_executable(test_serial_options test_serial_options.cpp)
target_link_libraries(test_serial_options PRIVATE packet_probe::core)
add_test(NAME test_serial_options COMMAND test_serial_options)

add_executable(test_frame_decoders test_frame_decoders.cpp)
target_link_libraries(test_frame_decoders PRIVATE packet_probe::core)
add_test(NAME test_frame_decoders COMMAND test_frame_decoders)

add_executable(test_event_pipeline test_event_pipeline.cpp)
target_link_libraries(test_event_pipeline PRIVATE packet_probe::core)
add_test(NAME test_event_pipeline COMMAND test_event_pipeline)

add_executable(test_send_input_parser test_send_input_parser.cpp)
target_link_libraries(test_send_input_parser PRIVATE packet_probe::core)
add_test(NAME test_send_input_parser COMMAND test_send_input_parser)

add_executable(
  test_cli_options
  test_cli_options.cpp
  ../apps/packet-probe-cli/cli_decoder_options.cpp
  ../apps/packet-probe-cli/cli_send_options.cpp
  ../apps/packet-probe-cli/cli_options.cpp
)
target_include_directories(test_cli_options PRIVATE ../apps/packet-probe-cli)
target_link_libraries(test_cli_options PRIVATE packet_probe::core)
add_test(NAME test_cli_options COMMAND test_cli_options)
