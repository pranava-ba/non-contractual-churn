import argparse, json, sys

p = argparse.ArgumentParser()
p.add_argument("--cohort"); p.add_argument("--out"); p.add_argument("--draws")
p.add_argument("--n-draws"); p.add_argument("--burn-in"); p.add_argument("--thin"); p.add_argument("--seed")
a = p.parse_args()
open(a.draws, "wb").write(b"fake")
open(a.out, "w").write(json.dumps({"r": 0.7, "alpha": 11.0, "s": 0.6, "beta": 13.0,
                                    "n_keep": 1, "n_customers": 1, "elapsed_s": 0.0}))
