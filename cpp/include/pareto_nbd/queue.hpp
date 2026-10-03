#pragma once
#include <drogon/nosql/RedisClient.h>
#include <optional>
#include <string>

namespace pareto_nbd {

// Local dev Redis URI, matching docker-compose.yml's redis service (Task 1).
// Production wiring (env-var override) is a Phase-4-hardening concern, not this plan's.
inline const std::string kTestRedisUri = "redis://127.0.0.1:6379";

// The production job queue: POST /uploads pushes here and the real `worker` binary consumes
// from here. Every production caller uses this key via EnqueueJob/DequeueJob's defaults.
inline const std::string kJobQueueKey = "pareto_nbd:jobs:queue";

// A separate queue key for the test binary (the shared test server fixture's /uploads route,
// and the queue/upload/integration tests that dequeue from it). Kept distinct from
// kJobQueueKey so running the test suite while a real `worker` process is live can never have
// that worker steal a test's job (or a test steal a real job) -- both share one Redis.
inline const std::string kTestJobQueueKey = "pareto_nbd:jobs:test_queue";

// Connects synchronously (a short-timeout PING) so callers can detect "Redis isn't running"
// up front and SKIP their test, rather than hanging on Drogon's async retry loop. Returns
// nullptr on failure instead of throwing -- this is a reachability probe, not a runtime
// connection (the returned RedisClientPtr, once obtained, is used for real async calls).
// redis_uri must look like "redis://host:port"; the scheme and port are optional.
drogon::nosql::RedisClientPtr ConnectRedis(const std::string& redis_uri);

// Pushes job_id onto the tail of queue_key (RPUSH; the production queue unless a caller
// explicitly passes another key). Blocks the calling thread until the write is acknowledged,
// fails, or a 5-second deadline passes. Returns true only when Redis acknowledged the push;
// false on any failure (Redis error reply, broken connection, timeout) -- the caller must
// treat false as "this job will never be picked up". Returns a bool rather than throwing,
// matching ConnectDb/ConnectRedis's existing report-failure-by-return-value convention.
[[nodiscard]] bool EnqueueJob(drogon::nosql::RedisClientPtr redis, const std::string& job_id,
                              const std::string& queue_key = kJobQueueKey);

// Blocking pop (Redis BLPOP) with a timeout in seconds; std::nullopt on timeout, the job id
// string otherwise. A timeout, not an infinite block, is what lets the worker's loop (Task
// 6) periodically check for a shutdown signal between dequeue attempts.
// queue_key defaults to the production queue (see kTestJobQueueKey for tests).
std::optional<std::string> DequeueJob(drogon::nosql::RedisClientPtr redis, int timeout_seconds,
                                      const std::string& queue_key = kJobQueueKey);

}  // namespace pareto_nbd
