#include <drogon/drogon.h>
#include <iostream>
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"

int main() {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    pareto_nbd::LocalDiskStorage storage("./data/uploads");

    if (!db || !redis) {
        std::cerr << "worker: Postgres/Redis unreachable, exiting\n";
        return 1;
    }

    std::cout << "worker: polling for jobs...\n";
    while (true) {
        auto job_id = pareto_nbd::DequeueJob(redis, 5);
        if (!job_id) { continue; }
        std::cout << "worker: processing job " << *job_id << "\n";
        pareto_nbd::ProcessOneJob(*job_id, db, storage);
    }
}
