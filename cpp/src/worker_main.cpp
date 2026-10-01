#include <drogon/drogon.h>
#include <exception>
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
        // Last line of defence: ProcessOneJob is documented never to throw, but a genuinely
        // unexpected exception from any iteration (dequeue included) must cost at most that
        // one job -- never the whole worker process, which would stop every queued job behind
        // it from being processed.
        try {
            auto job_id = pareto_nbd::DequeueJob(redis, 5);
            if (!job_id) { continue; }
            std::cout << "worker: processing job " << *job_id << "\n";
            pareto_nbd::ProcessOneJob(*job_id, db, storage);
        } catch (const std::exception& e) {
            std::cerr << "worker: unexpected error in job loop (continuing): " << e.what()
                      << "\n";
        } catch (...) {
            std::cerr << "worker: unexpected non-standard error in job loop (continuing)\n";
        }
    }
}
