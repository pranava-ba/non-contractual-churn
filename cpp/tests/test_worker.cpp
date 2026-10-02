#include <catch2/catch_test_macros.hpp>
#include <cstdlib>

#include <cmath>
#include <string>
#include <vector>

#include "pareto_nbd/clv.hpp"
#include "pareto_nbd/db.hpp"
#include "pareto_nbd/forecast.hpp"
#include "pareto_nbd/storage.hpp"
#include "pareto_nbd/worker.hpp"

TEST_CASE("ProcessOneJob ingests, forecasts, and writes results for a queued job", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    std::string key = "uploads/test-job.csv";
    storage.Put(key, "customer_id,transaction_date,amount\n"
                      "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
                      "B,2024-01-01,3.0\n"
                      "C,2024-01-15,20.0\nC,2024-01-29,6.0\n");

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', $2) RETURNING id",
        pareto_nbd::kDefaultBusinessId, key);
    std::string job_id = rows[0]["id"].as<std::string>();

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto job_rows = db->execSqlSync("SELECT status, error_reason FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(job_rows[0]["status"].as<std::string>() == "done");
    REQUIRE(job_rows[0]["error_reason"].isNull());

    auto result_rows = db->execSqlSync(
        "SELECT fr.expected_purchases, fr.p_alive, fr.clv_point, c.external_customer_id "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", job_id);
    REQUIRE(result_rows.size() == 3);  // A, B, C
    for (const auto& row : result_rows) {
        REQUIRE(row["expected_purchases"].as<double>() >= 0.0);
        double p_alive = row["p_alive"].as<double>();
        REQUIRE(p_alive >= 0.0);
        REQUIRE(p_alive <= 1.0);
    }
}

TEST_CASE("ProcessOneJob marks a job failed (not a crash) on a malformed CSV", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    std::string key = "uploads/test-job-bad.csv";
    storage.Put(key, "customer_id,amount\nA,10.0\n");  // missing transaction_date

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', $2) RETURNING id",
        pareto_nbd::kDefaultBusinessId, key);
    std::string job_id = rows[0]["id"].as<std::string>();

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto job_rows = db->execSqlSync("SELECT status, error_reason FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(job_rows[0]["status"].as<std::string>() == "failed");
    REQUIRE_FALSE(job_rows[0]["error_reason"].isNull());
}

TEST_CASE("ScoreCohortAndWriteResults skips an overflow-triggering customer without failing "
          "the rest of the cohort",
          "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    // Exact (r, alpha, s, beta) from models/forecast_golden.json's known
    // "C++ limitation: alpha/beta=1e-8, x=0 -> ForecastOverflowError" case: alpha/beta is
    // extreme enough that an x=0, t_x=0 customer overflows the fast series path. The worker
    // doesn't get to pick AmortizedModel's predicted (r, alpha, s, beta) for a crafted CSV,
    // so this test calls ScoreCohortAndWriteResults directly with this cohort-level
    // (population) parameter set, exactly as ProcessOneJob would after AmortizedModel::predict
    // happened to return it.
    const pareto_nbd::ParetoNbdParams overflow_params{0.7, 1e-6, 0.6, 100.0};

    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', 'uploads/unused.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = rows[0]["id"].as<std::string>();

    pareto_nbd::CustomerFeatures cohort;
    cohort.has_monetary = false;
    // "Overflow": x=0, t_x=0 -- the exact golden-case combination that throws
    // ForecastOverflowError for overflow_params.
    cohort.customer_id = {"overflow-cust", "normal-cust-1", "normal-cust-2"};
    cohort.x = {0.0, 5.0, 2.0};
    cohort.t_x = {0.0, 25.0, 29.0};
    cohort.T_cal = {30.0, 30.0, 30.0};

    // Sanity-check the test's own premise before exercising the worker code: at t_x=0 this
    // params/x=0 combination really does overflow, and the other two customers' (t_x, T)
    // combinations really do not (same params, just far from the t_x=0 edge case).
    REQUIRE(pareto_nbd::WouldOverflow(overflow_params, 0.0));
    REQUIRE_THROWS_AS(pareto_nbd::p_alive(overflow_params, 0.0, 0.0, 30.0),
                      pareto_nbd::ForecastOverflowError);
    REQUIRE_NOTHROW(pareto_nbd::p_alive(overflow_params, 5.0, 25.0, 30.0));
    REQUIRE_NOTHROW(pareto_nbd::p_alive(overflow_params, 2.0, 29.0, 30.0));

    pareto_nbd::ScoreCohortAndWriteResults(job_id, db, cohort, overflow_params);

    auto result_rows = db->execSqlSync(
        "SELECT c.external_customer_id, fr.expected_purchases, fr.p_alive, fr.data_quality "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", job_id);

    // Every customer in the cohort gets exactly one row now (Task 10): the overflow
    // customer is no longer silently omitted, it gets a 'forecast_unavailable' row with
    // placeholder 0.0 figures, while the two non-overflowing customers score normally.
    REQUIRE(result_rows.size() == 3);
    for (const auto& row : result_rows) {
        std::string ext_id = row["external_customer_id"].as<std::string>();
        if (ext_id == "overflow-cust") {
            REQUIRE(row["data_quality"].as<std::string>() == "forecast_unavailable");
            REQUIRE(row["expected_purchases"].as<double>() == 0.0);
            REQUIRE(row["p_alive"].as<double>() == 0.0);
        } else {
            REQUIRE(row["data_quality"].as<std::string>() == "ok");
            REQUIRE(row["p_alive"].as<double>() >= 0.0);
            REQUIRE(row["p_alive"].as<double>() <= 1.0);
        }
    }

    // The customer row itself is still created for the overflow customer too.
    auto cust_rows = db->execSqlSync(
        "SELECT external_customer_id FROM customers WHERE business_id = $1::uuid "
        "AND external_customer_id = 'overflow-cust'",
        pareto_nbd::kDefaultBusinessId);
    REQUIRE(cust_rows.size() == 1);
}

TEST_CASE("ProcessOneJob flags single-transaction customers as insufficient_history", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads2");
    storage.Put("uploads/thin.csv",
                "customer_id,transaction_date,amount\n"
                "A,2024-01-01,10.0\nA,2024-01-08,5.0\n"  // A has repeats: sufficient
                "B,2024-01-01,3.0\n");                    // B: single transaction, x=0

    auto job_rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) VALUES ($1::uuid, 'queued', 'uploads/thin.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = job_rows[0]["id"].as<std::string>();

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto rows = db->execSqlSync(
        "SELECT c.external_customer_id, fr.data_quality "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid ORDER BY c.external_customer_id", job_id);
    REQUIRE(rows.size() == 2);
    REQUIRE(rows[0]["external_customer_id"].as<std::string>() == "A");
    REQUIRE(rows[0]["data_quality"].as<std::string>() == "ok");
    REQUIRE(rows[1]["external_customer_id"].as<std::string>() == "B");
    REQUIRE(rows[1]["data_quality"].as<std::string>() == "insufficient_history");
}

TEST_CASE("ScoreCohortAndWriteResults never writes a NaN CLV: a degenerate Gamma-Gamma fit "
          "flags 'clv_unavailable' with 0.0 placeholders",
          "[worker][clv]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    // 20 single-repeat (x=1) customers whose mean spends span ~7 orders of magnitude (the
    // 2.5%..97.5% quantiles of the Gamma-Gamma marginal for p=0.3, q=0.4), plus one x=4
    // customer and one x=0 customer. Spend this dispersed drives fit_gamma_gamma to p+q < 1
    // (verified below), so posterior_mean_nu's Inverse-Gamma shape p*x+q is <= 1 -- i.e. NaN
    // -- for every x=1 customer (and q <= 1 makes it NaN for the x=0 one too), while the x=4
    // customer's shape 4p+q > 1 keeps a finite CLV.
    const std::vector<double> spends = {0.01,   0.07,   0.41,   1.26,    2.93,    5.8,      10.36,
                                        17.26,  27.44,  42.35,  64.28,   97.14,   147.96,   230.37,
                                        373.45, 647.51, 1256.0, 2977.7, 10806.83, 169190.2};
    pareto_nbd::CustomerFeatures cohort;
    cohort.has_monetary = true;
    for (size_t i = 0; i < spends.size(); ++i) {
        cohort.customer_id.push_back("nan-clv-x1-" + std::to_string(i));
        cohort.x.push_back(1.0);
        cohort.t_x.push_back(10.0);
        cohort.T_cal.push_back(30.0);
        cohort.m_bar.push_back(spends[i]);
    }
    cohort.customer_id.push_back("nan-clv-x4");
    cohort.x.push_back(4.0);
    cohort.t_x.push_back(25.0);
    cohort.T_cal.push_back(30.0);
    cohort.m_bar.push_back(50.0);
    cohort.customer_id.push_back("nan-clv-x0");
    cohort.x.push_back(0.0);
    cohort.t_x.push_back(0.0);
    cohort.T_cal.push_back(30.0);
    cohort.m_bar.push_back(0.0);

    // Premise checks -- on the real C++ fit, not an assumption carried over from Python.
    const auto gg = pareto_nbd::fit_gamma_gamma(cohort.x, cohort.m_bar);
    INFO("fitted p=" << gg.p << " q=" << gg.q << " v=" << gg.v);
    REQUIRE(gg.p + gg.q <= 1.0);
    REQUIRE(gg.q <= 1.0);
    REQUIRE(4.0 * gg.p + gg.q > 1.0);
    const auto nu = pareto_nbd::posterior_mean_nu(cohort.x, cohort.m_bar, gg);
    REQUIRE(std::isnan(nu[0]));
    REQUIRE(std::isfinite(nu[spends.size()]));  // the x=4 customer

    // Ordinary, non-overflowing population parameters so every customer scores (the CLV
    // path is what's under test here, not the forecast path).
    const pareto_nbd::ParetoNbdParams params{0.7, 10.0, 0.6, 10.0};
    REQUIRE_FALSE(pareto_nbd::WouldOverflow(params, 0.0));

    // These fixed external ids are upserted by the worker (ON CONFLICT DO UPDATE on
    // customers), and forecast_results rows are keyed by this run's fresh job_id, so reruns
    // never collide.
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', 'uploads/unused.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = rows[0]["id"].as<std::string>();

    pareto_nbd::ScoreCohortAndWriteResults(job_id, db, cohort, params);

    auto result_rows = db->execSqlSync(
        "SELECT c.external_customer_id, fr.clv_point, fr.clv_lower, fr.clv_upper, "
        "fr.p_alive, fr.data_quality, "
        "(fr.clv_point = 'NaN'::float8 OR fr.clv_lower = 'NaN'::float8 OR "
        " fr.clv_upper = 'NaN'::float8) AS has_nan "
        "FROM forecast_results fr JOIN customers c ON c.id = fr.customer_id "
        "WHERE fr.job_id = $1::uuid",
        job_id);
    REQUIRE(result_rows.size() == spends.size() + 2);

    size_t clv_unavailable = 0;
    for (const auto& row : result_rows) {
        const std::string ext_id = row["external_customer_id"].as<std::string>();
        const std::string dq = row["data_quality"].as<std::string>();
        INFO("customer " << ext_id << " data_quality=" << dq);
        // No NaN reached the database for anyone (checked on the Postgres side too).
        REQUIRE_FALSE(row["has_nan"].as<bool>());
        REQUIRE(std::isfinite(row["clv_point"].as<double>()));
        REQUIRE(std::isfinite(row["clv_lower"].as<double>()));
        REQUIRE(std::isfinite(row["clv_upper"].as<double>()));

        if (ext_id == "nan-clv-x4") {
            // Finite posterior mean: a real CLV, normal 'ok' row.
            REQUIRE(dq == "ok");
            REQUIRE(row["clv_point"].as<double>() > 0.0);
        } else if (ext_id == "nan-clv-x0") {
            // Also NaN (q <= 1), but 'insufficient_history' is the more specific reason and
            // is kept -- never overwritten by 'clv_unavailable'.
            REQUIRE(dq == "insufficient_history");
            REQUIRE(row["clv_point"].as<double>() == 0.0);
        } else {
            // Would have been 'ok' (x>0, scored): flagged, with 0.0 placeholders, while the
            // forecast itself (p_alive) is still a real figure.
            REQUIRE(dq == "clv_unavailable");
            REQUIRE(row["clv_point"].as<double>() == 0.0);
            REQUIRE(row["clv_lower"].as<double>() == 0.0);
            REQUIRE(row["clv_upper"].as<double>() == 0.0);
            REQUIRE(row["p_alive"].as<double>() > 0.0);
            ++clv_unavailable;
        }
    }
    REQUIRE(clv_unavailable == spends.size());
}

TEST_CASE("ProcessOneJob does not throw for a malformed (non-UUID) job id", "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    // The exact input the final review pushed onto the real queue: previously the very first
    // statement (UPDATE ... WHERE id = 'not-a-uuid'::uuid) threw outside any try/catch, and
    // the exception escaped ProcessOneJob and killed the worker process. Now the whole body is
    // guarded, and the best-effort failure marking (which ALSO throws for this id) is
    // swallowed and logged.
    REQUIRE_NOTHROW(pareto_nbd::ProcessOneJob("not-a-uuid", db, storage));
    // A well-formed id that matches no job is a quiet no-op, too.
    REQUIRE_NOTHROW(
        pareto_nbd::ProcessOneJob("00000000-0000-0000-0000-0000000000ff", db, storage));
}

TEST_CASE("ProcessOneJob marks a job failed (not a crash) when its upload file is missing",
          "[worker]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");

    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path) "
        "VALUES ($1::uuid, 'queued', 'uploads/definitely-does-not-exist.csv') RETURNING id",
        pareto_nbd::kDefaultBusinessId);
    std::string job_id = rows[0]["id"].as<std::string>();

    REQUIRE_NOTHROW(pareto_nbd::ProcessOneJob(job_id, db, storage));

    auto job_rows =
        db->execSqlSync("SELECT status, error_reason FROM jobs WHERE id = $1::uuid", job_id);
    REQUIRE(job_rows[0]["status"].as<std::string>() == "failed");
    REQUIRE_FALSE(job_rows[0]["error_reason"].isNull());
}

namespace {
void SetEnvW(const char* k, const std::string& v) {
#ifdef _WIN32
    _putenv_s(k, v.c_str());
#else
    setenv(k, v.c_str(), 1);
#endif
}
std::string InsertJobWithMode(drogon::orm::DbClientPtr db, const std::string& key,
                              const std::string& mode) {
    auto rows = db->execSqlSync(
        "INSERT INTO jobs (business_id, status, upload_path, fit_mode) "
        "VALUES ($1::uuid, 'queued', $2, $3) RETURNING id",
        pareto_nbd::kDefaultBusinessId, key, mode);
    return rows[0]["id"].as<std::string>();
}
const char* kSmallCsv = "customer_id,transaction_date,amount\n"
                         "A,2024-01-01,10.0\nA,2024-01-08,5.0\nA,2024-01-22,8.0\n"
                         "B,2024-01-01,3.0\nC,2024-01-15,20.0\nC,2024-01-29,6.0\n";
}  // namespace

TEST_CASE("fit_mode=mcmc uses the CLI's parameters and records fit_method", "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    SetEnvW("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/fake_mcmc_cli.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/mcmc-ok.csv", kSmallCsv);
    std::string job_id = InsertJobWithMode(db, "uploads/mcmc-ok.csv", "mcmc");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync(
        "SELECT status, fit_method, fit_note, mcmc_draws_path FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["status"].as<std::string>() == "done");
    if (j[0]["fit_method"].as<std::string>() != "mcmc") { SKIP("python not launchable"); }
    REQUIRE(j[0]["fit_note"].isNull());
    REQUIRE_FALSE(j[0]["mcmc_draws_path"].isNull());
    auto p = db->execSqlSync(
        "SELECT model_params->>'r' AS r FROM forecast_results WHERE job_id=$1::uuid LIMIT 1", job_id);
    REQUIRE(std::stod(p[0]["r"].as<std::string>()) == 0.7);
}

TEST_CASE("fit_mode=mcmc falls back to the amortized fit with a note when the CLI fails",
          "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    SetEnvW("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/mcmc-fail.csv", kSmallCsv);
    std::string job_id = InsertJobWithMode(db, "uploads/mcmc-fail.csv", "mcmc");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync("SELECT status, fit_method, fit_note FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["status"].as<std::string>() == "done");
    REQUIRE(j[0]["fit_method"].as<std::string>() == "amortized");
    REQUIRE(j[0]["fit_note"].as<std::string>().rfind("High-precision refit unavailable", 0) == 0);
}

TEST_CASE("auto on a tiny cohort stays on the fast path without spawning Python",
          "[worker][mcmc]") {
    auto db = pareto_nbd::ConnectDb(pareto_nbd::kTestConnString);
    if (!db) { SKIP("Postgres not reachable"); }
    pareto_nbd::ApplySchema(db, std::string(PROJECT_ROOT_DIR) + "/db/schema.sql");
    // A CLI path that would fail loudly if it were ever invoked.
    SetEnvW("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/cpp/tests/fixtures/does_not_exist.py");
    pareto_nbd::LocalDiskStorage storage("./data/test_worker_uploads");
    storage.Put("uploads/auto-tiny.csv", kSmallCsv);
    std::string job_id = InsertJobWithMode(db, "uploads/auto-tiny.csv", "auto");

    pareto_nbd::ProcessOneJob(job_id, db, storage);

    auto j = db->execSqlSync("SELECT fit_method, fit_note FROM jobs WHERE id=$1::uuid", job_id);
    REQUIRE(j[0]["fit_method"].as<std::string>() == "amortized");
    REQUIRE(j[0]["fit_note"].isNull());
}
