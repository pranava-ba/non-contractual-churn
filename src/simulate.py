"""
Pareto/NBD data-generating process — reproduction of the simulation framework in
Simon (2025), "A generalised comparison of Pareto/NBD based forecasts", Table 2.

Model (Schmittlein et al. 1987):
  - Purchase process (while alive): Poisson(lambda_i), i.e. inter-purchase
    times ~ Exp(lambda_i). Heterogeneity: lambda_i ~ Gamma(shape=r, rate=alpha).
  - Dropout: lifetime tau_i ~ Exp(mu_i). Heterogeneity: mu_i ~ Gamma(shape=s, rate=beta).
  - Each customer is acquired (initial purchase) at a random calendar date within
    the first 90 days (~12.857 weeks). Calibration ends at calendar time T.
  - We work in acquisition-relative time per customer: T_i = T - acquisition_i.

Per customer we record the standard BTYD summary (x, t_x, T_i) from the calibration
window plus the ground-truth number of repeat purchases x_star in each forecast
window (T_i, T_i + T*].  x counts REPEAT purchases (the acquisition purchase at
time 0 is excluded).

Table 2 target ranges (all drawn from uniforms per dataset):
  E(lambda) in [0.02, 0.30], CV(lambda) in [0.5, 2.5]
  E(mu)     in [0.02, 0.20], CV(mu)     in [0.5, 2.5]
  N in [1000, 4000], T in [26, 72] weeks, T* in {13, 26, 52}
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

WEEKS_PER_90_DAYS = 90.0 / 7.0  # ~12.857 weeks acquisition window

# Default Table-2 hyper-parameter ranges (edit here to widen the design later).
RANGES = {
    "E_lambda": (0.02, 0.30),
    "CV_lambda": (0.5, 2.5),
    "E_mu": (0.02, 0.20),
    "CV_mu": (0.5, 2.5),
    "N": (1000, 4000),
    "T": (26, 72),
}
FORECAST_HORIZONS = (13, 26, 52)


def moments_to_gamma(mean: float, cv: float) -> tuple[float, float]:
    """Convert a target (mean, coeff. of variation) to Gamma(shape, rate).

    For Gamma(shape=k, rate=theta): mean = k/theta, CV = 1/sqrt(k).
    => shape k = 1/CV**2, rate theta = k / mean.
    """
    shape = 1.0 / (cv * cv)
    rate = shape / mean
    return shape, rate


@dataclass
class DatasetParams:
    """The behavioural + operational characteristics drawn for one dataset."""

    E_lambda: float
    CV_lambda: float
    E_mu: float
    CV_mu: float
    N: int
    T: float
    # derived Gamma heterogeneity parameters (the true values used for scoring)
    r: float = field(init=False)
    alpha: float = field(init=False)
    s: float = field(init=False)
    beta: float = field(init=False)

    def __post_init__(self) -> None:
        self.r, self.alpha = moments_to_gamma(self.E_lambda, self.CV_lambda)
        self.s, self.beta = moments_to_gamma(self.E_mu, self.CV_mu)

    def as_dict(self) -> dict:
        return {
            "E_lambda": self.E_lambda, "CV_lambda": self.CV_lambda,
            "E_mu": self.E_mu, "CV_mu": self.CV_mu, "N": self.N, "T": self.T,
            "r": self.r, "alpha": self.alpha, "s": self.s, "beta": self.beta,
        }


def draw_params(rng: np.random.Generator) -> DatasetParams:
    """Draw one dataset's characteristics uniformly from the Table-2 ranges."""
    return DatasetParams(
        E_lambda=rng.uniform(*RANGES["E_lambda"]),
        CV_lambda=rng.uniform(*RANGES["CV_lambda"]),
        E_mu=rng.uniform(*RANGES["E_mu"]),
        CV_mu=rng.uniform(*RANGES["CV_mu"]),
        N=int(rng.integers(RANGES["N"][0], RANGES["N"][1] + 1)),
        T=float(rng.uniform(*RANGES["T"])),
    )


def _simulate_customer_purchases(
    lam: float, tau: float, horizon: float, rng: np.random.Generator
) -> np.ndarray:
    """Acquisition-relative repeat-purchase times in (0, horizon], truncated at
    dropout time tau.  Time 0 (acquisition) is excluded from the returned array."""
    end = min(tau, horizon)
    if end <= 0:
        return np.empty(0)
    # Poisson process: draw a generous batch of Exp(lam) gaps, cumulative-sum,
    # keep those <= end; extend if we happen to run out (rare).
    times = []
    t = 0.0
    # expected count ~ lam*end; draw with headroom, loop only if exhausted.
    while True:
        batch = rng.exponential(1.0 / lam, size=max(16, int(lam * end * 2) + 8))
        cs = t + np.cumsum(batch)
        keep = cs[cs <= end]
        times.append(keep)
        if len(keep) < len(batch):  # last gap overshot -> process complete
            break
        t = cs[-1]
    return np.concatenate(times) if times else np.empty(0)


def simulate_dataset(
    params: DatasetParams,
    horizons: tuple[int, ...] = FORECAST_HORIZONS,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Simulate one cohort. Returns one row per customer with calibration summary
    (x, t_x, T_i, alive_at_T) and ground-truth x_star_{h} for each forecast horizon."""
    if rng is None:
        rng = np.random.default_rng()

    N = params.N
    lam = rng.gamma(shape=params.r, scale=1.0 / params.alpha, size=N)
    mu = rng.gamma(shape=params.s, scale=1.0 / params.beta, size=N)
    tau = rng.exponential(1.0 / mu)  # lifetime from acquisition (weeks)
    acq = rng.uniform(0.0, WEEKS_PER_90_DAYS, size=N)  # acquisition within 90 days
    T_i = params.T - acq  # individual calibration length
    max_h = max(horizons)

    rows = []
    for i in range(N):
        cal_len = T_i[i]
        # full repeat-purchase path up to the longest forecast window
        path = _simulate_customer_purchases(lam[i], tau[i], cal_len + max_h, rng)
        cal = path[path <= cal_len]
        x = int(cal.size)
        t_x = float(cal.max()) if x > 0 else 0.0
        row = {
            "cust": i,
            "x": x,
            "t_x": t_x,
            "T_cal": cal_len,
            "alive_at_T": bool(tau[i] > cal_len),
            "lambda_true": lam[i],
            "mu_true": mu[i],
            "tau_true": tau[i],
        }
        for h in horizons:
            future = path[(path > cal_len) & (path <= cal_len + h)]
            row[f"x_star_{h}"] = int(future.size)
            # wait time to the next purchase after calibration (inf if none in window) -
            # the ground truth for the timing forecast (Extension B). Read-only, no rng.
            row[f"t_next_{h}"] = float(future.min() - cal_len) if future.size else np.inf
        rows.append(row)

    df = pd.DataFrame(rows)
    df.attrs["params"] = params.as_dict()
    return df


def summarise(df: pd.DataFrame) -> dict:
    """Quick sanity summary of a simulated dataset."""
    p = df.attrs.get("params", {})
    return {
        "N": len(df),
        "mean_x": round(df["x"].mean(), 3),
        "pct_zero_repeat": round((df["x"] == 0).mean() * 100, 1),
        "pct_alive_at_T": round(df["alive_at_T"].mean() * 100, 1),
        "mean_x_star_26": round(df["x_star_26"].mean(), 3),
        "pct_active_26": round((df["x_star_26"] > 0).mean() * 100, 1),
        "E_lambda": round(p.get("E_lambda", float("nan")), 3),
        "E_mu": round(p.get("E_mu", float("nan")), 3),
    }


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    print("Self-test: 3 random datasets from Table-2 ranges\n")
    for k in range(3):
        params = draw_params(rng)
        df = simulate_dataset(params, rng=rng)
        print(f"dataset {k}: ", summarise(df))
