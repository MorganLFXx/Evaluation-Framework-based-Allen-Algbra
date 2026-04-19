# 线性探针总览

## 1. 总体流程

目标是对同一批样本做 control/treatment 对照，并在隐藏层上检查模型：
二分类判断关键节点关系是否可被线性探针区分。

关键节点定义：左子树或右子树至少有一个不是叶子节点的节点。

端到端步骤：

1. 输入一批样本（结构与 [probing/construct_rels.py](probing/construct_rels.py) 中 example 相同）。
2. 使用 build_question 构造两组问题：
- control: shuffle=False
- treatment: shuffle=True
3. 对两组问题分别做本地模型前向，提取逐层隐藏状态。
4. 使用 get_key_rels 获取关键节点关系集合（正例）。
5. 使用 get_whole_rels 获取所有关系集合。
6. 以 key_rels 为正例、whole_rels\key_rels 为负例，在所有指定层训练并评估二分类探针。
7. 输出按层报告（control/treatment 指标、A/B 差值和置信区间）。

核心编排入口在 [probing/pipeline.py](probing/pipeline.py)。

## 2. 目录内每个文件职责

### [probing/construct_rels.py](probing/construct_rels.py)
职责：提供样本结构与关系抽取辅助逻辑。

关键函数：
- build_question: 构造 control/treatment 问题（shuffle 控制组别差异）。
- get_whole_rels: 从 paths 树还原全局关系集合。
- get_key_rels: 抽取关键节点关系集合。

### [probing/pipeline.py](probing/pipeline.py)
职责：统一编排（数据读取、隐藏层特征提取、按层二分类训练与统计、报告输出）。

关键流程：
1. 读取样本并构造 control/treatment 问题。
2. 提取逐层隐藏状态。
3. 组装关系级样本记录（含标签、group、layer、instance_key）。
4. 在所有指定层分别执行 control/treatment 二分类。
5. 对 control/treatment 的配对实例做 bootstrap A/B 差值统计。
6. 汇总并输出报告。

### [probing/model_inference.py](probing/model_inference.py)
职责：本地模型推理与隐藏层提取。

### [probing/anchors.py](probing/anchors.py)
职责：字符区间到 token 区间映射、span pooling。

### [probing/train_probe.py](probing/train_probe.py)
职责：线性探针训练、预测与评估。

### [probing/eval_ab.py](probing/eval_ab.py)
职责：control/treatment 的配对 bootstrap 差值统计。

### [probing/labels.py](probing/labels.py)
职责：根据 whole_rels 与 key_rels 构造二分类标签。

### [probing/hidding_state_analyze.py](probing/hidding_state_analyze.py)
职责：CLI 入口，组织参数并调用 pipeline。

### [probing/__init__.py](probing/__init__.py)
职责：导出统一调用接口。

## 3. 输出产物

默认输出目录：outputs/probe

主要产物：
- features.pt（可选特征缓存）
- report.json

报告重点字段：
- 每层 control/treatment 二分类指标（accuracy/precision/recall/f1/auroc）
- 每层 A/B 差值统计（control、treatment、diff、ci_low、ci_high）
- 按 sample_id 的训练/测试切分信息

## 4. 五个核心文件内部详细流程

### 4.1 [probing/model_inference.py](probing/model_inference.py)

定位：负责把问题文本转换为逐层隐藏状态。

内部流程：
1. 用 HiddenStateExtractorConfig 接收模型路径、设备、精度、最大长度。
2. HiddenStateExtractor.__init__ 完成初始化：
- _resolve_device: auto 时自动选 cuda 或 cpu。
- _resolve_dtype: 把字符串精度映射为 torch dtype。
- 加载 tokenizer 与 causal LM，并开启 output_hidden_states=True。
3. render_messages:
- 若 tokenizer 支持 apply_chat_template，走官方 chat template。
- 否则回退到简单 role 拼接格式。
4. extract_from_text:
- tokenizer 编码并返回 offset mapping。
- 前向推理拿到 hidden_states。
- 解析 layer_indices（支持负索引，如 -1）。
- 输出 token_ids / attention_mask / offset_mapping / layer_hidden / num_layers。

关键函数：
- HiddenStateExtractor._resolve_device
- HiddenStateExtractor._resolve_dtype
- HiddenStateExtractor.render_messages
- HiddenStateExtractor.extract_from_text

### 4.2 [probing/anchors.py](probing/anchors.py)

定位：负责文本锚点定位与 span pooling。

内部流程：
1. find_relation_char_span: 依据关系事件对在 prompt 中定位字符区间。
2. char_span_to_token_span: 用 offset mapping 将字符区间映射为 token 区间。
3. mean_pool_span: 对 token 区间做平均池化，得到固定维度特征。
4. 其余函数（hint/reasoning span）保留为可选调试能力。

关键函数：
- find_relation_char_span
- char_span_to_token_span
- mean_pool_span

### 4.3 [probing/train_probe.py](probing/train_probe.py)

定位：负责线性探针的训练、评估与预测。

内部流程：
1. _standardize_fit / _standardize_apply:
- 训练集拟合均值方差并标准化。
- 测试集/推理阶段复用同一均值方差。
2. train_linear_probe:
- 构建 LinearProbe（单层线性层）。
- CrossEntropyLoss + Adam 训练固定 epoch。
- 返回 TrainedProbe（含模型和标准化参数）。
3. evaluate_linear_probe:
- 输出分类指标（accuracy，二分类时含 precision/recall/f1/auroc）。
4. predict_linear_probe:
- 给任意特征批量输出预测类别和置信分数。

关键函数：
- train_linear_probe
- evaluate_linear_probe
- predict_linear_probe

### 4.4 [probing/labels.py](probing/labels.py)

定位：负责标签规则定义。

内部流程：
1. normalize_triples：关系三元组去重并保持顺序。
2. build_key_relation_labels：
- 输入 whole_rels 与 key_rels。
- 将 key_rels 映射为正例(1)。
- 将 whole_rels\key_rels 映射为负例(0)。
- 输出 positives / negatives / candidates / label_map。
3. label_for_triple：查询单条关系三元组标签，默认返回 0。

关键函数：
- normalize_triples
- build_key_relation_labels
- label_for_triple

### 4.5 [probing/pipeline.py](probing/pipeline.py)

定位：端到端主编排入口（run_pipeline）。

内部流程：
1. 读取数据并按 max_samples 裁剪。
2. 初始化 HiddenStateExtractor，解析层选择 layer_spec。
3. 对每个 sample 生成 control/treatment prompt 并提取层表示。
4. 调用 labels 逻辑构造关系级二分类样本。
5. 对每层分别训练 control/treatment 线性探针并评估。
6. 对测试集预测做配对对齐，调用 compare_ab_with_bootstrap 计算 A/B 差值与 CI。
7. 输出 features.pt（可选）与 report.json。

关键实现点：
- 训练/测试按照 sample_id 切分，避免同一样本泄漏。
- control 与 treatment 通过 instance_key 对齐后再做 A/B 统计。
- 当某层某组训练集类别不足时，该组标记 skipped 并在报告记录 reason。

## 5. 约束与约定

- 输入样本应包含 events / hints / paths / target 字段。
- layer_spec 支持 all 与负索引（例如 -1,-2,-3）。
- 文本锚点找不到时使用零向量回退，不中断流水线。
- 探针训练使用全量 batch（线性层 + CrossEntropy + Adam）。
