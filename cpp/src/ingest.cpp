#include "pareto_nbd/ingest.hpp"

namespace pareto_nbd {

CustomerFeatures ingest_csv(const std::string& path,
                             std::optional<std::string> as_of_iso_date) {
    (void)as_of_iso_date;
    CustomerFeatures result;
    result.customer_id = {"A", "B", "C"};   // placeholder -- Tasks 4-5 replace this
    return result;
}

}  // namespace pareto_nbd
