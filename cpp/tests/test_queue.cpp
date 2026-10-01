#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/queue.hpp"

TEST_CASE("EnqueueJob then DequeueJob round-trips a job id", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    pareto_nbd::EnqueueJob(redis, "job-abc-123");
    auto got = pareto_nbd::DequeueJob(redis, 2);
    REQUIRE(got.has_value());
    REQUIRE(*got == "job-abc-123");
}

TEST_CASE("DequeueJob times out on an empty queue", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    auto got = pareto_nbd::DequeueJob(redis, 1);
    REQUIRE_FALSE(got.has_value());
}
