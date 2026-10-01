#include "pareto_nbd/queue.hpp"

#include <chrono>
#include <cstdint>
#include <future>

namespace pareto_nbd {

namespace {

// Splits a "redis://host:port" (or bare "host:port", or bare "host") URI into its host and
// port parts. RedisClient::newRedisClient takes a trantor::InetAddress, not a URI string
// directly, so this is the glue between the two. Not a general URI parser -- adequate for
// this project's own kTestRedisUri and docker-compose-style host:port strings only.
void ParseRedisUri(const std::string& redis_uri, std::string* host, uint16_t* port) {
    std::string rest = redis_uri;
    const std::string scheme = "redis://";
    if (rest.rfind(scheme, 0) == 0) {
        rest = rest.substr(scheme.size());
    }

    auto colon_pos = rest.find(':');
    if (colon_pos == std::string::npos) {
        *host = rest;
        *port = 6379;
    } else {
        *host = rest.substr(0, colon_pos);
        *port = static_cast<uint16_t>(std::stoi(rest.substr(colon_pos + 1)));
    }
}

}  // namespace

drogon::nosql::RedisClientPtr ConnectRedis(const std::string& redis_uri) {
    try {
        std::string host;
        uint16_t port = 6379;
        ParseRedisUri(redis_uri, &host, &port);

        auto redis = drogon::nosql::RedisClient::newRedisClient(
            trantor::InetAddress(host, port), 1 /* connection pool size */);
        // newRedisClient connects asynchronously; force a real round trip with a short
        // deadline so an unreachable Redis fails fast instead of hanging.
        auto promise = std::make_shared<std::promise<bool>>();
        auto future = promise->get_future();
        redis->execCommandAsync(
            [promise](const drogon::nosql::RedisResult&) { promise->set_value(true); },
            [promise](const drogon::nosql::RedisException&) { promise->set_value(false); },
            "PING");
        if (future.wait_for(std::chrono::seconds(2)) != std::future_status::ready ||
            !future.get()) {
            return nullptr;
        }
        return redis;
    } catch (...) {
        return nullptr;
    }
}

void EnqueueJob(drogon::nosql::RedisClientPtr redis, const std::string& job_id) {
    auto promise = std::make_shared<std::promise<void>>();
    auto future = promise->get_future();
    redis->execCommandAsync(
        [promise](const drogon::nosql::RedisResult&) { promise->set_value(); },
        [promise](const drogon::nosql::RedisException&) { promise->set_value(); },
        "RPUSH %s %s", kJobQueueKey.c_str(), job_id.c_str());
    future.wait();
}

std::optional<std::string> DequeueJob(drogon::nosql::RedisClientPtr redis, int timeout_seconds) {
    auto promise = std::make_shared<std::promise<std::optional<std::string>>>();
    auto future = promise->get_future();
    redis->execCommandAsync(
        [promise](const drogon::nosql::RedisResult& r) {
            // BLPOP replies with a 2-element array [key, value] on success, nil on timeout.
            if (r.type() == drogon::nosql::RedisResultType::kNil) {
                promise->set_value(std::nullopt);
            } else {
                promise->set_value(r.asArray()[1].asString());
            }
        },
        [promise](const drogon::nosql::RedisException&) { promise->set_value(std::nullopt); },
        "BLPOP %s %d", kJobQueueKey.c_str(), timeout_seconds);
    return future.get();
}

}  // namespace pareto_nbd
