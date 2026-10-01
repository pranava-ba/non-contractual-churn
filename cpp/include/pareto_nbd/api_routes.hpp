#pragma once
#include <drogon/drogon.h>
#include <nlohmann/json.hpp>

#include <memory>

#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

namespace pareto_nbd {

// Builds a Drogon JSON response from an nlohmann::json body (this project uses nlohmann
// everywhere else; Drogon's own newHttpJsonResponse expects JsonCpp, a different library).
drogon::HttpResponsePtr JsonResponse(const nlohmann::json& body, drogon::HttpStatusCode code);

// Registers every API route (/healthz, /uploads, and any added by later tasks) onto
// drogon::app(). Called exactly once per process by api_main.cpp's main(), and exactly
// once per test binary by the shared test server fixture -- never call this twice against
// the same drogon::app() instance. queue_key is the Redis list POST /uploads pushes job ids
// onto: production (api_main.cpp) uses the default kJobQueueKey -- the key the real `worker`
// consumes -- while the test fixture passes kTestJobQueueKey so test runs never interfere
// with a live worker process.
void RegisterApiRoutes(std::shared_ptr<UploadStorage> storage,
                        drogon::orm::DbClientPtr db,
                        drogon::nosql::RedisClientPtr redis,
                        const std::string& queue_key = kJobQueueKey);

}  // namespace pareto_nbd
