#include "pareto_nbd/amortized_model.hpp"
#include "pareto_nbd/moments.hpp"

#include <cmath>
#include <fstream>
#include <vector>

#include <nlohmann/json.hpp>
#include <onnxruntime_cxx_api.h>

namespace pareto_nbd {
namespace {

#ifdef _WIN32
std::wstring to_ort_path(const std::string& s) { return std::wstring(s.begin(), s.end()); }
#else
std::string to_ort_path(const std::string& s) { return s; }
#endif

}  // namespace

struct AmortizedModel::Impl {
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "amortized_model"};
    Ort::Session session;
    std::array<double, 11> x_mean{};
    std::array<double, 11> x_scale{};
    std::array<double, 4> y_mean{};
    std::array<double, 4> y_scale{};

    Impl(const std::string& onnx_path, const std::string& scalers_json_path)
        : session(env, to_ort_path(onnx_path).c_str(), Ort::SessionOptions{nullptr}) {
        std::ifstream f(scalers_json_path);
        nlohmann::json j;
        f >> j;
        for (size_t i = 0; i < 11; ++i) {
            x_mean[i] = j["x_mean"][i].get<double>();
            x_scale[i] = j["x_scale"][i].get<double>();
        }
        for (size_t i = 0; i < 4; ++i) {
            y_mean[i] = j["y_mean"][i].get<double>();
            y_scale[i] = j["y_scale"][i].get<double>();
        }
    }
};

AmortizedModel::AmortizedModel(const std::string& onnx_path, const std::string& scalers_json_path)
    : impl_(std::make_unique<Impl>(onnx_path, scalers_json_path)) {}

AmortizedModel::~AmortizedModel() = default;

AmortizedParams AmortizedModel::predict(const std::array<double, 11>& features) const {
    std::vector<float> input(11);
    for (size_t i = 0; i < 11; ++i) {
        input[i] = static_cast<float>((features[i] - impl_->x_mean[i]) / impl_->x_scale[i]);
    }

    Ort::MemoryInfo mem_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    std::array<int64_t, 2> input_shape{1, 11};
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        mem_info, input.data(), input.size(), input_shape.data(), input_shape.size());

    Ort::AllocatorWithDefaultOptions allocator;
    auto input_name = impl_->session.GetInputNameAllocated(0, allocator);
    auto output_name = impl_->session.GetOutputNameAllocated(0, allocator);
    const char* input_names[] = {input_name.get()};
    const char* output_names[] = {output_name.get()};

    auto outputs = impl_->session.Run(Ort::RunOptions{nullptr}, input_names, &input_tensor, 1,
                                       output_names, 1);
    const float* y_scaled = outputs.front().GetTensorData<float>();

    // y = [E_lambda, E_mu, CV_lambda, CV_mu] in standardized log-space,
    // matching amortized.amortized_params's Y column order exactly.
    std::array<double, 4> y{};
    for (size_t i = 0; i < 4; ++i) {
        y[i] = std::exp(static_cast<double>(y_scaled[i]) * impl_->y_scale[i] + impl_->y_mean[i]);
    }

    auto [r, alpha] = moments_to_gamma(y[0], y[2]);   // (E_lambda, CV_lambda)
    auto [s, beta] = moments_to_gamma(y[1], y[3]);    // (E_mu, CV_mu)
    return {r, alpha, s, beta};
}

}  // namespace pareto_nbd
