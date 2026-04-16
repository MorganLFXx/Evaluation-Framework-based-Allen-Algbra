import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple


MetricFn = Callable[[Sequence[int], Sequence[int], Sequence[float]], float]


def metric_accuracy(
    y_true: Sequence[int], y_pred: Sequence[int], _: Sequence[float]
) -> float:
    if not y_true:
        return 0.0
    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    return correct / len(y_true)


def metric_f1_binary(
    y_true: Sequence[int], y_pred: Sequence[int], _: Sequence[float]
) -> float:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def metric_auroc_binary(
    y_true: Sequence[int],
    _: Sequence[int],
    y_score: Sequence[float],
) -> float:
    pos = [s for y, s in zip(y_true, y_score) if y == 1]
    neg = [s for y, s in zip(y_true, y_score) if y == 0]
    if not pos or not neg:
        return 0.5

    win = 0.0
    total = len(pos) * len(neg)
    for p in pos:
        for n in neg:
            if p > n:
                win += 1.0
            elif p == n:
                win += 0.5
    return win / total


@dataclass
class BootstrapDiffResult:
    control: float
    treatment: float
    diff: float
    ci_low: float
    ci_high: float


def paired_bootstrap_diff(
    keys: Sequence[Tuple],
    control_true: Sequence[int],
    control_pred: Sequence[int],
    control_score: Sequence[float],
    treatment_true: Sequence[int],
    treatment_pred: Sequence[int],
    treatment_score: Sequence[float],
    metric_fn: MetricFn,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> BootstrapDiffResult:
    if not keys:
        raise ValueError("paired_bootstrap_diff requires non-empty keys")

    n = len(keys)
    rng = random.Random(seed)

    ctrl_base = metric_fn(control_true, control_pred, control_score)
    trt_base = metric_fn(treatment_true, treatment_pred, treatment_score)
    base_diff = trt_base - ctrl_base

    diffs: List[float] = []
    for _ in range(n_bootstrap):
        idxs = [rng.randrange(0, n) for _ in range(n)]

        c_true = [control_true[i] for i in idxs]
        c_pred = [control_pred[i] for i in idxs]
        c_score = [control_score[i] for i in idxs]

        t_true = [treatment_true[i] for i in idxs]
        t_pred = [treatment_pred[i] for i in idxs]
        t_score = [treatment_score[i] for i in idxs]

        c_val = metric_fn(c_true, c_pred, c_score)
        t_val = metric_fn(t_true, t_pred, t_score)
        diffs.append(t_val - c_val)

    diffs.sort()
    low_idx = int((alpha / 2.0) * len(diffs))
    high_idx = int((1.0 - alpha / 2.0) * len(diffs)) - 1
    low_idx = max(0, min(low_idx, len(diffs) - 1))
    high_idx = max(0, min(high_idx, len(diffs) - 1))

    return BootstrapDiffResult(
        control=ctrl_base,
        treatment=trt_base,
        diff=base_diff,
        ci_low=diffs[low_idx],
        ci_high=diffs[high_idx],
    )


def compare_ab_with_bootstrap(
    keys: Sequence[Tuple],
    control: Dict[str, Sequence],
    treatment: Dict[str, Sequence],
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Dict[str, float]]:
    metrics = {
        "accuracy": metric_accuracy,
        "f1": metric_f1_binary,
        "auroc": metric_auroc_binary,
    }

    output: Dict[str, Dict[str, float]] = {}
    for name, fn in metrics.items():
        result = paired_bootstrap_diff(
            keys=keys,
            control_true=control["y_true"],
            control_pred=control["y_pred"],
            control_score=control["y_score"],
            treatment_true=treatment["y_true"],
            treatment_pred=treatment["y_pred"],
            treatment_score=treatment["y_score"],
            metric_fn=fn,
            n_bootstrap=n_bootstrap,
            alpha=alpha,
            seed=seed,
        )
        output[name] = {
            "control": result.control,
            "treatment": result.treatment,
            "diff": result.diff,
            "ci_low": result.ci_low,
            "ci_high": result.ci_high,
        }
    return output
