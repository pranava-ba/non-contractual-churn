#include "pareto_nbd/storage.hpp"

#include <filesystem>
#include <fstream>

namespace pareto_nbd {

LocalDiskStorage::LocalDiskStorage(std::string root_dir) : root_dir_(std::move(root_dir)) {
    std::filesystem::create_directories(root_dir_);
}

std::string LocalDiskStorage::GetPath(const std::string& key) {
    return (std::filesystem::path(root_dir_) / key).string();
}

bool LocalDiskStorage::Exists(const std::string& key) {
    return std::filesystem::exists(GetPath(key));
}

void LocalDiskStorage::Put(const std::string& key, const std::string& bytes) {
    auto path = std::filesystem::path(GetPath(key));
    std::filesystem::create_directories(path.parent_path());
    std::ofstream f(path, std::ios::binary);
    f << bytes;
}

}  // namespace pareto_nbd
