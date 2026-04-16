# 打乱顺序 Prompt 的注意力流分析

本文档说明如何比较正常顺序与打乱顺序 Prompt 的注意力流向。
事件对来自 probing/conflict_detect_example.py 的 get_key_rels，
并且严格保留 head 维度，不做 head 平均。

## 目标
- 对每个事件对计算指定层的注意力流向强度。
- 对比正常顺序与打乱顺序的差异。
- 输出每个 head 的变化，并用分组柱状图展示单个 head 的对比结果。

## 核心流程
1) 构造两种 Prompt
   - 正常顺序：build_question(sample, shuffle=False)
   - 打乱顺序：build_question(sample, shuffle=True)
   - 固定随机种子，保证打乱可复现。

2) 模型前向并保留注意力
   - output_attentions=True
   - 注意力张量维度为 attentions[layer][head, seq, seq]
   - 只分析指定层。

3) 将事件映射为 token 索引
   - 事件是字符串（如 "M0"）。
   - 先找包含两个事件的行，再定位字符跨度。
   - 结合 offset_mapping 映射到 token 索引集合，适配长度微变。

4) 计算每个 head 的 Flow
   - Attn(X -> Y) = mean(attention[i, j] for i in idx_X for j in idx_Y)
   - Flow(X, Y) = Attn(X -> Y) + Attn(Y -> X)
   - 每个 head 独立计算，不做平均。

5) 对比正常与打乱
   - drop_pct = (control - treatment) / max(|control|, eps) * 100
   - 输出 Top-K 平均下降最大的 head。

6) 可视化（分组柱状图）
   - 选择一个 head（默认平均下降最大）
   - 横轴为事件对，纵轴为 Flow 数值
   - 每组两根柱：normal vs shuffled

## 输出
- outputs/attention_flow/attention_flow_report.json
  - 每个事件对在各 head 的 Flow
  - 每个 head 的平均下降与 Top-K
- outputs/attention_flow/attention_flow_bars.png
  - 分组柱状图（normal vs shuffled）

## 运行方式
示例（数据集中的单条样本）：

python -m probing.attention_flow \
  --model-path /data/zhk/models/qwen-3.5-9b \
  --dataset-path datasets/debug_reasoning.json \
  --sample-index 0 \
  --layer -1 \
  --top-k 8

如果不传 --dataset-path，将使用 probing/conflict_detect_example.py 中的内置示例。

## 备注
- layer 参数支持 1-based、0-based 与负数索引。
  例如：-1 为最后一层，1 为第一层。
- 柱状图只展示单个 head，避免 head 平均。
- 若事件跨度无法定位，该事件对的 Flow 视为 0.0。
