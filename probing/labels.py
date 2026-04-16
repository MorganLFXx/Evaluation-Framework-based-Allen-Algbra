from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class Stage1LabelConfig:
    neighbor_window: int = 1


def build_stage1_label_info(sample: Dict, config: Stage1LabelConfig) -> Dict:
    hints = sample.get("hints", [])
    if not hints:
        raise ValueError("Sample has no hints")

    conflict_no = sample.get("target", {}).get("conflict_no")
    if conflict_no is None:
        raise ValueError("Sample has no target.conflict_no")

    core_idx = int(conflict_no) - 1
    if core_idx < 0 or core_idx >= len(hints):
        raise ValueError(
            f"Invalid conflict_no={conflict_no} for hints length={len(hints)}"
        )

    # Neighbor hints are treated as near-core conflict context.
    near_indices: Set[int] = set()
    window = max(0, int(config.neighbor_window))
    for i in range(core_idx - window, core_idx + window + 1):
        if 0 <= i < len(hints) and i != core_idx:
            near_indices.add(i)

    return {
        "core_idx": core_idx,
        "near_indices": sorted(near_indices),
        "neighbor_window": window,
    }


def stage1_binary_label(hint_idx: int, label_info: Dict) -> int:
    # Binary setting: core and near-core are both positive.
    if hint_idx == label_info["core_idx"]:
        return 1
    if hint_idx in set(label_info["near_indices"]):
        return 1
    return 0


def stage1_three_way_label(hint_idx: int, label_info: Dict) -> int:
    # Three-way setting: separate core vs near-core vs others.
    if hint_idx == label_info["core_idx"]:
        return 2
    if hint_idx in set(label_info["near_indices"]):
        return 1
    return 0
