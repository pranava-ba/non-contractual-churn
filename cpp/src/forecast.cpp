// C++ port of src/forecast_closed_form.py (p_alive, expected_purchases_exact).
//
// Model and decomposition (identical to the Python oracle and estimate._pnbd_loglik):
//   L_i   = p1_i * (term1 + term2)
//   term1 = 1 / ((alpha+T)^(r+x) (beta+T)^s)                    alive-at-T branch
//   term2 = (s / rsx) * A0                                       died-in-(t_x, T] branch
//   A0    = H(t_x) / (m+t_x)^rsx - H(T) / (m+T)^rsx
//   H(t)  = 2F1(rsx, b; rsx+1; z(t)),  z(t) = |alpha-beta| / (m+t),  m = max(alpha,beta)
//   b     = s+1 if alpha >= beta else r+x,  rsx = r+s+x
//   P(alive) = 1 / (1 + R),  R = term2 / term1, evaluated as log R.
//
// Numerics -- two deliberate departures from a literal transcription, both
// mathematically identical to the oracle and both validated against independent
// 50-digit mpmath integrals in models/forecast_golden.json:
//
// 1. hyp2f1 via the Euler transformation (DLMF 15.8.1), NOT the plain 2F1 series and
//    NOT the Pfaff transformation.  With c = a+1:
//        2F1(a, b; a+1; z) = (1-z)^(1-b) * 2F1(1, a+1-b; a+1; z)
//                          = (1-z)^(1-b) * S,   S = sum_n (p)_n/(q)_n z^n,
//    p = a+1-b, q = a+1.  Here p < q always (q-p = b > 0) and 0 <= z < 1, so every
//    term is positive and each term ratio (p+n)/(q+n)*z is < z: no cancellation, a
//    rigorous geometric tail bound, and S <= 1/(1-z) never overflows.  The prefactor
//    is kept in log space, so log H is finite for every customer.  By contrast the
//    plain series' terms grow to ~(1-z)^(-b), which is exactly what overflows scipy's
//    hyp2f1 for heavy buyers with alpha < beta (the oracle's quadrature-fallback
//    region) -- this formulation evaluates that region directly, with no quadrature.
//    (The Pfaff transformation, which the Task-6a review warned against, maps z to
//    z/(z-1) < -1 for z > 1/2 and needs analytic continuation; it is not used here.)
//
// 2. log R regrouped so the large (r+x)*log(...) terms cancel analytically instead of
//    numerically.  With D = T-t_x, La = log1p(D/(alpha+t_x)), Lb = log1p(D/(beta+t_x)):
//        log R = log(s/rsx) + log S(t_x) + log(1 - exp(d)) + (r+x) La + s Lb
//                + [alpha<beta] * log((alpha+t_x)/(beta+t_x))
//        d     = log S(T) - log S(t_x) + { (1-r-x) La - (1+s) Lb   if alpha < beta
//                                        { -(r+x) La - s Lb          otherwise
//    (substitute log H = (1-b) log((min+t)/(m+t)) + log S into the oracle's
//    l1 + log1mexp(l2-l1) + (r+x) log(alpha+T) + s log(beta+T) and collect terms).
//    The oracle's literal form loses ~1e-12 relative for x ~ 2000 to cancellation of
//    terms of size ~(r+x)*log(alpha+T); this form stays at ~1e-13 vs mpmath.
//
// MVP scope limitation (documented, intentional -- same spirit as this plan's other
// scope trade-offs, e.g. the MinIO deferral): when z(t) is extremely close to 1, i.e.
// min(alpha,beta)+t << max(alpha,beta)+t, S needs ~37/(1-z) terms.  We cap the series
// at kMaxSeriesTerms (enough for (min+t)/(max+t) >~ 4e-5; realistic fitted cohorts
// need tens to a few thousand terms) and throw ForecastOverflowError beyond it rather
// than port the oracle's adaptive-quadrature fallback to C++, which would be a
// meaningful extra numerical surface for a parameter regime (e.g. alpha/beta = 1e-8)
// that real fits do not produce.  A non-finite final result throws the same type.
#include "pareto_nbd/forecast.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace pareto_nbd {

namespace {

constexpr long kMaxSeriesTerms = 1'000'000;
// Stop once the rigorous tail bound is below this fraction of the running sum
// (below double epsilon, so truncation never contributes visible error).
constexpr double kSeriesRelTol = 1e-17;

void validate(const ParetoNbdParams& p, double x, double t_x, double T) {
    for (double v : {p.r, p.alpha, p.s, p.beta}) {
        if (!(std::isfinite(v) && v > 0.0)) {
            throw std::invalid_argument("r, alpha, s, beta must be finite and > 0");
        }
    }
    if (!(std::isfinite(x) && std::isfinite(t_x) && std::isfinite(T))) {
        throw std::invalid_argument("x, t_x, T must be finite");
    }
    if (x < 0.0 || t_x < 0.0 || t_x > T) {
        throw std::invalid_argument("require x >= 0 and 0 <= t_x <= T");
    }
}

[[noreturn]] void throw_not_converged(const ParetoNbdParams& p, double x, double t,
                                      double one_minus_z) {
    std::ostringstream msg;
    msg.precision(6);
    msg << "P(alive) computation could not converge for this customer (x=" << x
        << ", t=" << t << ", alpha=" << p.alpha << ", beta=" << p.beta
        << "): (min(alpha,beta)+t)/(max(alpha,beta)+t) = " << one_minus_z
        << " is too small for the hypergeometric series to converge within "
        << kMaxSeriesTerms
        << " terms; this is a known, documented limitation of the fast C++ path "
           "for extreme parameter combinations";
    throw ForecastOverflowError(msg.str());
}

// log S, S = 2F1(1, p; q; z) = sum_{n>=0} (p)_n / (q)_n * z^n, for 0 < p < q and
// 0 <= z < 1 (one_minus_z = 1 - z, passed in exactly). Terms are positive and
// decreasing with ratio rho_n = (p+n)/(q+n) * z < z, so after term t_n the tail is
// at most t_n * z / (1 - z). Kahan-compensated summation.
double log_series(double p, double q, double z, double one_minus_z,
                  const ParetoNbdParams& params, double x, double t) {
    if (z == 0.0) return 0.0;
    const double tail_factor = z / one_minus_z;
    double sum = 1.0;
    double comp = 0.0;
    double term = 1.0;
    for (long n = 0; n < kMaxSeriesTerms; ++n) {
        term *= (p + n) / (q + n) * z;
        const double y = term - comp;
        const double next = sum + y;
        comp = (next - sum) - y;
        sum = next;
        if (term * tail_factor <= kSeriesRelTol * sum) return std::log(sum);
    }
    throw_not_converged(params, x, t, one_minus_z);
}

// log R = log(term2 / term1); -infinity when t_x == T (no room to have died).
double log_alive_odds(const ParetoNbdParams& prm, double x, double t_x, double T) {
    if (t_x >= T) return -std::numeric_limits<double>::infinity();
    const double r = prm.r, alpha = prm.alpha, s = prm.s, beta = prm.beta;
    const bool alpha_lt_beta = alpha < beta;
    const double m = alpha_lt_beta ? beta : alpha;
    const double mn = alpha_lt_beta ? alpha : beta;
    const double absdiff = m - mn;
    const double rsx = r + s + x;
    // Euler-transformed series parameters: p = a+1-b, q = a+1 with a = rsx.
    const double p = alpha_lt_beta ? (s + 1.0) : (r + x);
    const double q = rsx + 1.0;

    auto log_S = [&](double t) {
        const double z = absdiff / (m + t);
        const double one_minus_z = (mn + t) / (m + t);
        return log_series(p, q, z, one_minus_z, prm, x, t);
    };
    const double lS_tx = log_S(t_x);
    const double lS_T = log_S(T);

    const double D = T - t_x;
    const double La = std::log1p(D / (alpha + t_x));
    const double Lb = std::log1p(D / (beta + t_x));
    double d;
    double branch;
    if (alpha_lt_beta) {
        d = lS_T - lS_tx + (1.0 - r - x) * La - (1.0 + s) * Lb;
        branch = std::log(alpha + t_x) - std::log(beta + t_x);
    } else {
        d = lS_T - lS_tx - (r + x) * La - s * Lb;
        branch = 0.0;
    }
    // log(1 - exp(d)); d >= 0 only through rounding when A0 ~ 0 -> A0 = 0 (as oracle).
    if (!(d < 0.0)) return -std::numeric_limits<double>::infinity();
    const double log_one_minus = std::log(-std::expm1(d));
    return std::log(s) - std::log(rsx) + lS_tx + log_one_minus + (r + x) * La + s * Lb +
           branch;
}

// E[(1 - exp(-mu h)) / mu] for mu ~ Gamma(s, rate = beta+T): expected time a customer
// alive at T stays alive within (T, T+h]. Equals (beta+T)/(s-1) * [1 - ((beta+T)/
// (beta+T+h))^(s-1)], evaluated as -(beta+T) * L * expm1(a)/a with
// L = log((beta+T)/(beta+T+h)) and a = (s-1) L -- exact for every s > 0 including the
// removable singularity at s = 1, where it tends to (beta+T) log((beta+T+h)/(beta+T)).
double expected_active_time(double s, double beta, double T, double h) {
    const double L = -std::log1p(h / (beta + T));  // <= 0
    const double a = (s - 1.0) * L;
    const double phi = (std::abs(a) < 1e-8) ? 1.0 + a / 2.0 + a * a / 6.0 : std::expm1(a) / a;
    return -(beta + T) * L * phi;  // in [0, h]
}

}  // namespace

double p_alive(const ParetoNbdParams& params, double x, double t_x, double T) {
    validate(params, x, t_x, T);
    const double log_R = log_alive_odds(params, x, t_x, T);
    if (std::isnan(log_R)) {
        std::ostringstream msg;
        msg << "P(alive) computation produced a non-finite value for this customer (x=" << x
            << ", t_x=" << t_x << ", T=" << T
            << "); this is a known, documented limitation of the fast C++ path for "
               "extreme cohorts";
        throw ForecastOverflowError(msg.str());
    }
    // 1 / (1 + exp(log_R)), stable for both signs; log_R = -inf -> 1, +inf -> 0.
    if (log_R >= 0.0) {
        const double e = std::exp(-log_R);
        return e / (1.0 + e);
    }
    return 1.0 / (1.0 + std::exp(log_R));
}

double expected_purchases(const ParetoNbdParams& params, double x, double t_x, double T,
                          double horizon, double precomputed_p_alive) {
    if (!(std::isfinite(horizon) && horizon >= 0.0)) {
        throw std::invalid_argument("horizon must be finite and >= 0");
    }
    // x, t_x, T, params still get the same cheap validation p_alive() would have done --
    // only the expensive hypergeometric series inside p_alive is skipped.
    validate(params, x, t_x, T);
    if (!(std::isfinite(precomputed_p_alive) && precomputed_p_alive >= 0.0 &&
          precomputed_p_alive <= 1.0)) {
        throw std::invalid_argument("precomputed_p_alive must be finite and in [0, 1]");
    }
    const double out = precomputed_p_alive * (params.r + x) / (params.alpha + T) *
                       expected_active_time(params.s, params.beta, T, horizon);
    if (!std::isfinite(out)) {
        std::ostringstream msg;
        msg << "expected_purchases produced a non-finite value for this customer (x=" << x
            << ", t_x=" << t_x << ", T=" << T << ", horizon=" << horizon
            << "); this is a known, documented limitation of the fast C++ path for "
               "extreme cohorts";
        throw ForecastOverflowError(msg.str());
    }
    return out;
}

double expected_purchases(const ParetoNbdParams& params, double x, double t_x, double T,
                          double horizon) {
    const double pa = p_alive(params, x, t_x, T);
    return expected_purchases(params, x, t_x, T, horizon, pa);
}

bool WouldOverflow(const ParetoNbdParams& params, double t_x) {
    if (!(std::isfinite(params.alpha) && params.alpha > 0.0 && std::isfinite(params.beta) &&
          params.beta > 0.0 && std::isfinite(t_x) && t_x >= 0.0)) {
        throw std::invalid_argument("alpha, beta must be finite and > 0, t_x finite and >= 0");
    }
    const double m = std::max(params.alpha, params.beta);
    const double mn = std::min(params.alpha, params.beta);
    const double z = (m - mn) / (m + t_x);
    if (z == 0.0) return false;  // alpha == beta: log_series short-circuits, never overflows
    const double one_minus_z = (mn + t_x) / (m + t_x);
    const double tail_factor = z / one_minus_z;

    // log_series's loop stops once term_n * tail_factor <= kSeriesRelTol * sum. It is proven
    // there (see that function's comment) that term_n <= z^n always, and sum >= term_0 = 1
    // always. Substituting those bounds gives a conservative, closed-form requirement on the
    // term count N: if even z^N * tail_factor <= kSeriesRelTol holds (the hardest version of
    // the real stopping condition, since it assumes the slowest-possible decay and the
    // smallest-possible sum), the real loop has certainly already stopped by N terms too.
    // Solving for N: N >= (log(kSeriesRelTol) - log(tail_factor)) / log(z).
    const double log_z = std::log(z);  // z in (0, 1) here, so log_z < 0
    const double required_n = (std::log(kSeriesRelTol) - std::log(tail_factor)) / log_z;
    return required_n > static_cast<double>(kMaxSeriesTerms);
}

}  // namespace pareto_nbd
