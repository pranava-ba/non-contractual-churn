#pragma once
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace pareto_nbd {

// Thrown for a malformed/empty CSV or a missing required column. Messages
// are written to be user-facing (surfaced by the future upload-validation
// API, per the spec's §6 error handling), not raw parser internals.
class IngestError : public std::runtime_error {
public:
    explicit IngestError(const std::string& msg) : std::runtime_error(msg) {}
};

// Per-customer BTYD + monetary features computed from a raw transaction-log
// CSV. Parallel arrays, one entry per customer, in no particular order.
// m_bar is empty (and has_monetary is false) when the CSV has no "amount"
// column -- the CLV stage (cpp/include/pareto_nbd/clv.hpp) is simply not
// run for a cohort ingested this way.
struct CustomerFeatures {
    std::vector<std::string> customer_id;
    std::vector<double> x;
    std::vector<double> t_x;
    std::vector<double> T_cal;
    std::vector<double> m_bar;
    bool has_monetary = false;
};

// Reads a transaction-log CSV (required columns: "customer_id",
// "transaction_date"; optional: "amount") and computes per-customer
// features as of as_of_iso_date (format "YYYY-MM-DD"), or the log's own max
// transaction date if not given. Mirrors src/ingest.py's
// elog_to_features exactly (see that module's docstring for the semantics).
// Throws IngestError on a missing required column or an empty file.
CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date = std::nullopt);

}  // namespace pareto_nbd
