import json
import os
import random
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence, Tuple

import torch

from probing.anchors import (
    char_span_to_token_span,
    find_relation_char_span,
    mean_pool_span,
)
from probing.construct_rels import build_question, get_key_rels, get_whole_rels
from probing.eval_ab import compare_ab_with_bootstrap
from probing.labels import build_key_relation_labels, label_for_triple
from probing.model_inference import HiddenStateExtractor, HiddenStateExtractorConfig
from probing.train_probe import (
    ProbeTrainConfig,
    evaluate_linear_probe,
    predict_linear_probe,
    train_linear_probe,
)


RelationTriple = Tuple[str, str, str]


@dataclass
class ProbePipelineConfig:
    dataset_path: str
    model_path: str = "/data/zhk/models/qwen-3.5-9b"
    output_dir: str = "outputs/probe"
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


# Backward-compatible alias for older imports.
Stage1Config = ProbePipelineConfig


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


def _instance_key(sample_id: int, triple: RelationTriple) -> str:
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

    # Keep treatment shuffle reproducible across runs.
    random.seed(seed + sid * 131 + (17 if group == "treatment" else 0))
    messages = build_question(sample, shuffle=shuffle)
    prompt_text = extractor.render_messages(messages)
    extracted = extractor.extract_from_text(prompt_text, layer_indices=selected_layers)

    label_info = build_key_relation_labels(
        whole_rels=get_whole_rels(sample),
        key_rels=get_key_rels(sample),
    )

    # Binary probing needs both positive and negative classes.
    if not label_info.positives or not label_info.negatives:
        return []

    offsets = extracted["offset_mapping"]
    records: List[Dict] = []

    for triple in label_info.candidates:
        char_span = find_relation_char_span(prompt_text, triple[0], triple[1])
        token_span = (
            char_span_to_token_span(offsets, char_span)
            if char_span is not None
            else None
        )
        label = label_for_triple(triple, label_info.label_map)

        for layer in selected_layers:
            feature = mean_pool_span(
                extracted["layer_hidden"][layer], token_span
            ).tolist()
            records.append(
                {
                    "sample_id": sid,
                    "group": group,
                    "layer": int(layer),
                    "triple": [triple[0], triple[1], triple[2]],
                    "e1": triple[0],
                    "e2": triple[1],
                    "rel": triple[2],
                    "instance_key": _instance_key(sid, triple),
                    "label": int(label),
                    "is_key_relation": bool(label),
                    "feature": feature,
                }
            )

    return records


def _collect_relation_records(config: ProbePipelineConfig) -> Dict:
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
    valid_sample_ids = set()

    for idx, sample in enumerate(samples):
        control_records = _extract_group_records(
            sample=sample,
            sample_idx=idx,
            group="control",
            shuffle=False,
            extractor=extractor,
            selected_layers=selected_layers,
            seed=config.seed,
        )
        treatment_records = _extract_group_records(
            sample=sample,
            sample_idx=idx,
            group="treatment",
            shuffle=True,
            extractor=extractor,
            selected_layers=selected_layers,
            seed=config.seed,
        )

        if not control_records or not treatment_records:
            continue

        records.extend(control_records)
        records.extend(treatment_records)
        valid_sample_ids.add(_sample_id(sample, idx))

    sample_ids_control = {r["sample_id"] for r in records if r["group"] == "control"}
    sample_ids_treat = {r["sample_id"] for r in records if r["group"] == "treatment"}
    common_sample_ids = sorted(sample_ids_control & sample_ids_treat & valid_sample_ids)

    return {
        "records": records,
        "selected_layers": selected_layers,
        "num_layers": num_layers,
        "common_sample_ids": common_sample_ids,
        "num_loaded_samples": len(samples),
    }


def _filter_records(
    records: Sequence[Dict],
    *,
    layer: int,
    group: str,
    sample_ids: Sequence[int],
) -> List[Dict]:
    id_set = set(sample_ids)
    return [
        r
        for r in records
        if r["layer"] == layer and r["group"] == group and r["sample_id"] in id_set
    ]


def _fit_probe_for_group(
    train_records: Sequence[Dict],
    test_records: Sequence[Dict],
    all_records: Sequence[Dict],
    config: ProbePipelineConfig,
) -> Dict:
    if not train_records or not test_records:
        return {
            "skipped": True,
            "reason": "empty_train_or_test",
        }

    x_train = [r["feature"] for r in train_records]
    y_train = [int(r["label"]) for r in train_records]
    x_test = [r["feature"] for r in test_records]
    y_test = [int(r["label"]) for r in test_records]

    if len(set(y_train)) < 2:
        return {
            "skipped": True,
            "reason": "insufficient_train_classes",
        }

    probe_cfg = ProbeTrainConfig(
        num_classes=2,
        lr=config.probe_lr,
        epochs=config.probe_epochs,
        seed=config.seed,
    )

    model = train_linear_probe(x_train, y_train, probe_cfg)
    eval_result = evaluate_linear_probe(model, x_test, y_test)

    pred_test, score_test = predict_linear_probe(model, x_test)

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
            }
        )

    pred_all, score_all = predict_linear_probe(
        model, [r["feature"] for r in all_records]
    )
    all_predictions = []
    for i, rec in enumerate(all_records):
        all_predictions.append(
            {
                "key": rec["instance_key"],
                "sample_id": rec["sample_id"],
                "layer": rec["layer"],
                "group": rec["group"],
                "y_true": int(rec["label"]),
                "y_pred": int(pred_all[i]),
                "y_score": float(score_all[i]),
            }
        )

    return {
        "skipped": False,
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


def _run_layer(
    records: Sequence[Dict],
    layer: int,
    train_ids: Sequence[int],
    test_ids: Sequence[int],
    config: ProbePipelineConfig,
) -> Dict:
    group_outputs: Dict[str, Dict] = {}

    for group in ["control", "treatment"]:
        train_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=train_ids,
        )
        test_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=test_ids,
        )
        all_records = _filter_records(
            records,
            layer=layer,
            group=group,
            sample_ids=list(train_ids) + list(test_ids),
        )

        group_outputs[group] = _fit_probe_for_group(
            train_records=train_records,
            test_records=test_records,
            all_records=all_records,
            config=config,
        )

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
        "n_aligned_test_pairs": len(keys),
    }


def run_pipeline(config: ProbePipelineConfig) -> Dict:
    _ensure_dir(config.output_dir)

    collected = _collect_relation_records(config)
    records = collected["records"]
    selected_layers = collected["selected_layers"]

    if not records:
        raise ValueError(
            "No relation records extracted. Check dataset format and relation helpers."
        )

    common_sample_ids = collected["common_sample_ids"]
    train_ids, test_ids = _split_sample_ids(
        common_sample_ids,
        config.test_ratio,
        config.seed,
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
            os.path.join(config.output_dir, "features.pt"),
        )

    layers_report: Dict[str, Dict] = {}
    for layer in selected_layers:
        layers_report[str(layer)] = _run_layer(
            records=records,
            layer=layer,
            train_ids=train_ids,
            test_ids=test_ids,
            config=config,
        )

    report = {
        "config": asdict(config),
        "num_records": len(records),
        "num_layers_total": collected["num_layers"],
        "selected_layers": selected_layers,
        "num_loaded_samples": collected["num_loaded_samples"],
        "split": {
            "n_common_samples": len(common_sample_ids),
            "n_train_samples": len(train_ids),
            "n_test_samples": len(test_ids),
        },
        "task_definition": {
            "positive": "key_rels",
            "negative": "whole_rels_minus_key_rels",
            "type": "binary_classification",
        },
        "layers": layers_report,
    }

    _dump_json(os.path.join(config.output_dir, "report.json"), report)
    return report
