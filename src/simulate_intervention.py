"""
Gear 2, Stage A: intervention data-generating process with GROUND-TRUTH CATE.

Extends the validated Pareto/NBD DGP (simulate.py) with a retention **treatment** T applied at the
calibration boundary T_i. Because we know each customer's latent (lambda, mu) and the exact effect we
inject, we can compute the *expected* potential outcomes analytically -> ground-truth conditional
average treatment effect (CATE) per customer, for three outcomes at once (count / retention / CLV).
Estimators (econml, causalml, ...) see only the NOISY FACTUAL outcome of the arm each customer was
assigned; the analytic CATE is the oracle we score them against.

Design (parameterised so a factorial over the Gear 2 §7 options runs on one engine):
  target    in {"mu","lambda","both"}       -- what the intervention shifts
  structure in {"homogeneous","heterogeneous","sleeping_dogs"} -- effect heterogeneity
  delta     float                            -- effect magnitude (mu: fractional hazard reduction;
                                                lambda: fractional rate increase)
  assignment in {"randomized","confounded"}  -- T independent of state, or firm targets high value/risk

Intervention mechanics (applied at T_i to customers ALIVE at T_i; the already-dead are unaffected ->
they are the "lost causes" a risk model wastes budget on):
  mu1_i = mu_i * (1 - eff_i)      (lower dropout hazard  -> longer residual life)   [target mu/both]
  lam1_i = lam_i * (1 + g*eff_i)  (higher purchase rate)                            [target lambda/both]
where eff_i is the per-customer effect (see _effects). Given "alive at T_i", the residual lifetime is
memoryless ~ Exp(mu_arm), so expected outcomes over a horizon h have closed forms (see _expected_*).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from simulate import DatasetParams, simulate_dataset


@dataclass
class InterventionConfig:
    target: str = "mu"                 # "mu" | "lambda" | "both"
    structure: str = "heterogeneous"   # "homogeneous" | "heterogeneous" | "sleeping_dogs"
    delta: float = 0.40                # base effect size
    assignment: str = "randomized"     # "randomized" | "confounded"
    p_treat: float = 0.5               # marginal treatment share
    lambda_gain: float = 1.0           # scales the lambda effect relative to delta ("both"/"lambda")
    sleeping_frac: float = 0.25        # fraction of (dormant) customers with a NEGATIVE effect
    horizon: int = 26                  # forecast/outcome window (weeks)

    def as_dict(self) -> dict:
        return {"target": self.target, "structure": self.structure, "delta": self.delta,
                "assignment": self.assignment, "p_treat": self.p_treat,
                "lambda_gain": self.lambda_gain, "sleeping_frac": self.sleeping_frac,
                "horizon": self.horizon}


def _standardize(v: np.ndarray) -> np.ndarray:
    s = v.std()
    return (v - v.mean()) / s if s > 0 else np.zeros_like(v)


def _effects(cfg: InterventionConfig, x: np.ndarray, t_x: np.ndarray, T_cal: np.ndarray,
             rng: np.random.Generator) -> np.ndarray:
    """Per-customer effect fraction eff_i in (-1, 1). Heterogeneity keys off observable RFM so an
    estimator can in principle recover it. Persuadability rises with engagement (frequency + recency)."""
    n = len(x)
    freq_z = _standardize(x.astype(float))
    rec_z = _standardize(t_x / np.maximum(T_cal, 1e-6))   # relative recency
    if cfg.structure == "homogeneous":
        eff = np.full(n, cfg.delta)
    else:
        # persuadability score in (0,1): engaged, recent buyers respond most
        score = 1.0 / (1.0 + np.exp(-(0.8 * freq_z + 0.8 * rec_z)))
        eff = cfg.delta * (0.25 + 1.5 * score)            # spread around delta
        if cfg.structure == "sleeping_dogs":
            # "do-not-disturb": loyal, engaged customers who would have stayed anyway are ANNOYED by
            # the contact and churn faster (Ascarza 2018). Keying on high engagement makes the
            # negative effect visible (these customers are alive with non-trivial lambda).
            loyal = (freq_z + rec_z) > np.quantile(freq_z + rec_z, 1.0 - cfg.sleeping_frac)
            eff = np.where(loyal, -np.abs(cfg.delta) * (0.5 + rng.random(n)), eff)
    return np.clip(eff, -0.95, 0.95)


def _propensity(cfg: InterventionConfig, lam: np.ndarray, mu: np.ndarray,
                rng: np.random.Generator) -> np.ndarray:
    """Treatment assignment. Randomized -> Bernoulli(p_treat). Confounded -> firm over-targets
    high-value (high lambda) and high-risk (high mu) customers, so treated differ in latent state."""
    n = len(lam)
    if cfg.assignment == "randomized":
        return rng.binomial(1, cfg.p_treat, size=n)
    z = 1.2 * _standardize(lam) + 1.2 * _standardize(mu)
    p = 1.0 / (1.0 + np.exp(-z))
    p = np.clip(p * (cfg.p_treat / p.mean()), 0.02, 0.98)  # re-centre to ~p_treat, keep overlap
    return rng.binomial(1, p)


def _expected_count(lam: np.ndarray, mu: np.ndarray, h: float) -> np.ndarray:
    """E[# repeat purchases in (0,h] | alive at 0, rates (lam,mu)]; residual life ~ Exp(mu)."""
    return (lam / mu) * (1.0 - np.exp(-mu * h))


def _p_active(lam: np.ndarray, mu: np.ndarray, h: float) -> np.ndarray:
    """P(>=1 purchase in (0,h] | alive at 0). P(0) = mu/(lam+mu)(1-e^{-(lam+mu)h}) + e^{-(lam+mu)h}."""
    s = lam + mu
    p0 = (mu / s) * (1.0 - np.exp(-s * h)) + np.exp(-s * h)
    return 1.0 - p0


def _simulate_arm(lam: np.ndarray, mu: np.ndarray, alive: np.ndarray, nu: np.ndarray, h: float,
                  rng: np.random.Generator):
    """Noisy factual outcome for one arm over (0,h]: residual life ~ Exp(mu), purchases ~ Poisson(lam)
    up to min(R,h); spend per purchase ~ Exp(mean nu). Dead-at-T customers yield zeros."""
    n = len(lam)
    R = rng.exponential(1.0 / mu)                 # residual lifetime from T_i
    window = np.minimum(R, h) * alive             # 0 if already dead
    counts = rng.poisson(lam * window)
    spend = counts * nu * rng.gamma(shape=4.0, scale=0.25, size=n)  # mean-nu spend w/ mild noise
    return counts.astype(float), (counts > 0).astype(float), spend


def simulate_intervention(params: DatasetParams, cfg: InterventionConfig,
                          rng: np.random.Generator | None = None) -> pd.DataFrame:
    """One cohort with a treatment. Returns one row per customer:
      features: x, t_x, T_cal, alive_at_T, lambda_true, mu_true
      assignment: T
      factual (what an estimator sees): y_count, y_active, y_clv   (outcome of the assigned arm)
      potential (validation only): y*_0/y*_1 per outcome
      ORACLE ground-truth CATE: cate_count, cate_active, cate_clv
    """
    if rng is None:
        rng = np.random.default_rng()
    h = float(cfg.horizon)

    base = simulate_dataset(params, horizons=(cfg.horizon,), rng=rng)
    lam = base["lambda_true"].to_numpy(float)
    mu0 = base["mu_true"].to_numpy(float)
    alive = base["alive_at_T"].to_numpy(float)
    x = base["x"].to_numpy(float)
    t_x = base["t_x"].to_numpy(float)
    T_cal = base["T_cal"].to_numpy(float)
    n = len(base)
    nu = rng.gamma(shape=4.0, scale=12.5, size=n)          # mean spend ~50 per purchase, heterogeneous

    eff = _effects(cfg, x, t_x, T_cal, rng)
    # eff is already clipped to (-0.95, 0.95) in _effects, so (1-eff) in [0.05, 1.95] and
    # (1+lambda_gain*eff) in [0.05, 1.95] (lambda_gain=1.0 default): the multiplicative transform
    # is provably strictly positive and bounded away from zero RELATIVE TO mu0/lam0 on its own.
    # An earlier fixed floor of 1e-4 could exceed mu0*(1-eff) for the rare customer whose drawn
    # mu0 was already below ~1.7e-4 (the Gamma(mu) heterogeneity has a heavy tail down to ~1e-7),
    # which INVERTED the treatment direction for exactly that customer. Floor at a genuine
    # underflow guard instead (never binds for any realistic draw) so direction is never inverted.
    mu1 = mu0 * (1.0 - eff) if cfg.target in ("mu", "both") else mu0
    mu1 = np.clip(mu1, 1e-9, None)
    lam1 = lam * (1.0 + cfg.lambda_gain * eff) if cfg.target in ("lambda", "both") else lam
    lam1 = np.clip(lam1, 1e-9, None)

    T = _propensity(cfg, lam, mu0, rng)

    # oracle CATE (analytic expectation, conditional on alive-at-T)
    cate_count = alive * (_expected_count(lam1, mu1, h) - _expected_count(lam, mu0, h))
    cate_active = alive * (_p_active(lam1, mu1, h) - _p_active(lam, mu0, h))
    cate_clv = cate_count * nu

    # noisy factual + both potential outcomes (common config, independent draws per arm)
    c0, a0, v0 = _simulate_arm(lam, mu0, alive, nu, h, rng)
    c1, a1, v1 = _simulate_arm(lam1, mu1, alive, nu, h, rng)
    pick = T == 1
    df = pd.DataFrame({
        "cust": base["cust"], "x": x, "t_x": t_x, "T_cal": T_cal, "alive_at_T": alive,
        "lambda_true": lam, "mu_true": mu0, "nu_true": nu, "eff_true": eff, "T": T,
        "y_count": np.where(pick, c1, c0), "y_active": np.where(pick, a1, a0),
        "y_clv": np.where(pick, v1, v0),
        "y0_count": c0, "y1_count": c1, "y0_active": a0, "y1_active": a1, "y0_clv": v0, "y1_clv": v1,
        "cate_count": cate_count, "cate_active": cate_active, "cate_clv": cate_clv,
    })
    df.attrs["params"] = params.as_dict()
    df.attrs["intervention"] = cfg.as_dict()
    return df


def summarise(df: pd.DataFrame) -> dict:
    cfg = df.attrs.get("intervention", {})
    return {
        "target": cfg.get("target"), "structure": cfg.get("structure"),
        "assignment": cfg.get("assignment"), "N": len(df),
        "treated_share": round(df["T"].mean(), 3),
        "true_ATE_count": round(df["cate_count"].mean(), 4),
        "true_ATE_clv": round(df["cate_clv"].mean(), 3),
        "true_ATE_active": round(df["cate_active"].mean(), 4),
        "pct_negative_cate": round((df["cate_count"] < -1e-6).mean() * 100, 1),
        "naive_diff_count": round(df.loc[df["T"] == 1, "y_count"].mean()
                                  - df.loc[df["T"] == 0, "y_count"].mean(), 4),
    }


if __name__ == "__main__":
    from simulate import draw_params
    rng = np.random.default_rng(7)
    params = draw_params(rng)
    print("Self-test: intervention DGP across a few configs\n")
    for structure in ("homogeneous", "heterogeneous", "sleeping_dogs"):
        for assignment in ("randomized", "confounded"):
            cfg = InterventionConfig(target="mu", structure=structure, delta=0.4,
                                     assignment=assignment)
            df = simulate_intervention(params, cfg, rng=rng)
            print(summarise(df))
    # sanity: with confounding, the naive difference should be biased vs the true ATE;
    # under randomization it should roughly match.
