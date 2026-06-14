cmake_minimum_required(VERSION 3.16)

project(
  packet-probe
  VERSION 0.1.0
  DESCRIPTION "Lightweight device communication analyzer"
  LANGUAGES CXX
)

option(PACKET_PROBE_BUILD_TESTS "Build Packet Probe tests" ON)
option(PACKET_PROBE_USE_UNILINK "Build TCP capture support with unilink-core" ON)
set(PACKET_PROBE_UNILINK_SOURCE_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../unilink"
    CACHE PATH "Path to a local unilink source tree"
)

add_library(
  packet_probe_core
  src/core/packet_event.cpp
  src/core/hex_dump.cpp
  src/core/endpoint.cpp
  src/core/latency_tracker.cpp
  src/core/serial_options.cpp
  src/core/event_pipeline.cpp
  src/decoder/frame_decoder.cpp
  src/decoder/fixed_size_frame_decoder.cpp
  src/decoder/delimiter_frame_decoder.cpp
  src/decoder/length_prefix_frame_decoder.cpp
  src/decoder/frame_decoder_factory.cpp
  src/recorder/jsonl_recorder.cpp
)
add_library(packet_probe::core ALIAS packet_probe_core)

target_compile_features(packet_probe_core PUBLIC cxx_std_20)
target_include_directories(
  packet_probe_core
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         $<INSTALL_INTERFACE:include>
)

if(PACKET_PROBE_USE_UNILINK)
  if(EXISTS "${PACKET_PROBE_UNILINK_SOURCE_DIR}/CMakeLists.txt")
    set(UNILINK_BUILD_TESTS
        OFF
        CACHE BOOL "" FORCE
    )
    add_subdirectory("${PACKET_PROBE_UNILINK_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/_deps/unilink")
  else()
    find_package(unilink CONFIG REQUIRED)
  endif()

  add_library(
    packet_probe_capture
    src/capture/tcp_direct_capture_session.cpp
    src/capture/tcp_proxy_capture_session.cpp
    src/capture/serial_direct_capture_session.cpp
    src/capture/udp_direct_capture_session.cpp
  )
  add_library(packet_probe::capture ALIAS packet_probe_capture)
  target_compile_features(packet_probe_capture PUBLIC cxx_std_20)
  target_include_directories(
    packet_probe_capture
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
           $<INSTALL_INTERFACE:include>
  )
  target_link_libraries(packet_probe_capture PUBLIC packet_probe::core unilink::unilink)

  add_subdirectory(apps/packet-probe-cli)
endif()

if(PACKET_PROBE_BUILD_TESTS)
  include(CTest)
  enable_testing()
  add_subdirectory(tests)
endif()
