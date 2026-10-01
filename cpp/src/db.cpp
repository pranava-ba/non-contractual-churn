#include "pareto_nbd/db.hpp"

#include <chrono>
#include <fstream>
#include <future>
#include <sstream>
#include <stdexcept>
#include <thread>

namespace pareto_nbd {

drogon::orm::DbClientPtr ConnectDb(const std::string& conn_str, size_t pool_size) {
    try {
        auto db = drogon::orm::DbClient::newPgClient(conn_str, pool_size == 0 ? 1 : pool_size);
        // newPgClient connects asynchronously; force a real round trip with a short
        // deadline so an unreachable Postgres fails fast instead of hanging.
        auto promise = std::make_shared<std::promise<bool>>();
        auto future = promise->get_future();
        db->execSqlAsync(
            "SELECT 1",
            [promise](const drogon::orm::Result&) { promise->set_value(true); },
            [promise](const drogon::orm::DrogonDbException&) { promise->set_value(false); });
        if (future.wait_for(std::chrono::seconds(2)) != std::future_status::ready ||
            !future.get()) {
            return nullptr;
        }
        return db;
    } catch (...) {
        return nullptr;
    }
}

void ApplySchema(drogon::orm::DbClientPtr db, const std::string& schema_sql_path) {
    std::ifstream f(schema_sql_path);
    if (!f) {
        throw std::runtime_error("ApplySchema: cannot open schema file '" + schema_sql_path + "'");
    }
    std::stringstream buf;
    buf << f.rdbuf();
    std::string sql = buf.str();

    size_t start = 0;
    while (start < sql.size()) {
        size_t end = sql.find(';', start);
        if (end == std::string::npos) break;
        std::string stmt = sql.substr(start, end - start);
        // skip whitespace-only/comment-only fragments between real statements
        if (stmt.find_first_not_of(" \t\r\n") != std::string::npos) {
            db->execSqlSync(stmt);
        }
        start = end + 1;
    }
}

}  // namespace pareto_nbd
