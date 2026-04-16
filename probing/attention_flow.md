# Attention Flow Analysis for Shuffled Prompts

This note documents the attention-flow experiment that compares normal vs shuffled prompt order.
It matches the event-pair definitions from probing/conflict_detect_example.py (get_whole_rels)
while keeping attention heads separate (no head-averaging).

## Goal
- For each event-pair (from get_whole_rels), measure attention flow in a chosen layer.
- Compare normal order vs shuffled order prompts.
- Report per-head flow changes and visualize a single head as heatmaps.

## Core Logic
1) Build two prompts
   - Normal order: build_question(sample, shuffle=False)
   - Shuffled order: build_question(sample, shuffle=True)
   - The random seed is fixed so shuffling is deterministic.

2) Run the model with output_attentions=True
   - Keep attention head dimension intact: attentions[layer][head, seq, seq].
   - Only the chosen layer is used for analysis (layer index configurable).

3) Map events to token indices
   - Each event is a string like "M0".
   - The code searches a line containing both events and finds each event span.
   - Using offset_mapping, each event span maps to a set of token indices.
   - This makes the mapping robust to small prompt length changes.

4) Compute attention flow per head
   - For event X and Y, define:
     Attn(X -> Y) = mean(attention[i, j] for i in idx_X for j in idx_Y)
   - Flow(X, Y) = Attn(X -> Y) + Attn(Y -> X)
   - This is computed separately for every head; no head averaging.

5) Compare normal vs shuffled
   - For each head: drop_pct = (control - treatment) / max(|control|, eps) * 100.
   - The code also reports Top-K heads by average drop.

6) Visualization
   - Choose a single head for heatmap (default: head with max average drop).
   - Plot two heatmaps (normal vs shuffled) over the event list.
   - The color encodes Flow(X, Y) for that head.

## Outputs
- outputs/attention_flow/attention_flow_report.json
  - Per-pair flow scores for each head.
  - Per-head average drop, and Top-K heads.
- outputs/attention_flow/attention_flow_heatmap.png
  - Side-by-side heatmaps for normal vs shuffled prompts.

## How to Run
Example (single sample from a dataset):

python -m probing.attention_flow \
  --model-path /data/zhk/models/qwen-3.5-9b \
  --dataset-path datasets/debug_reasoning.json \
  --sample-index 0 \
  --layer -1 \
  --top-k 8

If --dataset-path is omitted, the built-in example in probing/conflict_detect_example.py
is used.

## Notes
- The layer argument accepts 1-based indices, 0-based indices, or negative indices.
  Example: -1 means last layer; 1 means first layer.
- The heatmap uses a single head to avoid any head averaging.
- If an event span cannot be found for a pair, the flow defaults to 0.0.
