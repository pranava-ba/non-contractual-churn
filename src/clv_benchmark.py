"""
Phase 2, Step 7: probabilistic CLV benchmark -- structural vs. deep, under proper scoring.

Two forecasters for future customer value (money) over the horizon:
  - BTYD + Gamma-Gamma : Pareto/NBD predicts the purchase-count distribution x*, the Gamma-Gamma
    model (Fader, Hardie & Lee 2005) predicts the per-transaction spend nu; CLV = x* * nu.
  - ZILN (deep)        : a zero-inflated lognormal neural network (Wang, Liu & Fang 2019) --
    an MLP whose three outputs parameterise P(spend>0) and a lognormal for the positive part,
    trained with the ZILN loss. This is ZILN in its true monetary home.

Both are scored on the continuous CLV target with the same CRPS / PIT / coverage engine, on a fair
train/test split (ZILN is supervised on RFM+spend features; BTYD+GG is unsupervised).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))


def clv_features(df) -> np.ndarray:
    """RFM + spend features for the ML CLV model."""
    x = df["x"].to_numpy(float)
    tx = df["t_x"].to_numpy(float)
    T = df["T_cal"].to_numpy(float)
    mb = df["m_bar"].to_numpy(float)
    since = np.maximum(T - tx, 0.0)
    rate = np.divide(x, T, out=np.zeros_like(x), where=T > 0)
    return np.column_stack([x, tx, T, since, rate, mb, np.log1p(mb), x * mb])


def btyd_gg_clv_predict(df, horizon: int, seed: int = 0, mcmc_draws: int = 1500):
    """CLV predictive samples from Pareto/NBD (counts) x Gamma-Gamma (spend). Returns (J, N)."""
    from estimate import fit_mcmc
    from score import spp_predict
    from clv import fit_gamma_gamma, sample_posterior_nu

    Tcal = df["T_cal"].to_numpy(float)
    x = df["x"].to_numpy(float)
    m_bar = df["m_bar"].to_numpy(float)
    mc = fit_mcmc(df, n_draws=mcmc_draws, burn_in=500, thin=5, seed=seed + 1)
    counts = spp_predict(mc.lam, mc.mu, mc.tau, Tcal, horizon, np.random.default_rng(seed + 2))
    gg = fit_gamma_gamma(x, m_bar)
    nu = sample_posterior_nu(x, m_bar, gg["p"], gg["q"], gg["v"],
                             n_draws=counts.shape[0], seed=seed + 3)
    return counts * nu


def ziln_clv_predict(X_train, y_train, X_test, n_draws: int = 400, seed: int = 0, epochs: int = 1000):
    """Deep zero-inflated lognormal (Wang et al. 2019). MLP -> (P(spend>0), mu, sigma); predictive
    is 0 with prob 1-p, else LogNormal(mu, sigma). Uses a validation split for early stopping (so
    sigma is not over-inflated) and caps the heavy lognormal tail (extreme draws would otherwise
    dominate the CRPS). Returns (n_draws, N_test) CLV samples."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    torch.manual_seed(seed)
    y_train = np.asarray(y_train, float)
    mu_x, sd_x = X_train.mean(0), X_train.std(0) + 1e-8

    rng = np.random.default_rng(seed)
    m = len(X_train)
    perm = rng.permutation(m)
    n_val = max(50, int(0.15 * m))
    val_idx, tr_idx = perm[:n_val], perm[n_val:]

    def to_t(a):
        return torch.tensor((a - mu_x) / sd_x, dtype=torch.float32)

    def targets(y):
        yt = torch.tensor(y, dtype=torch.float32)
        return (yt > 0).float(), torch.log(torch.clamp(yt, min=1e-3))

    Xtr, Xval = to_t(X_train[tr_idx]), to_t(X_train[val_idx])
    a_tr, logy_tr = targets(y_train[tr_idx])
    a_val, logy_val = targets(y_train[val_idx])
    bce = nn.BCEWithLogitsLoss()

    def ziln_loss(out, active, logy):
        p_logit, mu, log_sigma = out[:, 0], out[:, 1], out[:, 2]
        sigma = F.softplus(log_sigma) + 1e-3
        L = bce(p_logit, active)
        pos = active > 0
        if pos.any():
            L = L + (0.5 * ((logy[pos] - mu[pos]) / sigma[pos]) ** 2 + torch.log(sigma[pos])).mean()
        return L

    net = nn.Sequential(nn.Linear(X_train.shape[1], 64), nn.ReLU(),
                        nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 3))
    opt = torch.optim.Adam(net.parameters(), lr=5e-3, weight_decay=1e-4)
    best_val, best_state, bad, patience = np.inf, None, 0, 50
    for _ in range(epochs):
        net.train(); opt.zero_grad()
        ziln_loss(net(Xtr), a_tr, logy_tr).backward(); opt.step()
        net.eval()
        with torch.no_grad():
            vl = ziln_loss(net(Xval), a_val, logy_val).item()
        if vl < best_val - 1e-4:
            best_val, best_state, bad = vl, {k: v.clone() for k, v in net.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state is not None:
        net.load_state_dict(best_state)

    net.eval()
    with torch.no_grad():
        out = net(to_t(X_test))
        p = torch.sigmoid(out[:, 0]).numpy()
        mu = out[:, 1].numpy()
        sigma = (F.softplus(out[:, 2]) + 1e-3).numpy()

    rng2 = np.random.default_rng(seed + 1)
    n = len(p)
    is_active = rng2.uniform(size=(n_draws, n)) < p[None, :]
    lognorm = np.exp(mu[None, :] + sigma[None, :] * rng2.standard_normal((n_draws, n)))
    pos_y = y_train[y_train > 0]
    cap = (np.quantile(pos_y, 0.999) * 3.0) if pos_y.size else (y_train.max() * 3.0 + 1.0)
    return np.clip(is_active * lognorm, 0.0, cap)


def compare_clv(df, horizon: int, test_frac: float = 0.3, seed: int = 0, mcmc_draws: int = 1500):
    """Score BTYD+Gamma-Gamma vs. deep ZILN on the CLV target, held-out split."""
    from score import score_forecast

    y = df[f"clv_{horizon}"].to_numpy(float)
    x = df["x"].to_numpy(float)
    n = len(df)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_test = int(round(test_frac * n))
    test_idx = np.sort(idx[:n_test])
    train_idx = np.sort(idx[n_test:])

    clv_bg = btyd_gg_clv_predict(df, horizon, seed=seed, mcmc_draws=mcmc_draws)[:, test_idx]
    X = clv_features(df)
    clv_ziln = ziln_clv_predict(X[train_idx], y[train_idx], X[test_idx], seed=seed + 7)

    y_test, active = y[test_idx], x[test_idx] > 0
    out = {}
    for name, pred in [("BTYD+GG", clv_bg), ("ZILN", clv_ziln)]:
        for cond, mask in [("all", np.ones(len(y_test), bool)), ("x>0", active)]:
            if mask.sum() < 15:
                continue
            sc = score_forecast(pred[:, mask], y_test[mask], np.random.default_rng(seed + 8))
            out[(name, cond)] = {"CRPS": sc["CRPS"], "pit_ks": sc["pit_ks"],
                                 "cov95": sc["cov95"], "nMAE": sc["nMAE"]}
    out["_n_test"] = int(n_test)
    return out


if __name__ == "__main__":
    from clv_data import load_clv_summary
    for name in ["OnlineRetailII", "Dunnhumby"]:
        df, h = load_clv_summary(name)
        res = compare_clv(df, h, seed=1)
        print(f"\n=== {name} CLV (n_test={res['_n_test']}) ===")
        print(f"  {'method':10s}{'cond':5s}{'CRPS':>12s}{'PIT-KS':>9s}{'cov95':>8s}{'nMAE':>8s}")
        for k, s in res.items():
            if isinstance(k, tuple):
                print(f"  {k[0]:10s}{k[1]:5s}{s['CRPS']:>12.2f}{s['pit_ks']:>9.3f}"
                      f"{s['cov95']:>8.3f}{s['nMAE']:>8.3f}")
