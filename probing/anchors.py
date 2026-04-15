from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import torch


CharSpan = Tuple[int, int]
TokenSpan = Tuple[int, int]


@dataclass
class AnchorConfig:
    reasoning_window_chars: int = 64


def _find_next_span(text: str, needle: str, start_pos: int) -> Optional[CharSpan]:
    idx = text.find(needle, start_pos)
    if idx < 0:
        return None
    return (idx, idx + len(needle))


def find_hint_char_spans(
    prompt_text: str, hints: Sequence[str]
) -> List[Optional[CharSpan]]:
    spans: List[Optional[CharSpan]] = []
    cursor = 0
    for hint in hints:
        # Primary strategy: scan forward to preserve hint order.
        span = _find_next_span(prompt_text, hint, cursor)
        if span is None:
            # Fallback: search from start in case formatting changed order.
            span = _find_next_span(prompt_text, hint, 0)
        if span is not None:
            cursor = span[1]
        spans.append(span)
    return spans


def find_reasoning_phase_span(
    prompt_text: str, config: AnchorConfig
) -> Optional[CharSpan]:
    markers = [
        "2. Reasoning Phase",
        "Reasoning Phase",
        "reasoning phase",
    ]
    marker_pos = -1
    marker_len = 0
    for marker in markers:
        marker_pos = prompt_text.find(marker)
        if marker_pos >= 0:
            marker_len = len(marker)
            break

    if marker_pos < 0:
        return None

    start = marker_pos
    end = min(len(prompt_text), marker_pos + marker_len + config.reasoning_window_chars)
    return (start, end)


def char_span_to_token_span(
    offset_mapping: Sequence[Tuple[int, int]], char_span: CharSpan
) -> Optional[TokenSpan]:
    char_start, char_end = char_span
    token_ids: List[int] = []
    for i, (tok_start, tok_end) in enumerate(offset_mapping):
        # Skip special tokens or empty spans with zero-length offsets.
        if tok_end <= tok_start:
            continue
        # Keep tokens that overlap with the char span.
        if tok_end <= char_start:
            continue
        if tok_start >= char_end:
            continue
        token_ids.append(i)

    if not token_ids:
        return None
    return (token_ids[0], token_ids[-1] + 1)


def mean_pool_span(
    hidden_state: torch.Tensor, token_span: Optional[TokenSpan]
) -> torch.Tensor:
    if token_span is None:
        # Return zero vector when anchor cannot be aligned.
        return torch.zeros(hidden_state.shape[-1], dtype=hidden_state.dtype)

    start, end = token_span
    if start >= end or start < 0 or end > hidden_state.shape[0]:
        return torch.zeros(hidden_state.shape[-1], dtype=hidden_state.dtype)

    # Fixed-size representation for variable-length token spans.
    return hidden_state[start:end].mean(dim=0)


def build_stage1_anchor_spans(
    prompt_text: str,
    hints: Sequence[str],
    config: Optional[AnchorConfig] = None,
) -> Dict[str, List[Optional[CharSpan]]]:
    cfg = config or AnchorConfig()
    hint_spans = find_hint_char_spans(prompt_text, hints)
    reasoning_span = find_reasoning_phase_span(prompt_text, cfg)
    return {
        "hint_spans": hint_spans,
        "reasoning_span": [reasoning_span],
    }
