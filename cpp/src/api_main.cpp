#include <drogon/drogon.h>

#include <algorithm>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

#include "pareto_nbd/api_routes.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

namespace {

// Largest accepted POST /uploads body. Drogon's default (1 MB) rejected a 60k-row CSV
// (~1.6 MB) with 413, but spec §2 targets "hundreds of thousands+ rows" per upload. At the
// ~27 bytes/row of a typical customer_id,transaction_date,amount line, 100 MB is roughly
// 3-4 million rows -- comfortably above that target while still bounding a single request.
// Bodies above Drogon's 64 KB in-memory threshold are spooled to a temp file by Drogon
// itself, so this limit does not mean holding 100 MB in RAM per request before the handler
// runs.
constexpr size_t kMaxUploadBytes = 100 * 1024 * 1024;

// Event-loop (IO) thread count. Drogon defaults to ONE, and POST /uploads does synchronous
// work (ingest_csv parsing + disk writes + Postgres round trips) directly on that thread, so
// a single in-flight upload would stall every other request, /healthz included. Use the
// hardware concurrency, clamped to [2, 8]: at least 2 so one upload can never block the
// whole server even on a 1-core box (or when hardware_concurrency() reports 0, "unknown"),
// and at most 8 because the expensive estimation work lives in the separate worker process,
// not here -- more API threads than that would mostly just queue on Postgres.
size_t ApiThreadCount() {
    const unsigned hw = std::thread::hardware_concurrency();
    return std::clamp<size_t>(hw == 0 ? 2 : hw, 2, 8);
}

// Location of db/schema.sql at runtime. PARETO_NBD_SCHEMA_PATH (env) wins when set -- for a
// deployed binary that no longer sits next to its source tree (e.g. a container image);
// otherwise fall back to the source tree's db/schema.sql, baked in at compile time via the
// PARETO_NBD_DEFAULT_SCHEMA_PATH definition in CMakeLists.txt (the same idea as the test
// binary's PROJECT_ROOT_DIR).
std::string SchemaPath() {
    if (const char* env = std::getenv("PARETO_NBD_SCHEMA_PATH"); env != nullptr && *env != '\0') {
        return env;
    }
    return PARETO_NBD_DEFAULT_SCHEMA_PATH;
}

}  // namespace

int main() {
    const size_t threads = ApiThreadCount();

    auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>("./data/uploads");
    // One Postgres connection per event-loop thread, so concurrent handlers don't serialize
    // on a single connection.
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString, threads);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);

    // ConnectDb/ConnectRedis return nullptr when the service is unreachable. Fail fast here
    // (same pattern as worker_main.cpp) instead of booting a server whose first real request
    // would null-dereference -- a crash Drogon's per-handler exception handling can't catch.
    if (!db || !redis) {
        std::cerr << "api_server: Postgres/Redis unreachable, exiting\n";
        return 1;
    }

    // Apply the (idempotent) schema once at startup so a fresh `docker compose up -d` works
    // without the test suite having been run first -- previously only the test binary ever
    // called ApplySchema, so every POST /uploads 500'd against a brand-new database.
    const std::string schema_path = SchemaPath();
    try {
        pareto_nbd::ApplySchema(db, schema_path);
    } catch (const std::exception& e) {
        std::cerr << "api_server: failed to apply schema from '" << schema_path
                  << "': " << e.what() << "\n";
        return 1;
    }

    pareto_nbd::RegisterApiRoutes(storage, db, redis);

    drogon::app().setClientMaxBodySize(kMaxUploadBytes);
    drogon::app().setThreadNum(threads);
    drogon::app().addListener("0.0.0.0", 8080);
    std::cout << "api_server: listening on 0.0.0.0:8080 with " << threads << " IO threads" << std::endl;
    drogon::app().run();
    return 0;
}
