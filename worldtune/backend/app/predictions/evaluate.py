"""Prediction evaluation (spec section 16).

Financial metrics: direction accuracy, precision / recall / F1 per direction,
Brier score, calibration curve, ROC AUC.
Career metrics: MAE, direction accuracy, trend correlation, ranking stability.

Every function is pure over lists of numbers so it can be unit-tested against
hand-computed fixtures. Small-sample behaviour is explicit: an undefined
metric returns `None`, not 0.0. Reporting "precision: 0.0" when no positive
call was ever made is a lie that reads as a result; `None` reads as "not
enough data", which is the truth for a young prototype.

NON-GOAL, again and on purpose: accuracy here is a research diagnostic. It is
not a backtest, it includes no costs, slippage or position sizing, and no
statement in this module should be read as a claim of profitability.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np


@dataclass
class ClassificationMetrics:
    n: int = 0
    accuracy: float | None = None
    per_class: dict[str, dict] = field(default_factory=dict)
    macro_f1: float | None = None
    brier: float | None = None
    roc_auc: float | None = None
    calibration: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- classification ----------------------------------------------------------

def direction_accuracy(predicted: list[str], actual: list[str]) -> float | None:
    if not predicted or len(predicted) != len(actual):
        return None
    return float(sum(p == a for p, a in zip(predicted, actual)) / len(predicted))


def precision_recall_f1(predicted: list[str], actual: list[str],
                        label: str) -> dict[str, float | None]:
    """One-vs-rest for `label`. Undefined ratios return None, not 0."""
    tp = sum(p == label and a == label for p, a in zip(predicted, actual))
    fp = sum(p == label and a != label for p, a in zip(predicted, actual))
    fn = sum(p != label and a == label for p, a in zip(predicted, actual))
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1,
            "support": int(tp + fn), "predicted_count": int(tp + fp)}


def mean_brier(probabilities: list[float], correct: list[bool]) -> float | None:
    """Mean (p - o)^2 where o == 1 when the stated direction was right."""
    if not probabilities or len(probabilities) != len(correct):
        return None
    return float(np.mean([(p - (1.0 if c else 0.0)) ** 2
                          for p, c in zip(probabilities, correct)]))


def calibration_curve(probabilities: list[float], correct: list[bool],
                      bins: int = 5) -> list[dict]:
    """Bucket predictions by stated probability and report the hit rate.

    The question this answers: when the model says 70%, is it right about 70%
    of the time? A model can have good accuracy and terrible calibration, and
    only calibration tells you whether the probability means anything.
    """
    if not probabilities or len(probabilities) != len(correct):
        return []
    edges = np.linspace(0.0, 1.0, bins + 1)
    out: list[dict] = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        idx = [j for j, p in enumerate(probabilities)
               if (p >= lo and (p < hi or (i == bins - 1 and p <= hi)))]
        if not idx:
            out.append({"bin_lower": round(float(lo), 2), "bin_upper": round(float(hi), 2),
                        "n": 0, "mean_predicted": None, "observed_rate": None})
            continue
        out.append({
            "bin_lower": round(float(lo), 2),
            "bin_upper": round(float(hi), 2),
            "n": len(idx),
            "mean_predicted": round(float(np.mean([probabilities[j] for j in idx])), 4),
            "observed_rate": round(float(np.mean([1.0 if correct[j] else 0.0 for j in idx])), 4),
        })
    return out


def roc_auc(scores: list[float], labels: list[int]) -> float | None:
    """AUC via the rank (Mann-Whitney U) identity, with tie handling.

    Implemented directly rather than via sklearn so it returns None on a
    single-class input instead of raising -- which is the common case early
    on, when every resolved prediction happens to have been correct.
    """
    if not scores or len(scores) != len(labels):
        return None
    pos = sum(1 for l in labels if l == 1)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return None
    order = np.argsort(np.asarray(scores, dtype=float), kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    sorted_scores = np.asarray(scores, dtype=float)[order]
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0     # average rank for the tied block
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    rank_sum_pos = sum(ranks[i] for i, l in enumerate(labels) if l == 1)
    return float((rank_sum_pos - pos * (pos + 1) / 2.0) / (pos * neg))


def evaluate_classification(predicted: list[str], actual: list[str],
                            probabilities: list[float],
                            labels: tuple[str, ...]) -> ClassificationMetrics:
    correct = [p == a for p, a in zip(predicted, actual)]
    per_class = {label: precision_recall_f1(predicted, actual, label) for label in labels}
    f1s = [v["f1"] for v in per_class.values() if v["f1"] is not None]
    return ClassificationMetrics(
        n=len(predicted),
        accuracy=direction_accuracy(predicted, actual),
        per_class=per_class,
        macro_f1=float(np.mean(f1s)) if f1s else None,
        brier=mean_brier(probabilities, correct),
        # Discrimination framing: does a higher stated probability actually
        # correspond to a higher chance of being right?
        roc_auc=roc_auc(probabilities, [1 if c else 0 for c in correct]),
        calibration=calibration_curve(probabilities, correct),
    )


# --- regression / ranking (career side) --------------------------------------

def mean_absolute_error(predicted: list[float], actual: list[float]) -> float | None:
    if not predicted or len(predicted) != len(actual):
        return None
    return float(np.mean([abs(p - a) for p, a in zip(predicted, actual)]))


def trend_correlation(predicted: list[float], actual: list[float]) -> float | None:
    """Pearson correlation; None when either series is constant."""
    if len(predicted) < 3 or len(predicted) != len(actual):
        return None
    p = np.asarray(predicted, dtype=float)
    a = np.asarray(actual, dtype=float)
    if p.std() == 0 or a.std() == 0:
        return None
    corr = float(np.corrcoef(p, a)[0, 1])
    return corr if math.isfinite(corr) else None


def ranking_stability(previous: list[str], current: list[str], k: int = 10) -> float | None:
    """Overlap of the top-k between two consecutive rankings, in [0, 1].

    A recommender whose top-10 turns over completely every day is noise
    wearing a ranking's clothes; one that never changes is not responding to
    the world. This is the diagnostic for that axis, and it is reported
    rather than optimized -- the right value depends on the domain.
    """
    if not previous or not current:
        return None
    prev_k, cur_k = set(previous[:k]), set(current[:k])
    denom = min(len(prev_k), len(cur_k))
    return float(len(prev_k & cur_k) / denom) if denom else None
