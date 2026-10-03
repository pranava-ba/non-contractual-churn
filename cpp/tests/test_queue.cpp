#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/queue.hpp"

// Every test here targets kTestJobQueueKey (or a key derived from it), never the production
// kJobQueueKey: a real `worker` process consuming the production queue while the suite runs
// would otherwise steal the test's pushed job, or the test would steal a real one.

TEST_CASE("EnqueueJob then DequeueJob round-trips a job id", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    const std::string key = pareto_nbd::kTestJobQueueKey + ":roundtrip";
    REQUIRE(pareto_nbd::EnqueueJob(redis, "job-abc-123", key));
    auto got = pareto_nbd::DequeueJob(redis, 2, key);
    REQUIRE(got.has_value());
    REQUIRE(*got == "job-abc-123");
}

TEST_CASE("DequeueJob times out on an empty queue", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    auto got = pareto_nbd::DequeueJob(redis, 1, pareto_nbd::kTestJobQueueKey + ":always-empty");
    REQUIRE_FALSE(got.has_value());
}

TEST_CASE("The test queue key is distinct from the production queue key", "[queue]") {
    REQUIRE(pareto_nbd::kTestJobQueueKey != pareto_nbd::kJobQueueKey);
}

TEST_CASE("EnqueueJob reports failure (false) when Redis rejects the push", "[queue]") {
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);
    if (!redis) { SKIP("Redis not reachable at " + pareto_nbd::kTestRedisUri); }

    // A key holding a plain string makes RPUSH fail with a WRONGTYPE error reply -- a real
    // Redis-side failure, the same exception path a dropped connection takes.
    const std::string key = pareto_nbd::kTestJobQueueKey + ":wrongtype";
    redis->execCommandSync<std::string>(
        [](const drogon::nosql::RedisResult& r) { return r.getStringForDisplaying(); },
        "SET %s %s", key.c_str(), "not-a-list");
    const bool ok = pareto_nbd::EnqueueJob(redis, "job-should-fail", key);
    redis->execCommandSync<std::string>(
        [](const drogon::nosql::RedisResult& r) { return r.getStringForDisplaying(); },
        "DEL %s", key.c_str());
    REQUIRE_FALSE(ok);
}

TEST_CASE("EnqueueJob returns false for a null Redis client", "[queue]") {
    REQUIRE_FALSE(pareto_nbd::EnqueueJob(nullptr, "job-x", pareto_nbd::kTestJobQueueKey));
}
