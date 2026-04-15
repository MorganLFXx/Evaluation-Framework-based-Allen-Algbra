import json
import os
import random
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Sequence, Tuple

import torch

from probing.anchors import char_span_to_token_span, mean_pool_span
from probing.conflict_detect_example import (
    build_question,
    get_whole_rels,
    locate_conflict,
)
from probing.eval_ab import (
    compare_ab_with_bootstrap,
    metric_accuracy,
    paired_bootstrap_diff,
)
from probing.model_inference import HiddenStateExtractor, HiddenStateExtractorConfig
from probing.train_probe import (
    ProbeTrainConfig,
    evaluate_linear_probe,
    predict_linear_probe,
    train_linear_probe,
)


@dataclass
class Stage1Config:
    dataset_path: str
    model_path: str = "/data/zhk/models/qwen-3.5-9b"
    output_dir: str = "outputs/stage1_probe"
    max_samples: int = 200
    layer_spec: str = "-1,-2,-3,-4"
    test_ratio: float = 0.2
    seed: int = 42
    device: str = "auto"
    dtype: str = "auto"
    max_length: int = 4096
    n_bootstrap: int = 1000
    bootstrap_alpha: float = 0.05
    probe_lr: float = 0.05
    probe_epochs: int = 300
    save_feature_cache: bool = True


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _dump_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_layer_spec(layer_spec: str, num_layers: int) -> List[int]:
    spec = (layer_spec or "").strip().lower()
    if spec in {"", "all"}:
        return list(range(1, num_layers + 1))

    layers: List[int] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        idx = int(item)
        if idx < 0:
            idx = num_layers + 1 + idx
        if idx <= 0 or idx > num_layers:
            raise ValueError(
                f"Invalid layer index {item} -> {idx}. Valid range is [1, {num_layers}]"
            )
        layers.append(idx)

    if not layers:
        raise ValueError("No valid layers parsed from layer_spec")

    return sorted(set(layers))


def _split_sample_ids(
    sample_ids: Sequence[int], test_ratio: float, seed: int
) -> Tuple[List[int], List[int]]:
    ids = list(sample_ids)
    rng = random.Random(seed)
    rng.shuffle(ids)

    if not ids:
        return [], []

    n_test = max(1, int(len(ids) * test_ratio))
    if n_test >= len(ids):
        n_test = max(1, len(ids) // 3)

    test_ids = ids[:n_test]
    train_ids = ids[n_test:]
    if not train_ids:
        train_ids = test_ids[:]
    return train_ids, test_ids


def _dedupe_triples(
    triples: Sequence[Tuple[str, str, str]],
) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    seen = set()
    for tri in triples:
        if len(tri) != 3:
            continue
        key = (tri[0], tri[1], tri[2])
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _find_anchor_span_for_pair(prompt_text: str, e1: str, e2: str):
    cursor = 0
    for line in prompt_text.splitlines(True):
        start = cursor
        end = cursor + len(line)
        if e1 in line and e2 in line:
            return (start, end)
        cursor = end

    p1 = prompt_text.find(e1)
    p2 = prompt_text.find(e2)
    if p1 >= 0 and p2 >= 0:
        s = min(p1, p2)
        e = max(p1 + len(e1), p2 + len(e2))
        return (s, e)

    if p1 >= 0:
        return (p1, min(len(prompt_text), p1 + max(24, len(e1))))
    if p2 >= 0:
        return (p2, min(len(prompt_text), p2 + max(24, len(e2))))
    return None


def _instance_key(sample_id: int, triple: Tuple[str, str, str]) -> str:
    return f"{sample_id}|{triple[0]}|{triple[1]}|{triple[2]}"


def _sample_id(sample: Dict, fallback: int) -> int:
    return int(sample.get("id", fallback))


def _extract_group_records(
    sample: Dict,
    sample_idx: int,
    group: str,
    shuffle: bool,
    extractor: HiddenStateExtractor,
    selected_layers: Sequence[int],
    seed: int,
) -> List[Dict]:
    sid = _sample_id(sample, sample_idx)

    random.seed(seed + sid * 131 + (17 if group == "treatment" else 0))
    messages = build_question(sample, shuffle=shuffle)

    rendered_prompt = extractor.render_messages(messages)
    extracted = extractor.extract_from_text(
        rendered_prompt, layer_indices=selected_layers
    )

    conflict_pairs = locate_conflict(sample)
    conflict_pairs = _dedupe_triples(conflict_pairs[1:]) # 传入除第一条以外的, 因为第一条是被隐藏的冲突关系
    if len(conflict_pairs) < 3:
        return []

    whole_rels = _dedupe_triples(get_whole_rels(sample, conflict_pairs))
    all_rels = _dedupe_triples(conflict_pairs + whole_rels)

    stage1_basic = _dedupe_triples(conflict_pairs[1:3])
    stage1_basic_rank = {tri: idx for idx, tri in enumerate(stage1_basic)}
    conflict_triple = conflict_pairs[0]

    offsets = extracted["offset_mapping"]
    records: List[Dict] = []

    for triple in all_rels:
        anchor_span = _find_anchor_span_for_pair(rendered_prompt, triple[0], triple[1])
        token_span = (
            char_span_to_token_span(offsets, anchor_span)
            if anchor_span is not None
            else None
        )

        for layer in selected_layers:
            feat = mean_pool_span(extracted["layer_hidden"][layer], token_span).tolist()
            records.append(
                {
                    "sample_id": sid,
                    "group": group,
                    "layer": int(layer),
                    "e1": triple[0],
                    "e2": triple[1],
                    "rel": triple[2],
                    "instance_key": _instance_key(sid, triple),
                    "feature": feat,
                    "stage1_label": 1 if triple in stage1_basic else 0,
                    "is_stage1_basic": triple in stage1_basic,
                    "basic_rank": int(stage1_basic_rank.get(triple, -1)),
                    "is_conflict_pair": triple == conflict_triple,
                    "is_global": triple in whole_rels,
                }
            )

    return records


def _collect_relation_records(config: Stage1Config) -> Dict:
    samples = _read_json(config.dataset_path)
    if not isinstance(samples, list):
        raise ValueError("dataset_path must point to a JSON list")

    if config.max_samples > 0:
        samples = samples[: config.max_samples]

    extractor = HiddenStateExtractor(
        HiddenStateExtractorConfig(
            model_path=config.model_path,
            device=config.device,
            dtype=config.dtype,
            max_length=config.max_length,
        )
    )
    num_layers = int(extractor.model.config.num_hidden_layers)
    selected_layers = _parse_layer_spec(config.layer_spec, num_layers)

    records: List[Dict] = []
    for idx, sample in enumerate(samples):
        if "conflict_no" not in sample.get("target", {}):
            continue

        records.extend(
            _extract_group_records(
                sample=sample,
                sample_idx=idx,
                group="control",
                shuffle=False,
                extractor=extractor,
                selected_layers=selected_layers,
                seed=config.seed,
            )
        )
        records.extend(
            _extract_group_records(
                sample=sample,
                sample_idx=idx,
                group="treatment",
                shuffle=True,
                extractor=extractor,
                selected_layers=selected_layers,
                seed=config.seed,
            )
        )

    sample_ids_control = {r["sample_id"] for r in records if r["group"] == "control"}
    sample_ids_treat = {r["sample_id"] for r in records if r["group"] == "treatment"}
    common_sample_ids = sorted(sample_ids_control & sample_ids_treat)

    return {
        "records": records,
        "selected_layers": selected_layers,
        "num_layers": num_layers,
        "common_sample_ids": common_sample_ids,
    }


def _filter_records(
    records: Sequence[Dict],
    *,
    layer: int,
    group: str,
    sample_ids: Sequence[int],
    predicate: Callable[[Dict], bool],
) -> List[Dict]:
    ids = set(sample_ids)
    return [
        r
        for r in records
        if r["layer"] == layer
        and r["group"] == group
        and r["sample_id"] in ids
        and predicate(r)
    ]


def _class_count(labels: Sequence[int]) -> int:
    return len(set(labels))


def _build_label_map(labels: Sequence[str]) -> Dict[str, int]:
    uniq = sorted(set(labels))
    return {name: i for i, name in enumerate(uniq)}


def _fit_probe_for_group(
    train_records: Sequence[Dict],
    test_records: Sequence[Dict],
    all_records: Sequence[Dict],
    *,
    label_fn: Callable[[Dict], int],
    num_classes: int,
    config: Stage1Config,
) -> Dict:
    if not train_records or not test_records:
        return {
            "skipped": True,
            "reason": "empty_train_or_test",
        }

    x_train = [r["feature"] for r in train_records]
    y_train = [int(label_fn(r)) for r in train_records]
    x_test = [r["feature"] for r in test_records]
    y_test = [int(label_fn(r)) for r in test_records]

    if _class_count(y_train) < min(num_classes, 2):
        return {
            "skipped": True,
            "reason": "insufficient_train_classes",
        }

    probe_cfg = ProbeTrainConfig(
        num_classes=num_classes,
        lr=config.probe_lr,
        epochs=config.probe_epochs,
        seed=config.seed,
    )

    model = train_linear_probe(x_train, y_train, probe_cfg)
    eval_result = evaluate_linear_probe(model, x_test, y_test)

    pred_test, score_test = predict_linear_probe(model, x_test)
    pred_all, score_all = predict_linear_probe(
        model, [r["feature"] for r in all_records]
    )

    test_predictions = []
    for i, rec in enumerate(test_records):
        test_predictions.append(
            {
                "key": rec["instance_key"],
                "sample_id": rec["sample_id"],
                "layer": rec["layer"],
                "group": rec["group"],
                "y_true": int(y_test[i]),
                "y_pred": int(pred_test[i]),
                "y_score": float(score_test[i]),
                "basic_rank": int(rec.get("basic_rank", -1)),
            }
        )

    all_predictions = []
    for i, rec in enumerate(all_records):
        all_predictions.append(
            {
                "key": rec["instance_key"],
                "sample_id": rec["sample_id"],
                "layer": rec["layer"],
                "group": rec["group"],
                "y_true": int(label_fn(rec)),
                "y_pred": int(pred_all[i]),
                "y_score": float(score_all[i]),
                "basic_rank": int(rec.get("basic_rank", -1)),
            }
        )

    return {
        "skipped": False,
        "model": model,
        "metrics": eval_result.metrics,
        "n_train": len(train_records),
        "n_test": len(test_records),
        "predictions_test": test_predictions,
        "predictions_all": all_predictions,
    }


def _align_predictions(control_preds: Sequence[Dict], treatment_preds: Sequence[Dict]):
    c_map = {p["key"]: p for p in control_preds}
    t_map = {p["key"]: p for p in treatment_preds}
    keys = sorted(set(c_map.keys()) & set(t_map.keys()))

    if not keys:
        return [], {}, {}

    control = {
        "y_true": [int(c_map[k]["y_true"]) for k in keys],
        "y_pred": [int(c_map[k]["y_pred"]) for k in keys],
        "y_score": [float(c_map[k]["y_score"]) for k in keys],
    }
    treatment = {
        "y_true": [int(t_map[k]["y_true"]) for k in keys],
        "y_pred": [int(t_map[k]["y_pred"]) for k in keys],
        "y_score": [float(t_map[k]["y_score"]) for k in keys],
    }
    return keys, control, treatment


def _ab_accuracy_only(
    keys: Sequence[str],
    control: Dict[str, Sequence],
    treatment: Dict[str, Sequence],
    config: Stage1Config,
) -> Dict[str, float]:
    if not keys:
        return {
            "control": 0.0,
            "treatment": 0.0,
            "diff": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
        }

    res = paired_bootstrap_diff(
        keys=keys,
        control_true=control["y_true"],
        control_pred=control["y_pred"],
        control_score=control["y_score"],
        treatment_true=treatment["y_true"],
        treatment_pred=treatment["y_pred"],
        treatment_score=treatment["y_score"],
        metric_fn=metric_accuracy,
        n_bootstrap=config.n_bootstrap,
        alpha=config.bootstrap_alpha,
        seed=config.seed,
    )
    return {
        "control": float(res.control),
        "treatment": float(res.treatment),
        "diff": float(res.diff),
        "ci_low": float(res.ci_low),
        "ci_high": float(res.ci_high),
    }


def _run_stage1_layer(
    records: Sequence[Dict],
    layer: int,
    train_ids: Sequence[int],
    test_ids: Sequence[int],
    config: Stage1Config,
):
    group_outputs: Dict[str, Dict] = {}
    all_preds: Dict[str, List[Dict]] = {}

    for group in ["control", "treatment"]:
        train_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=train_ids,
            predicate=lambda r: True,
        )
        test_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=test_ids,
            predicate=lambda r: True,
        )
        all_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=list(train_ids) + list(test_ids),
            predicate=lambda r: True,
        )

        output = _fit_probe_for_group(
            train_records,
            test_records,
            all_records,
            label_fn=lambda r: int(r["stage1_label"]),
            num_classes=2,
            config=config,
        )
        group_outputs[group] = output
        all_preds[group] = output.get("predictions_all", [])

    c_test = group_outputs.get("control", {}).get("predictions_test", [])
    t_test = group_outputs.get("treatment", {}).get("predictions_test", [])
    keys, c_pack, t_pack = _align_predictions(c_test, t_test)

    if keys:
        ab_diff = compare_ab_with_bootstrap(
            keys=keys,
            control=c_pack,
            treatment=t_pack,
            n_bootstrap=config.n_bootstrap,
            alpha=config.bootstrap_alpha,
            seed=config.seed,
        )
    else:
        ab_diff = {}

    return {
        "groups": {
            g: {
                "skipped": group_outputs[g].get("skipped", True),
                "reason": group_outputs[g].get("reason", ""),
                "metrics": group_outputs[g].get("metrics", {}),
                "n_train": group_outputs[g].get("n_train", 0),
                "n_test": group_outputs[g].get("n_test", 0),
            }
            for g in ["control", "treatment"]
        },
        "ab_diff": ab_diff,
        "predictions_all": all_preds,
    }


def _run_stage3_layer(
    records: Sequence[Dict],
    layer: int,
    train_ids: Sequence[int],
    test_ids: Sequence[int],
    config: Stage1Config,
    *,
    predicate: Callable[[Dict], bool],
    label_map: Dict[str, int],
):
    group_outputs: Dict[str, Dict] = {}
    all_preds: Dict[str, List[Dict]] = {}

    for group in ["control", "treatment"]:
        train_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=train_ids,
            predicate=predicate,
        )
        test_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=test_ids,
            predicate=predicate,
        )
        all_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=list(train_ids) + list(test_ids),
            predicate=predicate,
        )

        output = _fit_probe_for_group(
            train_records,
            test_records,
            all_records,
            label_fn=lambda r: int(label_map[r["rel"]]),
            num_classes=len(label_map),
            config=config,
        )
        group_outputs[group] = output
        all_preds[group] = output.get("predictions_all", [])

    c_test = group_outputs.get("control", {}).get("predictions_test", [])
    t_test = group_outputs.get("treatment", {}).get("predictions_test", [])
    keys, c_pack, t_pack = _align_predictions(c_test, t_test)
    ab_accuracy = _ab_accuracy_only(keys, c_pack, t_pack, config)

    return {
        "groups": {
            g: {
                "skipped": group_outputs[g].get("skipped", True),
                "reason": group_outputs[g].get("reason", ""),
                "metrics": group_outputs[g].get("metrics", {}),
                "n_train": group_outputs[g].get("n_train", 0),
                "n_test": group_outputs[g].get("n_test", 0),
            }
            for g in ["control", "treatment"]
        },
        "ab_accuracy": ab_accuracy,
        "predictions_all": all_preds,
    }


def _stage3_recovery_after_stage1(
    layers: Sequence[int],
    stage1_preds_by_layer: Dict[int, Dict[str, List[Dict]]],
    stage3_preds_by_layer: Dict[int, Dict[str, List[Dict]]],
) -> Dict[str, Dict[str, Dict]]:
    sorted_layers = sorted(layers)

    stage1_idx: Dict[Tuple[str, int, int], Dict[int, int]] = {}
    for layer in sorted_layers:
        for group, rows in stage1_preds_by_layer.get(layer, {}).items():
            for row in rows:
                sid = int(row["sample_id"])
                rank = int(row.get("basic_rank", -1))
                if rank < 0:
                    continue
                key = (group, sid, layer)
                stage1_idx.setdefault(key, {})[rank] = int(row["y_pred"])

    detected_layer: Dict[Tuple[str, int], int] = {}
    all_group_sample = sorted({(k[0], k[1]) for k in stage1_idx.keys()})
    for group, sid in all_group_sample:
        for layer in sorted_layers:
            preds = stage1_idx.get((group, sid, layer), {})
            if 0 in preds and 1 in preds and preds[0] == 1 and preds[1] == 1:
                detected_layer[(group, sid)] = layer
                break

    stage3_idx: Dict[Tuple[str, int, int], List[Tuple[int, int]]] = {}
    for layer in sorted_layers:
        for group, rows in stage3_preds_by_layer.get(layer, {}).items():
            for row in rows:
                sid = int(row["sample_id"])
                key = (group, sid, layer)
                stage3_idx.setdefault(key, []).append(
                    (int(row["y_true"]), int(row["y_pred"]))
                )

    output: Dict[str, Dict[str, Dict]] = {"control": {}, "treatment": {}}
    for (group, sid), start_layer in detected_layer.items():
        trace = []
        for layer in sorted_layers:
            if layer < start_layer:
                continue
            pairs = stage3_idx.get((group, sid, layer), [])
            if not pairs:
                continue
            correct = sum(1 for yt, yp in pairs if yt == yp)
            total = len(pairs)
            ratio = correct / total if total else 0.0
            trace.append(
                {
                    "layer": layer,
                    "recovered": correct,
                    "total": total,
                    "ratio": ratio,
                }
            )

        max_ratio = max((x["ratio"] for x in trace), default=0.0)
        output[group][str(sid)] = {
            "detected_layer": start_layer,
            "trace": trace,
            "max_ratio": max_ratio,
        }

    return output


def run_pipeline(config: Stage1Config) -> Dict:
    _ensure_dir(config.output_dir)

    collected = _collect_relation_records(config)
    records = collected["records"]
    selected_layers = collected["selected_layers"]

    if not records:
        raise ValueError(
            "No relation records extracted. Check dataset format and helpers."
        )

    common_sample_ids = collected["common_sample_ids"]
    train_ids, test_ids = _split_sample_ids(
        common_sample_ids, config.test_ratio, config.seed
    )

    if config.save_feature_cache:
        torch.save(
            {
                "records": records,
                "selected_layers": selected_layers,
                "num_layers": collected["num_layers"],
                "train_ids": train_ids,
                "test_ids": test_ids,
            },
            os.path.join(config.output_dir, "stage1_features.pt"),
        )

    stage3_label_map = _build_label_map([r["rel"] for r in records if r["is_global"]])

    stage1_layers: Dict[str, Dict] = {}
    stage3_layers: Dict[str, Dict] = {}

    stage1_preds_by_layer: Dict[int, Dict[str, List[Dict]]] = {}
    stage3_preds_by_layer: Dict[int, Dict[str, List[Dict]]] = {}

    for layer in selected_layers:
        st1 = _run_stage1_layer(records, layer, train_ids, test_ids, config)
        stage1_layers[str(layer)] = {
            "groups": st1["groups"],
            "ab_diff": st1["ab_diff"],
        }
        stage1_preds_by_layer[layer] = st1["predictions_all"]

        st3 = _run_stage3_layer(
            records,
            layer,
            train_ids,
            test_ids,
            config,
            predicate=lambda r: bool(r["is_global"]),
            label_map=stage3_label_map,
        )
        stage3_layers[str(layer)] = {
            "groups": st3["groups"],
            "ab_accuracy": st3["ab_accuracy"],
        }
        stage3_preds_by_layer[layer] = st3["predictions_all"]

    recovery = _stage3_recovery_after_stage1(
        selected_layers,
        stage1_preds_by_layer,
        stage3_preds_by_layer,
    )

    report = {
        "config": asdict(config),
        "num_records": len(records),
        "num_layers_total": collected["num_layers"],
        "selected_layers": selected_layers,
        "split": {
            "n_common_samples": len(common_sample_ids),
            "n_train_samples": len(train_ids),
            "n_test_samples": len(test_ids),
        },
        "labels": {
            "stage3_relation_classes": stage3_label_map,
        },
        "stages": {
            "stage1": {
                "definition": "二分类：检查冲突关系组中的两条基本关系是否在该层被判别出来",
                "layers": stage1_layers,
            },
            "stage3": {
                "definition": "从Stage1检测层开始，统计后续层对全局关系集合的恢复比例",
                "layers": stage3_layers,
                "recovery_after_stage1": recovery,
            },
        },
    }

    _dump_json(os.path.join(config.output_dir, "stage1_report.json"), report)
    return report
