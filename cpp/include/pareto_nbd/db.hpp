#pragma once
#include <drogon/orm/DbClient.h>
#include <string>

namespace pareto_nbd {

// Local dev connection string, matching docker-compose.yml's postgres service (Task 1).
// Production wiring (env-var override) is a Phase-4-hardening concern, not this plan's.
inline const std::string kTestConnString =
    "host=127.0.0.1 port=5432 dbname=pareto_nbd user=pareto_nbd password=pareto_nbd_dev";

inline const std::string kDefaultBusinessId = "00000000-0000-0000-0000-000000000001";

// Connects synchronously (a short-timeout attempt) so callers can detect "Postgres isn't
// running" up front and SKIP their test, rather than hanging on Drogon's async retry loop.
// Returns nullptr on failure instead of throwing -- this is a reachability probe, not a
// runtime connection (the returned DbClientPtr, once obtained, is used for real async calls).
drogon::orm::DbClientPtr ConnectDb(const std::string& conn_str);

// Splits schema_sql_path's content on ';' and executes each non-empty statement in order.
// A hand-rolled splitter is adequate for this project's own schema.sql (no stored
// procedures, no semicolons inside string literals) -- do not generalize it into a real SQL
// parser.
void ApplySchema(drogon::orm::DbClientPtr db, const std::string& schema_sql_path);

}  // namespace pareto_nbd
