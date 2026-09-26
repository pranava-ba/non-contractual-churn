cmake_minimum_required(VERSION 3.25)
project(pareto_nbd_inference CXX)

# Default to a Release build. This vcpkg build of onnxruntime 1.23.2 (which
# statically embeds onnx 1.19.0) has a debug-only assertion in onnx's
# operator-schema registry (schema.cc's SchemasRegisterer, guarded by
# #ifndef NDEBUG) that spuriously fires the moment any ONNX model is loaded
# in a Debug build, aborting the process. The underlying duplicate-schema
# condition it's asserting on is otherwise harmless (onnx's registry already
# deduplicates and just logs "Schema error: Trying to register..." to
# stderr) — the crash is purely a Debug-build artifact of this
# onnxruntime/onnx/compiler combination. Release (NDEBUG defined) compiles
# the assertion out entirely, so default to it here; pass
# -DCMAKE_BUILD_TYPE=Debug explicitly if you need a debug build and can
# accept AmortizedModel's tests failing.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Catch2 3 CONFIG REQUIRED)
find_package(onnxruntime CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

add_library(amortized_inference
    src/version.cpp
    src/moments.cpp
    src/cohort_features.cpp
    src/amortized_model.cpp
)
target_include_directories(amortized_inference PUBLIC include)
target_link_libraries(amortized_inference PUBLIC
    onnxruntime::onnxruntime
    nlohmann_json::nlohmann_json
)

add_executable(main src/main.cpp)
target_link_libraries(main PRIVATE amortized_inference nlohmann_json::nlohmann_json)
target_compile_definitions(main PRIVATE
    PROJECT_MODELS_DIR="${CMAKE_SOURCE_DIR}/../models"
)

enable_testing()
add_executable(unit_tests
    tests/test_version.cpp
    tests/test_moments.cpp
    tests/test_cohort_features.cpp
    tests/test_amortized_model.cpp
)
target_link_libraries(unit_tests PRIVATE amortized_inference Catch2::Catch2WithMain)
target_compile_definitions(unit_tests PRIVATE
    PROJECT_MODELS_DIR="${CMAKE_SOURCE_DIR}/../models"
)
include(CTest)
add_test(NAME unit_tests COMMAND unit_tests)
