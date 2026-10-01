#pragma once
#include <drogon/nosql/RedisClient.h>
#include <optional>
#include <string>

namespace pareto_nbd {

// Local dev Redis URI, matching docker-compose.yml's redis service (Task 1).
// Production wiring (env-var override) is a Phase-4-hardening concern, not this plan's.
inline const std::string kTestRedisUri = "redis://127.0.0.1:6379";

inline const std::string kJobQueueKey = "pareto_nbd:jobs:queue";

// Connects synchronously (a short-timeout PING) so callers can detect "Redis isn't running"
// up front and SKIP their test, rather than hanging on Drogon's async retry loop. Returns
// nullptr on failure instead of throwing -- this is a reachability probe, not a runtime
// connection (the returned RedisClientPtr, once obtained, is used for real async calls).
// redis_uri must look like "redis://host:port"; the scheme and port are optional.
drogon::nosql::RedisClientPtr ConnectRedis(const std::string& redis_uri);

// Pushes job_id onto the tail of the shared job queue (RPUSH). Blocks the calling thread
// until the write is acknowledged (or fails), mirroring ApplySchema's synchronous feel.
void EnqueueJob(drogon::nosql::RedisClientPtr redis, const std::string& job_id);

// Blocking pop (Redis BLPOP) with a timeout in seconds; std::nullopt on timeout, the job id
// string otherwise. A timeout, not an infinite block, is what lets the worker's loop (Task
// 6) periodically check for a shutdown signal between dequeue attempts.
std::optional<std::string> DequeueJob(drogon::nosql::RedisClientPtr redis, int timeout_seconds);

}  // namespace pareto_nbd
