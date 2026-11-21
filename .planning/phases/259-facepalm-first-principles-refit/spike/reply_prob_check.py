"""Throwaway: does ln(best-reply prob) add ranking signal to the chosen shape?"""
import csv, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from scripts.blunder_check import fit_facepalm as F
from app.services.facepalm_material import loses

def run(features: str) -> None:
    table = F.load_features(ROOT / "temp/facepalm-259" / features)
    spec = F.CandidateSpec(material_form="split", missed_floor=0, missed_cap=5,
                           spread_form="best_prob_for_misses", material_input="decaying_mean")
    base, _ = F.split_usable(table.rows)
    rows, _ = F.spec_usable(base, spec)
    reply = {r["n"]: r["reply_prob"] for r in csv.DictReader(open(ROOT / "temp/facepalm-259/reply-prob.tsv"), delimiter="\t")}
    x = F.spec_design_matrix(rows, spec)
    y = F.labels_of(rows)
    col, known = [], 0
    for row in rows:
        loss = F._spec_loss(row, spec)
        p = reply.get(str(row.n), "")
        if loses(loss, None) and p:
            col.append(math.log(float(p) + 0.01)); known += 1
        else:
            col.append(0.0)
    col = np.array(col)
    names = F.spec_columns(spec)
    spread_i = names.index("spread")
    variants = {
        "shape as shipped": x,
        "+ reply prob": np.column_stack([x, col]),
        "reply prob instead of spread": np.column_stack([np.delete(x, spread_i, axis=1), col]),
    }
    print(f"\n{features}: rows {len(rows)}, loss rows with a reply prob {known}")
    for name, m in variants.items():
        aucs = [F.auc(F.cv_predictions(m, y, FOLDS, seed), y) for seed in range(F.REPEAT_SEEDS)]
        coef = F.fit_logistic(m, y)
        print(f"  {name:32s} CV AUC {np.mean(aucs):.3f} (sd {np.std(aucs):.3f})  last coef {coef[-1]:+.3f}  spread coef {coef[spread_i] if m.shape[1] > spread_i and name != 'reply prob instead of spread' else float('nan'):+.3f}")

FOLDS = int(sys.argv[1])
for f in ("baseline-today.tsv", "quiet-any.tsv"):
    run(f)
