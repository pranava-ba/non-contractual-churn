#include <catch2/catch_test_macros.hpp>
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
