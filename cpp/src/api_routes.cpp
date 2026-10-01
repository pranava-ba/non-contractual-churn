#include "pareto_nbd/api_routes.hpp"

#include <regex>
#include <string>

#include "pareto_nbd/ingest.hpp"

namespace pareto_nbd {

// Drogon's HttpResponse::newHttpJsonResponse(...) takes a JsonCpp Json::Value, a different
// JSON library from the nlohmann::json this project uses everywhere else (ingest.cpp,
// tests). Building the response this way -- a plain string body with the JSON content type
// set explicitly -- keeps every handler on one JSON library instead of mixing two.
drogon::HttpResponsePtr JsonResponse(const nlohmann::json& body, drogon::HttpStatusCode code) {
    auto resp = drogon::HttpResponse::newHttpResponse();
    resp->setStatusCode(code);
    resp->setContentTypeCode(drogon::CT_APPLICATION_JSON);
    resp->setBody(body.dump());
    return resp;
}

namespace {

// Validates that `id` is syntactically a UUID (standard 8-4-4-4-12 hex format with dashes)
// BEFORE it ever reaches a `::uuid`-cast SQL query. /jobs/{id} is the first route in this
// codebase to pass a user-controlled path parameter into such a cast (see /uploads's
// business_id cast, which uses a hardcoded constant, never user input) -- an id that isn't a
// syntactically valid UUID makes Postgres's cast throw, uncaught, inside the handler. Both
// /jobs/{id} and /jobs/{id}/results share this same user-controlled-id-into-::uuid-cast
// pattern, so both call this helper first and return a clean 400 instead.
bool IsValidUuidFormat(const std::string& id) {
    static const std::regex kUuidRegex(
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$");
    return std::regex_match(id, kUuidRegex);
}

}  // namespace

void RegisterApiRoutes(std::shared_ptr<UploadStorage> storage,
                        drogon::orm::DbClientPtr db,
                        drogon::nosql::RedisClientPtr redis) {
    drogon::app().registerHandler(
        "/healthz",
        [](const drogon::HttpRequestPtr&,
           std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setBody("ok");
            callback(resp);
        },
        {drogon::Get});

    // POST /uploads: the entire request body IS the raw CSV file (no multipart/form-data
    // parsing in this MVP -- that's a Phase-5 frontend-integration concern if the browser's
    // file input ever needs it, not blocking this endpoint's core logic).
    //
    // Flow: validate synchronously via ingest_csv's LoadRawTable path so a bad upload never
    // even reaches the job queue (spec Sec6) -> store the raw bytes under a fresh
    // server-generated key (never derived from the request body or any client-supplied
    // header -- Task 3's review flagged path-traversal risk in UploadStorage if a key were
    // ever attacker-influenced, and this handler is the first real caller of storage->Put)
    // -> insert a `jobs` row (status='queued') -> enqueue the job id in Redis for the worker
    // (Task 6) to pick up -> return the job id.
    //
    // ingest_csv is deliberately called twice across this phase's full flow -- once here
    // (validation only, result discarded) and once for real in the worker. Parsing a CSV is
    // cheap relative to the AmortizedModel/Gamma-Gamma stages, and keeping validation
    // synchronous in the request path matters more than saving one parse pass.
    drogon::app().registerHandler(
        "/uploads",
        [storage, db, redis](
            const drogon::HttpRequestPtr& req,
            std::function<void(const drogon::HttpResponsePtr&)>&& callback) {
            std::string body(req->getBody());
            if (body.empty()) {
                callback(
                    JsonResponse({{"error", "empty request body"}}, drogon::k400BadRequest));
                return;
            }

            // Server-generated key -- the only caller-controlled input is the raw CSV bytes
            // stored *at* this key, never the key itself.
            std::string key = "uploads/" + drogon::utils::getUuid() + ".csv";
            storage->Put(key, body);

            try {
                pareto_nbd::ingest_csv(storage->GetPath(key));
            } catch (const pareto_nbd::IngestError& e) {
                callback(JsonResponse({{"error", std::string(e.what())}},
                                       drogon::k400BadRequest));
                return;
            }

            auto rows = db->execSqlSync(
                "INSERT INTO jobs (business_id, status, upload_path) "
                "VALUES ($1::uuid, 'queued', $2) RETURNING id",
                pareto_nbd::kDefaultBusinessId, key);
            std::string job_id = rows[0]["id"].as<std::string>();

            pareto_nbd::EnqueueJob(redis, job_id);

            callback(JsonResponse({{"job_id", job_id}}, drogon::k200OK));
        },
        {drogon::Post});

    // GET /jobs/{id}: status lookup for a previously-created job. `{id}` is a Drogon
    // path-parameter placeholder -- any non-numeric name in braces binds positionally to the
    // handler's trailing parameter (here, the id itself; see HttpControllersRouter::addHttpPath
    // in the Drogon sources -- a bare name like `{id}` isn't looked up by name, it just has to
    // be the first/only placeholder to line up with this handler's one trailing std::string).
    drogon::app().registerHandler(
        "/jobs/{id}",
        [db](const drogon::HttpRequestPtr&,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(
                    JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }
            auto rows = db->execSqlSync(
                "SELECT status, error_reason FROM jobs WHERE id = $1::uuid", id);
            if (rows.empty()) {
                callback(JsonResponse({{"error", "job not found"}}, drogon::k404NotFound));
                return;
            }
            nlohmann::json body{{"id", id}, {"status", rows[0]["status"].as<std::string>()}};
            body["error_reason"] = rows[0]["error_reason"].isNull()
                                        ? nlohmann::json(nullptr)
                                        : nlohmann::json(rows[0]["error_reason"].as<std::string>());
            callback(JsonResponse(body, drogon::k200OK));
        },
        {drogon::Get});

    // GET /jobs/{id}/results: paginated per-customer forecasts for a completed job. Same
    // id-into-::uuid-cast pattern as /jobs/{id} above, so the same format check runs first.
    // Per spec Sec4.2's documented polling flow, a client calls GET /jobs/{id} first to learn
    // a job is 'done' before ever calling this endpoint -- so this route collapses "unknown
    // job id" and "job exists but isn't done yet (queued/running/failed, no results to page
    // through)" into the same 404, distinguishable only via that prior /jobs/{id} call.
    drogon::app().registerHandler(
        "/jobs/{id}/results",
        [db](const drogon::HttpRequestPtr& req,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(
                    JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }

            int page = 1;
            int page_size = 50;
            if (auto p = req->getParameter("page"); !p.empty()) {
                try {
                    page = std::stoi(p);
                } catch (const std::exception&) {
                    page = 1;
                }
            }
            if (auto ps = req->getParameter("page_size"); !ps.empty()) {
                try {
                    page_size = std::stoi(ps);
                } catch (const std::exception&) {
                    page_size = 50;
                }
            }
            if (page < 1) page = 1;
            if (page_size < 1) page_size = 50;

            auto job_rows = db->execSqlSync("SELECT status FROM jobs WHERE id = $1::uuid", id);
            if (job_rows.empty() || job_rows[0]["status"].as<std::string>() != "done") {
                callback(
                    JsonResponse({{"error", "job not found or not done"}}, drogon::k404NotFound));
                return;
            }

            auto count_rows = db->execSqlSync(
                "SELECT count(*) FROM forecast_results WHERE job_id = $1::uuid", id);
            int64_t total = count_rows[0]["count"].as<int64_t>();

            // $2/$3 are cast explicitly: LIMIT/OFFSET default to Postgres's `bigint`, but the
            // wire-protocol parameter drogon sends for a C++ `int` is a 4-byte int32 -- left
            // uncast, that byte-count mismatch makes libpq fail to parse the bound message
            // ("insufficient data left in message... parameter $2"), caught empirically while
            // testing this route with a real page_size.
            auto rows = db->execSqlSync(
                "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, "
                "fr.clv_point, fr.clv_lower, fr.clv_upper "
                "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
                "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id "
                "LIMIT $2::int OFFSET $3::int",
                id, page_size, (page - 1) * page_size);

            nlohmann::json customers = nlohmann::json::array();
            for (const auto& row : rows) {
                customers.push_back({
                    {"customer_id", row["external_customer_id"].as<std::string>()},
                    {"expected_purchases", row["expected_purchases"].as<double>()},
                    {"p_alive", row["p_alive"].as<double>()},
                    {"clv_point", row["clv_point"].as<double>()},
                    {"clv_lower", row["clv_lower"].as<double>()},
                    {"clv_upper", row["clv_upper"].as<double>()},
                });
            }
            nlohmann::json body{{"job_id", id}, {"page", page}, {"page_size", page_size},
                                 {"total", total}, {"customers", customers}};
            callback(JsonResponse(body, drogon::k200OK));
        },
        {drogon::Get});
}

}  // namespace pareto_nbd
