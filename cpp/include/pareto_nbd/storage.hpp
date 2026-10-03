#pragma once
#include <string>

namespace pareto_nbd {

// Where uploaded CSVs and generated exports live. Every caller (the upload endpoint, the
// worker, the export endpoint) goes through this interface, never a filesystem or S3 API
// directly -- swapping LocalDiskStorage for a MinIO-backed implementation later touches only
// this file's implementation, not any call site. See the plan's Global Constraints for why
// MinIO itself isn't built in this phase.
class UploadStorage {
public:
    virtual ~UploadStorage() = default;
    virtual void Put(const std::string& key, const std::string& bytes) = 0;
    virtual bool Exists(const std::string& key) = 0;
    // Returns a filesystem path ingest_csv (or any other local reader) can open directly.
    // A future remote-storage implementation would instead download to a temp file here and
    // return that path -- callers never need to know the difference.
    virtual std::string GetPath(const std::string& key) = 0;
};

class LocalDiskStorage : public UploadStorage {
public:
    explicit LocalDiskStorage(std::string root_dir);
    void Put(const std::string& key, const std::string& bytes) override;
    bool Exists(const std::string& key) override;
    std::string GetPath(const std::string& key) override;

private:
    std::string root_dir_;
};

}  // namespace pareto_nbd
