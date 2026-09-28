#include "pareto_nbd/ingest.hpp"

#include <arrow/api.h>
#include <arrow/csv/api.h>
#include <arrow/io/api.h>
#include <arrow/util/value_parsing.h>  // arrow::TimestampParser (not re-exported by csv/api.h)

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

}  // namespace

CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;
    RawTable raw = LoadRawTable(path);

    CustomerFeatures result;
    result.has_monetary = raw.has_monetary;
    result.customer_id = {"A", "B", "C"};   // placeholder -- Task 5 replaces this
    return result;
}

}  // namespace pareto_nbd
