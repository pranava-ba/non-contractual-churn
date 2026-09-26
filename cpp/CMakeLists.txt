cmake_minimum_required(VERSION 3.25)
project(pareto_nbd_inference CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Catch2 3 CONFIG REQUIRED)

add_library(amortized_inference
    src/version.cpp
)
target_include_directories(amortized_inference PUBLIC include)

add_executable(main src/main.cpp)
target_link_libraries(main PRIVATE amortized_inference)

enable_testing()
add_executable(unit_tests
    tests/test_version.cpp
)
target_link_libraries(unit_tests PRIVATE amortized_inference Catch2::Catch2WithMain)
include(CTest)
add_test(NAME unit_tests COMMAND unit_tests)
