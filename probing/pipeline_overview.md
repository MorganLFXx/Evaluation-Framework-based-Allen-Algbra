# 冲突检测线性探针两阶段总览

## 1. 总体流程

目标是对同一批样本做 control/treatment 对照，并在隐藏层上分两阶段检查模型：

1. Stage1：是否识别出与冲突直接相关的两条基本关系
2. Stage3：在 Stage1 检测层之后，模型恢复了多少全局关系

端到端步骤：

1. 输入一批样本（结构与 [probing/conflict_detect_example.py](probing/conflict_detect_example.py) 中 example 相同）。
2. 使用 build_question 构造问题：
- control: shuffle=False
- treatment: shuffle=True
3. 对两组问题分别做本地模型前向，提取逐层隐藏状态。
4. 使用 locate_conflict 获取冲突关系组（冲突关系 + 引发冲突的两条基本关系）。
5. 使用 get_whole_rels 获取全局关系集合（去除冲突关系组后）。
6. Stage1（二分类，逐层）：检查“那两条会与冲突句引发冲突的基本关系”是否在该层可被探针判别。
7. Stage3（逐层恢复率）：若 Stage1 在某层检测到冲突关系组，则从该层往后统计 get_whole_rels 的关系恢复比例。
8. 输出按层报告（control/treatment 指标、A/B 差值、Stage3 恢复轨迹）。

核心编排入口在 [probing/pipeline.py](probing/pipeline.py)。

## 2. 阶段定义

### Stage1
检查那两个会和冲突句引发冲突的基本关系是否判断出来。

实现口径：
- 样本内正类：locate_conflict 返回的两条 cause 关系。
- 样本内负类：同样本其他非冲突关系（来自 get_whole_rels 与关系集合补充）。
- 每层训练/评估二分类线性探针。

### Stage3
尽可能多地检查模型还原了全局多少关系。

实现口径：
- 先找 Stage1 首个“冲突关系组已检测到”的层（per sample, per group）。
- 从该层及之后，统计 get_whole_rels 中关系被探针正确恢复的比例。
- 输出每样本恢复轨迹与总体分布。

## 3. 目录内每个文件职责

### [probing/conflict_detect_example.py](probing/conflict_detect_example.py)
职责：提供样本结构与关系抽取辅助逻辑。

关键函数：
- build_question: 构造 control/treatment 问题（shuffle 控制组别差异）。
- locate_conflict: 抽取冲突关系组（conflict + cause relations）。
- get_whole_rels: 从 paths 树还原全局关系集合。

### [probing/pipeline.py](probing/pipeline.py)
职责：两阶段统一编排（数据读取、隐藏层特征、Stage1/Stage3 训练与统计、报告输出）。

关键流程：
1. 读取样本并构造 control/treatment 问题。
2. 提取逐层隐藏状态。
3. 组装关系级样本记录（冲突组 + 全局关系）。
4. 逐层执行 Stage1 二分类。
5. 逐层执行 Stage3 全局关系分类与恢复分析。
6. 汇总并输出报告。

### [probing/model_inference.py](probing/model_inference.py)
职责：本地模型推理与隐藏层提取。

### [probing/anchors.py](probing/anchors.py)
职责：字符区间到 token 区间映射、span pooling。

### [probing/train_probe.py](probing/train_probe.py)
职责：线性探针训练、预测与评估。

### [probing/eval_ab.py](probing/eval_ab.py)
职责：control/treatment 的配对 bootstrap 差值统计。

### [probing/hidding_state_analyze.py](probing/hidding_state_analyze.py)
职责：CLI 入口，组织参数并调用 pipeline。

### [probing/__init__.py](probing/__init__.py)
职责：导出统一调用接口。

## 4. 输出产物

默认输出目录：outputs/stage1_probe

主要产物：
- stage1_features.pt（可选特征缓存）
- stage1_report.json（包含 Stage1/Stage3 分层结果）

报告重点字段：
- 每层 Stage1 二分类指标与 A/B 差值
- 每层 Stage3 关系恢复指标
- Stage3 检测层后的全局关系恢复比例（按样本与汇总）

## 5. 四个核心文件内部详细流程

### 5.1 [probing/model_inference.py](probing/model_inference.py)

定位：负责把“问题文本”变成“逐层隐藏状态”。

内部流程：
1. 用 HiddenStateExtractorConfig 接收模型路径、设备、精度、最大长度。
2. HiddenStateExtractor.__init__ 完成初始化：
- _resolve_device: `auto` 时自动选 `cuda` 或 `cpu`。
- _resolve_dtype: 把字符串精度映射为 torch dtype。
- 加载 tokenizer 与 causal LM，并开启 `output_hidden_states=True`。
3. render_messages:
- 若 tokenizer 支持 `apply_chat_template`，走官方 chat template。
- 否则回退到简单 role 拼接格式。
4. extract_from_text:
- tokenizer 编码并返回 offset mapping。
- 前向推理拿到 hidden_states。
- 解析 layer_indices（支持负索引，如 `-1`）。
- 输出 token_ids / attention_mask / offset_mapping / layer_hidden / num_layers。

关键函数：
- HiddenStateExtractor._resolve_device
- HiddenStateExtractor._resolve_dtype
- HiddenStateExtractor.render_messages
- HiddenStateExtractor.extract_from_text

### 5.2 [probing/anchors.py](probing/anchors.py)

定位：负责“文本位置 -> token 位置 -> 向量池化”。

内部流程：
1. find_hint_char_spans: 按 hints 在 prompt 里顺序定位字符区间。
2. find_reasoning_phase_span: 查找 Reasoning Phase 标记并截取一个窗口。
3. char_span_to_token_span: 用 offset mapping 将字符区间映射为 token 区间。
4. mean_pool_span: 对 token 区间做平均池化，得到固定维度特征。
5. build_stage1_anchor_spans: 汇总 hint spans 与 reasoning span。

关键函数：
- find_hint_char_spans
- find_reasoning_phase_span
- char_span_to_token_span
- mean_pool_span
- build_stage1_anchor_spans

### 5.3 [probing/train_probe.py](probing/train_probe.py)

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

### 5.4 [probing/labels.py](probing/labels.py)

定位：负责 Stage1 的标签规则定义。

内部流程：
1. build_stage1_label_info:
- 从 `target.conflict_no` 得到核心 hint（core）。
- 根据 neighbor_window 扩展 near-core 区域。
2. stage1_binary_label:
- core/near-core 标为 1，其他标 0。
3. stage1_three_way_label:
- core=2, near=1, other=0（可用于更细粒度实验）。

关键函数：
- build_stage1_label_info
- stage1_binary_label
- stage1_three_way_label
