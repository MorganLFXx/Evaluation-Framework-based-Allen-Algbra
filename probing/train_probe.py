from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import torch
import torch.nn as nn


@dataclass
class ProbeTrainConfig:
    num_classes: int = 2
    lr: float = 0.05
    weight_decay: float = 0.0
    epochs: int = 300
    seed: int = 42


class LinearProbe(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


@dataclass
class TrainedProbe:
    model: LinearProbe
    feature_mean: torch.Tensor
    feature_std: torch.Tensor
    num_classes: int


@dataclass
class ProbeEvalResult:
    metrics: Dict[str, float]
    predictions: List[int]
    probabilities: List[float]


def _standardize_fit(
    x: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # Fit normalization stats on train set only.
    mean = x.mean(dim=0, keepdim=True)
    std = x.std(dim=0, keepdim=True, unbiased=False)
    # Guard against zero-variance dimensions.
    std = torch.where(std < 1e-6, torch.ones_like(std), std)
    return (x - mean) / std, mean, std


def _standardize_apply(
    x: torch.Tensor, mean: torch.Tensor, std: torch.Tensor
) -> torch.Tensor:
    return (x - mean) / std


def _accuracy(y_true: torch.Tensor, y_pred: torch.Tensor) -> float:
    return float((y_true == y_pred).float().mean().item())


def _precision_recall_f1_binary(
    y_true: torch.Tensor, y_pred: torch.Tensor
) -> Tuple[float, float, float]:
    tp = float(((y_true == 1) & (y_pred == 1)).sum().item())
    fp = float(((y_true == 0) & (y_pred == 1)).sum().item())
    fn = float(((y_true == 1) & (y_pred == 0)).sum().item())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _binary_auroc(y_true: torch.Tensor, y_score: torch.Tensor) -> float:
    # Mann-Whitney U equivalent AUROC computation.
    pos_scores = y_score[y_true == 1]
    neg_scores = y_score[y_true == 0]
    n_pos = int(pos_scores.shape[0])
    n_neg = int(neg_scores.shape[0])
    if n_pos == 0 or n_neg == 0:
        return 0.5

    comparisons = (pos_scores.unsqueeze(1) > neg_scores.unsqueeze(0)).float()
    ties = (pos_scores.unsqueeze(1) == neg_scores.unsqueeze(0)).float() * 0.5
    auc = (comparisons + ties).mean().item()
    return float(auc)


def train_linear_probe(
    x_train: Sequence[Sequence[float]],
    y_train: Sequence[int],
    config: Optional[ProbeTrainConfig] = None,
) -> TrainedProbe:
    cfg = config or ProbeTrainConfig()
    torch.manual_seed(cfg.seed)

    x = torch.tensor(x_train, dtype=torch.float32)
    y = torch.tensor(y_train, dtype=torch.long)

    x_norm, mean, std = _standardize_fit(x)

    model = LinearProbe(input_dim=x.shape[1], num_classes=cfg.num_classes)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
    )
    criterion = nn.CrossEntropyLoss()

    # Simple full-batch optimization is enough for linear probes.
    for _ in range(cfg.epochs):
        optimizer.zero_grad()
        logits = model(x_norm)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()

    return TrainedProbe(
        model=model,
        feature_mean=mean,
        feature_std=std,
        num_classes=cfg.num_classes,
    )


def evaluate_linear_probe(
    trained_probe: TrainedProbe,
    x_test: Sequence[Sequence[float]],
    y_test: Sequence[int],
) -> ProbeEvalResult:
    x = torch.tensor(x_test, dtype=torch.float32)
    y = torch.tensor(y_test, dtype=torch.long)

    x_norm = _standardize_apply(
        x, trained_probe.feature_mean, trained_probe.feature_std
    )

    # Evaluation keeps the same normalization space as training.
    with torch.no_grad():
        logits = trained_probe.model(x_norm)
        probs = torch.softmax(logits, dim=-1)
        pred = probs.argmax(dim=-1)

    metrics: Dict[str, float] = {
        "accuracy": _accuracy(y, pred),
    }

    if trained_probe.num_classes == 2:
        precision, recall, f1 = _precision_recall_f1_binary(y, pred)
        metrics["precision"] = precision
        metrics["recall"] = recall
        metrics["f1"] = f1
        metrics["auroc"] = _binary_auroc(y, probs[:, 1])

        prob_scores = probs[:, 1].tolist()
    else:
        prob_scores = probs.max(dim=-1).values.tolist()

    return ProbeEvalResult(
        metrics=metrics,
        predictions=pred.tolist(),
        probabilities=prob_scores,
    )


def predict_linear_probe(
    trained_probe: TrainedProbe,
    x_data: Sequence[Sequence[float]],
) -> Tuple[List[int], List[float]]:
    if not x_data:
        return [], []

    # Reuse fitted standardization for arbitrary inference batches.
    x = torch.tensor(x_data, dtype=torch.float32)
    x_norm = _standardize_apply(
        x, trained_probe.feature_mean, trained_probe.feature_std
    )

    with torch.no_grad():
        logits = trained_probe.model(x_norm)
        probs = torch.softmax(logits, dim=-1)
        pred = probs.argmax(dim=-1)

    if trained_probe.num_classes == 2:
        prob_scores = probs[:, 1].tolist()
    else:
        prob_scores = probs.max(dim=-1).values.tolist()

    return pred.tolist(), prob_scores
