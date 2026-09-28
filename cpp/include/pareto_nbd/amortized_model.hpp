#pragma once
#include <array>
#include <memory>
#include <string>

namespace pareto_nbd {

struct AmortizedParams {
    double r;
    double alpha;
    double s;
    double beta;
};

// Loads the exported MLP (ONNX) + scaler JSON produced by
// src/export_amortizer_onnx.py and reproduces amortized.amortized_params()
// from the Python implementation.
class AmortizedModel {
public:
    AmortizedModel(const std::string& onnx_path, const std::string& scalers_json_path);
    ~AmortizedModel();

    AmortizedModel(AmortizedModel&&) noexcept;
    AmortizedModel& operator=(AmortizedModel&&) noexcept;

    AmortizedParams predict(const std::array<double, 11>& features) const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace pareto_nbd
