#include <catch2/catch_test_macros.hpp>
#include <filesystem>
#include <fstream>
#include "pareto_nbd/storage.hpp"

TEST_CASE("LocalDiskStorage round-trips a put through GetPath", "[storage]") {
    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_storage_test";
    std::filesystem::remove_all(tmp_dir);
    pareto_nbd::LocalDiskStorage storage(tmp_dir.string());

    REQUIRE_FALSE(storage.Exists("uploads/abc.csv"));
    storage.Put("uploads/abc.csv", "customer_id,transaction_date\nA,2024-01-01\n");
    REQUIRE(storage.Exists("uploads/abc.csv"));

    std::string path = storage.GetPath("uploads/abc.csv");
    {
        std::ifstream f(path);
        std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
        REQUIRE(content == "customer_id,transaction_date\nA,2024-01-01\n");
    }  // f goes out of scope and closes here

    std::filesystem::remove_all(tmp_dir);
}

TEST_CASE("LocalDiskStorage creates nested directories as needed", "[storage]") {
    auto tmp_dir = std::filesystem::temp_directory_path() / "pareto_nbd_storage_test2";
    std::filesystem::remove_all(tmp_dir);
    pareto_nbd::LocalDiskStorage storage(tmp_dir.string());

    storage.Put("a/b/c/deep.csv", "x");
    REQUIRE(storage.Exists("a/b/c/deep.csv"));

    std::filesystem::remove_all(tmp_dir);
}
