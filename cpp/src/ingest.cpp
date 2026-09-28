#include "pareto_nbd/ingest.hpp"

#include <algorithm>
#include <arrow/api.h>
#include <arrow/compute/api.h>
#include <arrow/compute/initialize.h>
#include <arrow/csv/api.h>
#include <arrow/io/api.h>
#include <arrow/util/value_parsing.h>  // arrow::TimestampParser (not re-exported by csv/api.h)
#include <cmath>
#include <map>

namespace pareto_nbd {
namespace {

struct RawTable {
    std::shared_ptr<arrow::Table> table;
    bool has_monetary = false;
};

RawTable LoadRawTable(const std::string& path) {
    auto file_result = arrow::io::ReadableFile::Open(path);
    if (!file_result.ok()) {
        throw IngestError("could not open transaction log: " + file_result.status().ToString());
    }

    auto read_options = arrow::csv::ReadOptions::Defaults();
    auto parse_options = arrow::csv::ParseOptions::Defaults();
    auto convert_options = arrow::csv::ConvertOptions::Defaults();
    convert_options.column_types["customer_id"] = arrow::utf8();
    convert_options.column_types["transaction_date"] = arrow::timestamp(arrow::TimeUnit::SECOND);
    convert_options.timestamp_parsers = {arrow::TimestampParser::MakeISO8601()};
    // amount's type (if present) is left to Arrow's own inference (float64
    // for numeric columns); we only need to know whether it exists.

    auto reader_result = arrow::csv::TableReader::Make(
        arrow::io::default_io_context(), *file_result, read_options, parse_options, convert_options);
    if (!reader_result.ok()) {
        throw IngestError("could not parse transaction log: " + reader_result.status().ToString());
    }

    auto table_result = (*reader_result)->Read();
    if (!table_result.ok()) {
        throw IngestError("could not parse transaction log: " + table_result.status().ToString());
    }
    auto table = *table_result;

    const auto& schema = table->schema();
    if (schema->GetFieldIndex("customer_id") < 0) {
        throw IngestError("missing required column 'customer_id'");
    }
    if (schema->GetFieldIndex("transaction_date") < 0) {
        throw IngestError("missing required column 'transaction_date'");
    }
    if (table->num_rows() == 0) {
        throw IngestError("transaction log is empty");
    }

    RawTable result;
    result.table = table;
    result.has_monetary = schema->GetFieldIndex("amount") >= 0;
    return result;
}

constexpr int64_t kSecondsPerDay = 86400;

// Arrow 25's compute kernels (e.g. "sort_indices") are not auto-registered
// on the global FunctionRegistry via static initializers on this build --
// they require an explicit one-time arrow::compute::Initialize() call (see
// arrow/compute/initialize.h). A function-local static gives C++11
// thread-safe, exactly-once initialization without a separate call site.
void EnsureComputeInitialized() {
    static const arrow::Status init_status = arrow::compute::Initialize();
    if (!init_status.ok()) {
        throw IngestError("failed to initialize Arrow compute module: " + init_status.ToString());
    }
}

// Sorts by (customer_id, transaction_date) so every customer's rows are
// contiguous and date-ordered; the linear pass below relies on this.
std::shared_ptr<arrow::Table> SortByCustomerThenDate(const std::shared_ptr<arrow::Table>& table) {
    EnsureComputeInitialized();
    arrow::compute::SortOptions sort_options({
        arrow::compute::SortKey("customer_id", arrow::compute::SortOrder::Ascending),
        arrow::compute::SortKey("transaction_date", arrow::compute::SortOrder::Ascending),
    });
    auto indices = arrow::compute::SortIndices(table, sort_options).ValueOrDie();
    auto sorted = arrow::compute::Take(table, indices).ValueOrDie();
    return sorted.table();
}

// One row per (customer, calendar day), amounts summed within a day.
// Building this from the sorted table is a single pass since duplicate
// (customer, day) rows are guaranteed adjacent after SortByCustomerThenDate.
struct DedupedRow {
    std::string customer_id;
    int64_t day;             // days since epoch
    double amount = 0.0;
};

std::vector<DedupedRow> DedupSameDay(const std::shared_ptr<arrow::Table>& sorted, bool has_monetary) {
    auto combined = sorted->CombineChunks().ValueOrDie();
    auto cust_col = std::static_pointer_cast<arrow::StringArray>(combined->column(0)->chunk(0));
    auto date_col = std::static_pointer_cast<arrow::TimestampArray>(combined->column(1)->chunk(0));
    std::shared_ptr<arrow::DoubleArray> amount_col;
    if (has_monetary) {
        int amount_idx = combined->schema()->GetFieldIndex("amount");
        amount_col = std::static_pointer_cast<arrow::DoubleArray>(combined->column(amount_idx)->chunk(0));
    }

    std::vector<DedupedRow> out;
    const int64_t n = cust_col->length();
    for (int64_t i = 0; i < n; ++i) {
        std::string cust = cust_col->GetString(i);
        int64_t day = date_col->Value(i) / kSecondsPerDay;
        double amount = has_monetary ? amount_col->Value(i) : 0.0;

        if (!out.empty() && out.back().customer_id == cust && out.back().day == day) {
            out.back().amount += amount;   // same-day duplicate: sum
        } else {
            out.push_back({cust, day, amount});
        }
    }
    return out;
}

}  // namespace

CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;   // Task 6 wires this through

    RawTable raw = LoadRawTable(path);
    auto sorted = SortByCustomerThenDate(raw.table);
    auto rows = DedupSameDay(sorted, raw.has_monetary);

    int64_t as_of_day = rows.front().day;
    for (const auto& r : rows) as_of_day = std::max(as_of_day, r.day);

    CustomerFeatures result;
    result.has_monetary = raw.has_monetary;

    size_t i = 0;
    while (i < rows.size()) {
        size_t j = i;
        while (j < rows.size() && rows[j].customer_id == rows[i].customer_id) ++j;
        // rows[i..j) is this customer's date-ordered, same-day-deduped history.
        int64_t acq_day = rows[i].day;
        size_t n_repeats = (j - i) - 1;

        result.customer_id.push_back(rows[i].customer_id);
        result.x.push_back(static_cast<double>(n_repeats));
        result.t_x.push_back(n_repeats > 0 ? (rows[j - 1].day - acq_day) / 7.0 : 0.0);
        result.T_cal.push_back((as_of_day - acq_day) / 7.0);
        if (raw.has_monetary) {
            double sum = 0.0;
            for (size_t k = i + 1; k < j; ++k) sum += rows[k].amount;
            result.m_bar.push_back(n_repeats > 0 ? sum / static_cast<double>(n_repeats) : 0.0);
        }
        i = j;
    }
    return result;
}

}  // namespace pareto_nbd
