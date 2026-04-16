import argparse
import json
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from probing.conflict_detect_example import (
    build_question,
    get_whole_rels,
    locate_conflict,
    get_key_rels,
)


@dataclass
class AttentionFlowConfig:
    model_path: str
    dataset_path: Optional[str] = None
    sample_index: int = 0
    output_dir: str = "outputs/attention_flow"
    device: str = "auto"
    dtype: str = "auto"
    max_length: int = 4096
    layer: int = -1
    seed: int = 42
    top_k: int = 8
    head_for_heatmap: str = "max_drop"


def _resolve_device(device_name: str) -> str:
    if device_name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device_name


def _resolve_dtype(dtype_name: str):
    if dtype_name == "auto":
        return None
    mapping = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }
    if dtype_name not in mapping:
        raise ValueError(f"Unsupported dtype: {dtype_name}")
    return mapping[dtype_name]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_layer_index(layer: int, num_layers: int) -> int:
    if layer < 0:
        idx = num_layers + layer
    elif 1 <= layer <= num_layers:
        idx = layer - 1
    else:
        idx = layer
    if idx < 0 or idx >= num_layers:
        raise ValueError(
            f"Invalid layer index {layer}. Valid range: [1, {num_layers}] or [-{num_layers}, -1]"
        )
    return idx


def _line_spans(text: str) -> List[Tuple[int, int, str]]:
    spans = []
    cursor = 0
    for line in text.splitlines(True):
        start = cursor
        end = cursor + len(line)
        spans.append((start, end, line))
        cursor = end
    return spans


def _find_event_spans_in_pair_line(
    prompt_text: str, event_a: str, event_b: str
) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    for start, end, line in _line_spans(prompt_text):
        if event_a in line and event_b in line:
            a_pos = prompt_text.find(event_a, start, end)
            b_pos = prompt_text.find(event_b, start, end)
            a_span = None if a_pos < 0 else (a_pos, a_pos + len(event_a))
            b_span = None if b_pos < 0 else (b_pos, b_pos + len(event_b))
            return a_span, b_span

    a_pos = prompt_text.find(event_a)
    b_pos = prompt_text.find(event_b)
    a_span = None if a_pos < 0 else (a_pos, a_pos + len(event_a))
    b_span = None if b_pos < 0 else (b_pos, b_pos + len(event_b))
    return a_span, b_span


def _char_span_to_token_indices(
    offset_mapping: Sequence[Tuple[int, int]],
    char_span: Optional[Tuple[int, int]],
) -> List[int]:
    if char_span is None:
        return []
    char_start, char_end = char_span
    token_ids: List[int] = []
    for i, (tok_start, tok_end) in enumerate(offset_mapping):
        # Skip special tokens or empty spans with zero-length offsets.
        if tok_end <= tok_start:
            continue
        if tok_end <= char_start:
            continue
        if tok_start >= char_end:
            continue
        token_ids.append(i)
    return token_ids


def _mean_attn(attn: torch.Tensor, idx_x: List[int], idx_y: List[int]) -> float:
    if not idx_x or not idx_y:
        return 0.0
    sub = attn[idx_x][:, idx_y]
    if sub.numel() == 0:
        return 0.0
    return float(sub.mean().item())


def _build_event_list(rels: Sequence[Tuple[str, str, str]]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for l, r, _ in rels:
        for item in (l, r):
            if item not in seen:
                seen.add(item)
                ordered.append(item)
    return ordered


class AttentionFlowExtractor:
    def __init__(self, config: AttentionFlowConfig):
        self.config = config
        self.device = _resolve_device(config.device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            config.model_path,
            trust_remote_code=False,
            use_fast=True,
        )
        torch_dtype = _resolve_dtype(config.dtype)
        model_kwargs = {
            "trust_remote_code": False,
            "output_attentions": True,
        }
        if torch_dtype is not None:
            model_kwargs["torch_dtype"] = torch_dtype

        self.model = AutoModelForCausalLM.from_pretrained(
            config.model_path, **model_kwargs
        )
        self.model.to(self.device)
        self.model.eval()

    def render_messages(self, messages: Sequence[Dict[str, str]]) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )
        lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            lines.append(f"[{role}]\n{content}")
        lines.append("[ASSISTANT]\n")
        return "\n\n".join(lines)

    def extract_attention(self, text: str) -> Dict:
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_length,
            return_offsets_mapping=True,
        )
        offset_mapping = encoded.pop("offset_mapping", None)
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self.model(
                **encoded,
                output_attentions=True,
                use_cache=False,
                return_dict=True,
            )

        attentions = outputs.attentions
        if attentions is None:
            raise RuntimeError("Model did not return attentions")

        attention_mask = encoded["attention_mask"][0].detach().cpu()
        seq_len = int(attention_mask.sum().item())

        if offset_mapping is None:
            offsets = []
        elif hasattr(offset_mapping, "detach"):
            offsets = offset_mapping[0][:seq_len].detach().cpu().tolist()
        else:
            offsets = offset_mapping[0][:seq_len]

        layer_attn = [
            attn[0, :, :seq_len, :seq_len].detach().cpu() for attn in attentions
        ]

        return {
            "attentions": layer_attn,
            "offset_mapping": offsets,
            "num_layers": len(layer_attn),
        }


def _extract_flow_for_extracted(
    prompt_text: str,
    rels: Sequence[Tuple[str, str, str]],
    extracted: Dict,
    layer_idx: int,
) -> Dict:
    layer_attn = extracted["attentions"][layer_idx]
    offsets = extracted["offset_mapping"]

    num_heads = layer_attn.shape[0]
    results: Dict[Tuple[str, str], List[float]] = {}

    for e1, e2, _ in rels:
        span1, span2 = _find_event_spans_in_pair_line(prompt_text, e1, e2)
        idx1 = _char_span_to_token_indices(offsets, span1)
        idx2 = _char_span_to_token_indices(offsets, span2)

        flows: List[float] = []
        for h in range(num_heads):
            attn = layer_attn[h]
            a_to_b = _mean_attn(attn, idx1, idx2)
            b_to_a = _mean_attn(attn, idx2, idx1)
            flows.append(a_to_b + b_to_a)
        results[(e1, e2)] = flows

    return {
        "flows": results,
        "num_heads": num_heads,
    }


def _compute_drop_pct(control: float, treatment: float, eps: float = 1e-12) -> float:
    base = max(abs(control), eps)
    return (control - treatment) / base * 100.0


def _select_head_for_heatmap(
    drop_by_head: Sequence[float],
    strategy: str,
) -> int:
    if strategy == "max_drop":
        return int(np.argmax(drop_by_head))
    if strategy == "min_drop":
        return int(np.argmin(drop_by_head))
    if strategy.startswith("head"):
        try:
            return int(strategy.split(":", 1)[1])
        except (ValueError, IndexError):
            pass
    return 0


def _build_flow_matrix(
    events: Sequence[str],
    rel_pairs: Sequence[Tuple[str, str]],
    flows: Dict[Tuple[str, str], List[float]],
    head_idx: int,
) -> np.ndarray:
    idx_map = {e: i for i, e in enumerate(events)}
    mat = np.full((len(events), len(events)), np.nan, dtype=np.float32)
    for e1, e2 in rel_pairs:
        if (e1, e2) not in flows:
            continue
        i = idx_map.get(e1)
        j = idx_map.get(e2)
        if i is None or j is None:
            continue
        mat[i, j] = float(flows[(e1, e2)][head_idx])
    return mat


def _plot_heatmaps(
    events: Sequence[str],
    control_mat: np.ndarray,
    treat_mat: np.ndarray,
    output_path: str,
    title: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vmax = np.nanmax([np.nanmax(control_mat), np.nanmax(treat_mat)])
    vmin = np.nanmin([np.nanmin(control_mat), np.nanmin(treat_mat)])

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), constrained_layout=True)
    for ax, mat, name in zip(axes, [control_mat, treat_mat], ["normal", "shuffled"]):
        im = ax.imshow(mat, cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_title(name)
        ax.set_xticks(range(len(events)))
        ax.set_yticks(range(len(events)))
        ax.set_xticklabels(events, rotation=45, ha="right")
        ax.set_yticklabels(events)
        ax.set_xlabel("Event")
        ax.set_ylabel("Event")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(title)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def run_attention_flow(config: AttentionFlowConfig) -> Dict:
    _ensure_dir(config.output_dir)

    if config.dataset_path:
        samples = _read_json(config.dataset_path)
        if not isinstance(samples, list) or not samples:
            raise ValueError("dataset_path must point to a non-empty JSON list")
        sample = samples[config.sample_index]
    else:
        from probing.conflict_detect_example import example

        sample = example

    extractor = AttentionFlowExtractor(config)

    random.seed(config.seed)
    messages_control = build_question(sample, shuffle=False)
    random.seed(config.seed)
    messages_treat = build_question(sample, shuffle=True)

    prompt_control = extractor.render_messages(messages_control)
    prompt_treat = extractor.render_messages(messages_treat)

    # rels = get_key_rels(sample)
    rels = get_whole_rels(sample)
    rels = [(l, r, rel) for l, r, rel in rels]

    extracted_control = extractor.extract_attention(prompt_control)
    num_layers = int(extracted_control["num_layers"])
    layer_idx = _normalize_layer_index(config.layer, num_layers)

    extracted_treat = extractor.extract_attention(prompt_treat)
    if int(extracted_treat["num_layers"]) != num_layers:
        raise RuntimeError(
            "Attention layer count mismatch between control and treatment"
        )

    control = _extract_flow_for_extracted(
        prompt_control,
        rels,
        extracted_control,
        layer_idx,
    )
    treatment = _extract_flow_for_extracted(
        prompt_treat,
        rels,
        extracted_treat,
        layer_idx,
    )

    num_heads = control["num_heads"]
    if num_heads != treatment["num_heads"]:
        raise RuntimeError("Head count mismatch between control and treatment")

    drop_by_head = [0.0 for _ in range(num_heads)]
    drops_per_pair: Dict[Tuple[str, str], List[float]] = {}

    for pair, control_flow in control["flows"].items():
        treat_flow = treatment["flows"].get(pair, [0.0 for _ in range(num_heads)])
        drop_pct = [
            _compute_drop_pct(control_flow[h], treat_flow[h]) for h in range(num_heads)
        ]
        drops_per_pair[pair] = drop_pct
        for h in range(num_heads):
            drop_by_head[h] += drop_pct[h]

    drop_by_head = [v / max(1, len(rels)) for v in drop_by_head]
    top_k = min(config.top_k, num_heads)
    top_heads = sorted(
        [(h, drop_by_head[h]) for h in range(num_heads)],
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    events = _build_event_list(rels)
    rel_pairs = [(l, r) for l, r, _ in rels]

    head_idx = _select_head_for_heatmap(drop_by_head, config.head_for_heatmap)
    control_mat = _build_flow_matrix(events, rel_pairs, control["flows"], head_idx)
    treat_mat = _build_flow_matrix(events, rel_pairs, treatment["flows"], head_idx)

    heatmap_path = os.path.join(config.output_dir, "attention_flow_heatmap.png")
    _plot_heatmaps(
        events,
        control_mat,
        treat_mat,
        heatmap_path,
        title=f"Attention Flow (layer {layer_idx + 1}, head {head_idx})",
    )

    report = {
        "layer_index": layer_idx,
        "num_heads": num_heads,
        "top_heads": top_heads,
        "drop_by_head": drop_by_head,
        "pairs": [
            {
                "pair": [pair[0], pair[1]],
                "control": control["flows"][pair],
                "treatment": treatment["flows"][pair],
                "drop_pct": drops_per_pair[pair],
            }
            for pair in rel_pairs
        ],
        "heatmap_path": heatmap_path,
        "events": events,
    }

    report_path = os.path.join(config.output_dir, "attention_flow_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Attention flow analysis for event pairs with shuffled prompts"
    )
    model_path = "/data/zhk/models/qwen-3.5-9b"
    # parser.add_argument("--dataset-path", type=str, help="Dataset JSON path")
    dataset_path = "datasets/final6/test_10_final_conflict.json"
    parser.add_argument(
        "--sample-index",
        type=int,
        default=2,
        help="Sample index inside dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/attention_flow",
        help="Output directory",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help='Torch device, e.g. "auto", "cuda:0", "cpu"',
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="auto",
        choices=["auto", "float16", "bfloat16", "float32"],
        help="Model dtype",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=4096,
        help="Tokenizer max_length for prompt truncation",
    )
    parser.add_argument(
        "--layer",
        type=int,
        default=-1,
        help="Layer index (1-based, 0-based, or negative)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for shuffling",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Top-K heads by average drop",
    )
    parser.add_argument(
        "--head-for-heatmap",
        type=str,
        default="max_drop",
        help="Heatmap head strategy: max_drop|min_drop|head:<idx>",
    )
    args = parser.parse_args()

    cfg = AttentionFlowConfig(
        model_path=model_path,
        dataset_path=dataset_path,
        sample_index=args.sample_index,
        output_dir=args.output_dir,
        device=args.device,
        dtype=args.dtype,
        max_length=args.max_length,
        layer=args.layer,
        seed=args.seed,
        top_k=args.top_k,
        head_for_heatmap=args.head_for_heatmap,
    )

    report = run_attention_flow(cfg)
    print(f"Saved report to: {cfg.output_dir}/attention_flow_report.json")
    print(f"Saved heatmap to: {report['heatmap_path']}")


if __name__ == "__main__":
    main()
