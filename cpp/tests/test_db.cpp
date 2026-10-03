#include <catch2/catch_test_macros.hpp>
#include "pareto_nbd/db.hpp"

TEST_CASE("ConnectDb connects and ApplySchema seeds the default business", "[db]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable at " + pareto_nbd::kTestConnString); }

    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    auto result = db->execSqlSync(
        "SELECT name FROM businesses WHERE id = $1::uuid", pareto_nbd::kDefaultBusinessId);
    REQUIRE(result.size() == 1);
    REQUIRE(result[0]["name"].as<std::string>() == "default");
}
