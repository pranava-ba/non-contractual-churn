#include <drogon/drogon.h>

#include <memory>

#include "pareto_nbd/api_routes.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/queue.hpp"
#include "pareto_nbd/storage.hpp"

int main() {
    auto storage = std::make_shared<pareto_nbd::LocalDiskStorage>("./data/uploads");
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    auto redis = pareto_nbd::ConnectRedis(pareto_nbd::kTestRedisUri);

    pareto_nbd::RegisterApiRoutes(storage, db, redis);

    drogon::app().addListener("0.0.0.0", 8080);
    drogon::app().run();
    return 0;
}
