#include "pareto_nbd/mcmc_fit.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <sstream>

#include "pareto_nbd/subprocess.hpp"

namespace pareto_nbd {
namespace {

std::string EnvOr(const char* name, const std::string& fallback) {
    const char* v = std::getenv(name);
    return (v && *v) ? std::string(v) : fallback;
}

McmcFitResult Unavailable(const std::string& reason) {
    McmcFitResult r;
    r.note = "High-precision refit unavailable (" + reason + ") - used the fast estimator instead.";
    return r;
}

}  // namespace

McmcFitResult RunMcmcFit(const std::string& job_id, const CustomerFeatures& cohort,
                         UploadStorage& storage) {
    try {
        std::ostringstream csv;
        csv << std::setprecision(17) << "x,t_x,T_cal\n";
        for (size_t i = 0; i < cohort.x.size(); ++i) {
            csv << cohort.x[i] << ',' << cohort.t_x[i] << ',' << cohort.T_cal[i] << '\n';
        }
        const std::string cohort_key = "mcmc/" + job_id + "_cohort.csv";
        const std::string fit_key = "mcmc/" + job_id + "_fit.json";
        const std::string draws_key = "mcmc/" + job_id + "_draws.npz";
        storage.Put(cohort_key, csv.str());

        const std::string py = EnvOr("PARETO_PYTHON", "python");
        const std::string cli =
            EnvOr("PARETO_MCMC_CLI", std::string(PROJECT_ROOT_DIR) + "/src/mcmc_cli.py");
        const int timeout = std::atoi(EnvOr("PARETO_MCMC_TIMEOUT_S", "600").c_str());

        auto res = RunWithTimeout({py, cli, "--cohort", storage.GetPath(cohort_key), "--out",
                                   storage.GetPath(fit_key), "--draws", storage.GetPath(draws_key)},
                                  timeout > 0 ? timeout : 600);
        if (!res.launched) return Unavailable("could not start Python");
        if (res.timed_out) return Unavailable("timed out after " + std::to_string(timeout) + " s");
        if (res.exit_code != 0)
            return Unavailable("sampler exited with code " + std::to_string(res.exit_code));
        if (!storage.Exists(fit_key)) return Unavailable("sampler produced no output");

        std::ifstream in(storage.GetPath(fit_key));
        auto j = nlohmann::json::parse(in);
        McmcFitResult out;
        out.params = ParetoNbdParams{j.at("r").get<double>(), j.at("alpha").get<double>(),
                                     j.at("s").get<double>(), j.at("beta").get<double>()};
        for (double v : {out.params.r, out.params.alpha, out.params.s, out.params.beta}) {
            if (!std::isfinite(v) || v <= 0.0)
                return Unavailable("sampler returned invalid parameters");
        }
        out.ok = true;
        if (storage.Exists(draws_key)) out.draws_key = draws_key;
        return out;
    } catch (const std::exception& e) {
        return Unavailable(std::string("internal error: ") + e.what());
    }
}

}  // namespace pareto_nbd
