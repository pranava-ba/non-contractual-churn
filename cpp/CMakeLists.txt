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
find_package(Arrow CONFIG REQUIRED)

# This vcpkg build of Arrow 25 ships its compute kernels (sort_indices,
# take, etc.) in a separate CMake package, ArrowCompute, rather than folding
# them into Arrow::arrow_shared. The kernels register themselves onto the
# global FunctionRegistry via arrow::compute::Initialize(), whose symbol
# lives in this library, so it must be linked explicitly.
find_package(ArrowCompute CONFIG REQUIRED)
find_package(Drogon CONFIG REQUIRED)

add_library(amortized_inference
    src/version.cpp
    src/moments.cpp
    src/cohort_features.cpp
    src/amortized_model.cpp
    src/nelder_mead.cpp
    src/clv.cpp
    src/conformal.cpp
    src/ingest.cpp
    src/db.cpp
)
target_include_directories(amortized_inference PUBLIC include)
target_link_libraries(amortized_inference PUBLIC
    onnxruntime::onnxruntime
    nlohmann_json::nlohmann_json
    "$<IF:$<BOOL:${ARROW_BUILD_STATIC}>,Arrow::arrow_static,Arrow::arrow_shared>"
    "$<IF:$<BOOL:${ARROW_BUILD_STATIC}>,ArrowCompute::arrow_compute_static,ArrowCompute::arrow_compute_shared>"
    Drogon::Drogon
)

add_executable(main src/main.cpp)
target_link_libraries(main PRIVATE amortized_inference nlohmann_json::nlohmann_json)
target_compile_definitions(main PRIVATE
    PROJECT_MODELS_DIR="${CMAKE_SOURCE_DIR}/../models"
)

add_executable(api_server src/api_main.cpp)
target_link_libraries(api_server PRIVATE amortized_inference Drogon::Drogon)

enable_testing()
add_executable(unit_tests
    tests/test_version.cpp
    tests/test_moments.cpp
    tests/test_cohort_features.cpp
    tests/test_amortized_model.cpp
    tests/test_nelder_mead.cpp
    tests/test_clv.cpp
    tests/test_conformal.cpp
    tests/test_ingest.cpp
    tests/test_api_smoke.cpp
    tests/test_db.cpp
)
target_link_libraries(unit_tests PRIVATE amortized_inference Catch2::Catch2WithMain Drogon::Drogon)
target_compile_definitions(unit_tests PRIVATE
    PROJECT_MODELS_DIR="${CMAKE_SOURCE_DIR}/../models"
    PROJECT_ROOT_DIR="${CMAKE_SOURCE_DIR}/.."
)
include(CTest)
add_test(NAME unit_tests COMMAND unit_tests)
