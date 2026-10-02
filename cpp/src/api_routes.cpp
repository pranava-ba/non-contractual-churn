#include "pareto_nbd/api_routes.hpp"

#include <charconv>
#include <cstdint>
#include <regex>
#include <string>
#include <string_view>
#include <vector>

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

// Escapes one free-text CSV field (customer_id, data_quality) for /jobs/{id}/export.csv.
//
// 1. Formula-injection guard (OWASP "CSV Injection" mitigation): a field starting with '=',
//    '+', '-', '@', TAB or CR is interpreted as a formula by Excel/LibreOffice/Sheets when the
//    export is opened, so it is prefixed with a single quote, which those tools treat as
//    "this cell is text". Trade-off: a legitimate customer id like "-123" exports as "'-123"
//    -- the standard, accepted cost of this mitigation. Applied ONLY to free-text fields,
//    never to the numeric columns (a negative number there is data, not a formula, and they
//    are produced by FormatDouble below, never from user input).
// 2. RFC 4180 quoting: a field containing a comma, double quote, CR or LF is wrapped in
//    double quotes with each embedded double quote doubled.
std::string EscapeCsvField(std::string_view field) {
    std::string out;
    out.reserve(field.size() + 3);
    if (!field.empty() && (field[0] == '=' || field[0] == '+' || field[0] == '-' ||
                           field[0] == '@' || field[0] == '\t' || field[0] == '\r')) {
        out.push_back('\'');
    }
    out.append(field);
    if (out.find_first_of(",\"\r\n") == std::string::npos) {
        return out;
    }
    std::string quoted;
    quoted.reserve(out.size() + 2);
    quoted.push_back('"');
    for (char c : out) {
        if (c == '"') quoted.push_back('"');
        quoted.push_back(c);
    }
    quoted.push_back('"');
    return quoted;
}

// Formats a double for the CSV export with std::to_chars's shortest round-trip
// representation (C++17 <charconv>, supported by this project's MSVC/C++20 toolchain): the
// shortest decimal string that parses back to the exact same double. Chosen over
// std::setprecision(17), which is also round-trip-safe but prints noise digits for values
// that aren't exactly representable (1477186.37 -> "1477186.3700000001"), and over the
// default ostream precision (6 significant digits), which silently truncated real CLV
// values (1477186.37 -> "1.47719e+06").
std::string FormatDouble(double value) {
    char buf[64];
    auto [ptr, ec] = std::to_chars(buf, buf + sizeof(buf), value);
    if (ec != std::errc()) {
        return "0";  // unreachable for a 64-byte buffer; never emit garbage if it ever is
    }
    return std::string(buf, ptr);
}

// Builds {"edges": [...], "counts": [...]} for one forecast_results column of one job.
// `column` and `quality_clause` are TRUSTED string literals supplied by this file's own call
// sites below -- never request data -- so concatenating them into the SQL is safe; the job id
// and numeric parameters are always bound. Bin edges run from 0 to `hi`; width_bucket returns
// bucket `bins + 1` for a value exactly equal to `hi`, so the result is clamped into
// [1, bins] (otherwise the maximum value would silently fall out of the chart).
// $2::float8 / $3::int casts are required, same wire-format reason as /results's LIMIT/OFFSET.
nlohmann::json BuildHistogram(const drogon::orm::DbClientPtr& db, const std::string& job_id,
                              const std::string& column, const std::string& quality_clause,
                              int bins, const double* fixed_hi) {
    double hi = 1.0;
    if (fixed_hi != nullptr) {
        hi = *fixed_hi;
    } else {
        auto max_rows = db->execSqlSync(
            "SELECT COALESCE(max(fr." + column + "), 0)::float8 AS m FROM forecast_results fr "
            "WHERE fr.job_id = $1::uuid AND " + quality_clause,
            job_id);
        hi = max_rows[0]["m"].as<double>();
        if (!(hi > 0.0)) hi = 1.0;  // empty or all-zero column: any positive range will do
    }

    auto rows = db->execSqlSync(
        "SELECT LEAST(GREATEST(width_bucket(fr." + column +
            ", 0::float8, $2::float8, $3::int), 1), $3::int) AS b, count(*)::bigint AS n "
        "FROM forecast_results fr WHERE fr.job_id = $1::uuid AND " + quality_clause +
            " GROUP BY b ORDER BY b",
        job_id, hi, bins);

    std::vector<int64_t> counts(static_cast<size_t>(bins), 0);
    for (const auto& row : rows) {
        counts[static_cast<size_t>(row["b"].as<int>() - 1)] = row["n"].as<int64_t>();
    }
    std::vector<double> edges;
    for (int i = 0; i <= bins; ++i) edges.push_back(hi * i / bins);
    return {{"edges", edges}, {"counts", counts}};
}

}  // namespace

void RegisterApiRoutes(std::shared_ptr<UploadStorage> storage,
                        drogon::orm::DbClientPtr db,
                        drogon::nosql::RedisClientPtr redis,
                        const std::string& queue_key) {
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
        [storage, db, redis, queue_key](
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

            // If the push to Redis fails, no worker will ever see this job: returning 200 with
            // a job_id here would hand the client an id that stays 'queued' forever. Instead
            // mark the already-inserted row failed (so GET /jobs/{id} tells the truth if the
            // id is ever looked up) and tell the client to retry with a 503.
            if (!pareto_nbd::EnqueueJob(redis, job_id, queue_key)) {
                db->execSqlSync(
                    "UPDATE jobs SET status = 'failed', error_reason = $2, completed_at = now() "
                    "WHERE id = $1::uuid",
                    job_id,
                    std::string("could not enqueue job for processing (queue unavailable)"));
                // job_id is still returned so the client can reference the failed job
                // (GET /jobs/{id} reports it as 'failed' with this reason).
                callback(JsonResponse(
                    {{"error", "job queue unavailable, please retry"}, {"job_id", job_id}},
                    drogon::k503ServiceUnavailable));
                return;
            }

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
                "fr.clv_point, fr.clv_lower, fr.clv_upper, fr.data_quality "
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
                    // Per spec Sec6, every row carries its data-quality flag: 'ok',
                    // 'insufficient_history', 'forecast_unavailable' (numbers are 0.0
                    // placeholders) or 'clv_unavailable' (clv_* are 0.0 placeholders).
                    // Without it a placeholder row is indistinguishable from a real
                    // p_alive=0 churn prediction.
                    {"data_quality", row["data_quality"].as<std::string>()},
                });
            }
            nlohmann::json body{{"job_id", id}, {"page", page}, {"page_size", page_size},
                                 {"total", total}, {"customers", customers}};
            callback(JsonResponse(body, drogon::k200OK));
        },
        {drogon::Get});

    // GET /jobs/{id}/summary: cohort-level aggregates and histograms for the dashboard (Phase 5
    // frontend). Computed in SQL so the browser never has to download every customer row.
    // Same id validation and 404-until-done gate as /results. Placeholder rows (see
    // data_quality in worker.cpp) are excluded from every statistic they would corrupt:
    // forecast statistics use ok + insufficient_history rows, CLV statistics use ok rows only.
    drogon::app().registerHandler(
        "/jobs/{id}/summary",
        [db](const drogon::HttpRequestPtr&,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(
                    JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }
            auto job_rows = db->execSqlSync("SELECT status FROM jobs WHERE id = $1::uuid", id);
            if (job_rows.empty() || job_rows[0]["status"].as<std::string>() != "done") {
                callback(
                    JsonResponse({{"error", "job not found or not done"}}, drogon::k404NotFound));
                return;
            }

            const std::string kValidForecast =
                "fr.data_quality IN ('ok','insufficient_history')";
            const std::string kValidClv = "fr.data_quality = 'ok'";

            auto agg = db->execSqlSync(
                "SELECT count(*)::bigint AS n, "
                "COALESCE(avg(fr.p_alive) FILTER (WHERE " + kValidForecast + "), 0)::float8 AS mean_p, "
                "COALESCE(sum(fr.expected_purchases) FILTER (WHERE " + kValidForecast + "), 0)::float8 AS sum_ep, "
                "COALESCE(sum(fr.clv_point) FILTER (WHERE " + kValidClv + "), 0)::float8 AS sum_clv, "
                "COALESCE(bool_or(fr.clv_upper > fr.clv_lower), false) AS has_interval "
                "FROM forecast_results fr WHERE fr.job_id = $1::uuid",
                id);

            nlohmann::json quality_counts = nlohmann::json::object();
            auto q_rows = db->execSqlSync(
                "SELECT data_quality, count(*)::bigint AS n FROM forecast_results "
                "WHERE job_id = $1::uuid GROUP BY data_quality",
                id);
            for (const auto& row : q_rows) {
                quality_counts[row["data_quality"].as<std::string>()] = row["n"].as<int64_t>();
            }

            const double p_alive_hi = 1.0;
            nlohmann::json body{
                {"job_id", id},
                {"n_customers", agg[0]["n"].as<int64_t>()},
                {"quality_counts", quality_counts},
                {"mean_p_alive", agg[0]["mean_p"].as<double>()},
                {"total_expected_purchases", agg[0]["sum_ep"].as<double>()},
                {"total_clv", agg[0]["sum_clv"].as<double>()},
                {"has_clv_interval", agg[0]["has_interval"].as<bool>()},
                {"histograms",
                 {{"p_alive", BuildHistogram(db, id, "p_alive", kValidForecast, 10, &p_alive_hi)},
                  {"expected_purchases",
                   BuildHistogram(db, id, "expected_purchases", kValidForecast, 20, nullptr)},
                  {"clv_point", BuildHistogram(db, id, "clv_point", kValidClv, 20, nullptr)}}}};
            callback(JsonResponse(body, drogon::k200OK));
        },
        {drogon::Get});

    // GET /jobs/{id}/export.csv: the full (unpaginated) forecast_results for a job as CSV.
    // Same id-into-::uuid-cast pattern as /jobs/{id} and /jobs/{id}/results above, so the same
    // format check runs first, and the same job-status gate as /jobs/{id}/results: an unknown
    // or not-yet-'done' job is a 404, never a 200 with a header-only (or, for a job that
    // failed partway through writing forecast_results, a silently partial) CSV.
    //
    // Columns: customer_id, the five numeric forecast columns, and data_quality (spec Sec6's
    // per-row flag -- see /jobs/{id}/results). Free-text fields go through EscapeCsvField
    // (RFC 4180 quoting + formula-injection guard); numeric fields through FormatDouble
    // (shortest round-trip, no precision loss).
    drogon::app().registerHandler(
        "/jobs/{id}/export.csv",
        [db](const drogon::HttpRequestPtr&,
             std::function<void(const drogon::HttpResponsePtr&)>&& callback,
             const std::string& id) {
            if (!IsValidUuidFormat(id)) {
                callback(
                    JsonResponse({{"error", "invalid job id format"}}, drogon::k400BadRequest));
                return;
            }

            auto job_rows = db->execSqlSync("SELECT status FROM jobs WHERE id = $1::uuid", id);
            if (job_rows.empty() || job_rows[0]["status"].as<std::string>() != "done") {
                callback(
                    JsonResponse({{"error", "job not found or not done"}}, drogon::k404NotFound));
                return;
            }

            auto rows = db->execSqlSync(
                "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, "
                "fr.clv_point, fr.clv_lower, fr.clv_upper, fr.data_quality "
                "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
                "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id",
                id);

            std::string csv =
                "customer_id,expected_purchases,p_alive,clv_point,clv_lower,clv_upper,"
                "data_quality\n";
            for (const auto& row : rows) {
                csv += EscapeCsvField(row["external_customer_id"].as<std::string>());
                for (const char* col :
                     {"expected_purchases", "p_alive", "clv_point", "clv_lower", "clv_upper"}) {
                    csv += ',';
                    csv += FormatDouble(row[col].as<double>());
                }
                csv += ',';
                csv += EscapeCsvField(row["data_quality"].as<std::string>());
                csv += '\n';
            }

            // Drogon's drogon::ContentType enum (CT_*) has no built-in CSV entry -- the closest
            // is CT_TEXT_PLAIN/CT_APPLICATION_OCTET_STREAM, neither of which is "text/csv".
            // setContentTypeString (NOT addHeader("Content-Type", ...)) is required here:
            // HttpResponseImpl::makeHeaderString always writes its own
            // "content-type: <contentTypeString_>" line (defaulting to "text/html;
            // charset=utf-8") ahead of the generic headers_ map, so addHeader("Content-Type",
            // ...) would just add a SECOND, duplicate content-type header rather than replacing
            // the default -- confirmed by reading HttpResponseImpl.cc's makeHeaderString/
            // setContentTypeString. setContentTypeString updates that same contentTypeString_
            // field directly, so only one content-type header is ever emitted. (The response
            // status already defaults to 200.)
            auto resp = drogon::HttpResponse::newHttpResponse();
            resp->setContentTypeString("text/csv");
            resp->setBody(std::move(csv));
            callback(resp);
        },
        {drogon::Get});
}

}  // namespace pareto_nbd
