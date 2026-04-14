"""
检查模型生成的答案是否存在自然语言理解错误或推理错误，并给出相应的分析。
"""

import json
import os
import shutil
import re
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.chat import call_api
from utils.format import parse_json_block
from generate.generate_response import allen_helper


def _read_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _atomic_dump_json(path: str, data) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp_path, path)


def _event_name(events: List[str], index: int) -> str:
    if 0 <= index < len(events):
        return events[index]
    return f"event_{index}"


def _rel_stmt(l_idx: int, rel: str, r_idx: int, events: List[str]):
    left = _event_name(events, l_idx)
    right = _event_name(events, r_idx)
    return f"{left} {rel} {right}"


def build_bottom_up_path_summaries(
    paths: List[Dict[str, Any]], events: List[str]
) -> List[str]:
    """Build bottom-up path tree lines for LLM checking."""
    if not paths:
        return []

    def build_line(path: Dict[str, Any], left_rel: str, right_rel: str):
        base_l, base_r = path["base_event"]
        new_event = path["new_event"]
        target_stmt = _rel_stmt(base_l, path["target"], base_r, events)
        left_stmt = _rel_stmt(base_l, left_rel, new_event, events)
        right_stmt = _rel_stmt(new_event, right_rel, base_r, events)
        excluded = path.get("excluded", [])
        excluded_text = ",".join(excluded) if excluded else ""
        return f"{left_stmt} + {right_stmt} + not({excluded_text}) -> {target_stmt}"

    lines: List[str] = []
    visited = set()

    def dfs(idx: int) -> None:
        if idx in visited:
            return
        visited.add(idx)
        node = paths[idx]
        left_idx = node.get("left", -1)
        right_idx = node.get("right", -1)

        if left_idx != -1:
            dfs(left_idx)
        if right_idx != -1:
            dfs(right_idx)

        left_rel = node["path"][0] if left_idx == -1 else paths[left_idx]["target"]
        right_rel = node["path"][1] if right_idx == -1 else paths[right_idx]["target"]
        lines.append(build_line(node, left_rel, right_rel))

    roots = [i for i, p in enumerate(paths) if p.get("parent", -1) == -1]
    for root in roots:
        dfs(root)

    return lines


def build_top_down_path_summaries(paths: List[Dict[str, Any]], events) -> List[str]:
    """
    Build top-down path tree lines for LLM checking.
    Line Format: up_node -> left_node + right_node + exclude_relationship
    """
    if not paths:
        return []

    def build_line(path: Dict[str, Any], left_rel: str, right_rel: str) -> str:
        base_l, base_r = path["base_event"]
        new_event = path["new_event"]
        up_stmt = _rel_stmt(base_l, path["target"], base_r, events)
        left_stmt = _rel_stmt(base_l, left_rel, new_event, events)
        right_stmt = _rel_stmt(new_event, right_rel, base_r, events)
        excluded = path.get("excluded", [])
        excluded_text = f"not({','.join(excluded)})" if excluded else "not()"
        return f"{up_stmt} -> {left_stmt} + {right_stmt} + {excluded_text}"

    lines: List[str] = []
    visited = set()

    def dfs(idx: int) -> None:
        if idx in visited:
            return
        visited.add(idx)

        node = paths[idx]
        left_idx = node.get("left", -1)
        right_idx = node.get("right", -1)

        left_rel = node["path"][0] if left_idx == -1 else paths[left_idx]["target"]
        right_rel = node["path"][1] if right_idx == -1 else paths[right_idx]["target"]
        lines.append(build_line(node, left_rel, right_rel))

        if left_idx != -1:
            dfs(left_idx)
        if right_idx != -1:
            dfs(right_idx)

    roots = [i for i, p in enumerate(paths) if p.get("parent", -1) == -1]
    for root in roots:
        dfs(root)

    return lines


def _call_llm_json(
    messages: List[Dict[str, str]], model: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    raw = call_api(messages, model)
    parsed = parse_json_block(raw)
    return parsed, raw


def _separate_thinking(thinking: str) -> Tuple[str, str]:
    """
    Thinking format is '1. Hint Interpretation Phase: ... 2. Reasoning Phase: ...'. This function separates the two phases and returns them as a tuple (hint_interpretation, reasoning).
    """

    hint_pattern = re.compile(
        r"(?:^|\n)\s*1\s*[\).:-]?\s*hint\s*interpretation\s*phase\s*:?",
        flags=re.IGNORECASE,
    )
    reason_pattern = re.compile(
        r"(?:^|\n)\s*2\s*[\).:-]?\s*reasoning\s*phase\s*:?",
        flags=re.IGNORECASE,
    )

    hint_match = hint_pattern.search(thinking)
    reason_match = reason_pattern.search(thinking)

    # Preferred split: keep only phase content (without phase titles).
    if reason_match:
        hint_start = hint_match.end() if hint_match else 0
        hint_text = thinking[hint_start : reason_match.start()].strip()
        reasoning_text = thinking[reason_match.end() :].strip()
        return hint_text, reasoning_text
    # Fallback: no explicit reasoning phase marker.
    if hint_match:
        return thinking[hint_match.end() :].strip(), ""

    return thinking, thinking


def _build_tips(sample):
    thinking = sample.get("thinking", "") or ""
    hints = sample.get("hints", []) or []
    explanations = sample.get("explanation", []) or []
    if "blank_object" in sample["target"]:
        path_lines = build_top_down_path_summaries(sample["paths"], sample["events"])
    else:
        path_lines = build_bottom_up_path_summaries(sample["paths"], sample["events"])

    user = (
        "Return JSON only. Schema: "
        '{"ok": bool, "error_description": string}. '
        "'error_description' means the brief summary of error you found"
        "Note: model thinking may be truncated due to token limit. If you don't find any issues in the existing content, return ok=false and error_description: 'Thinking content is truncated. No error found in existing content'."
        "Hints and explanations:\n"
        + "\n".join(
            [
                f"- Hint {i+1}: {h} | Explanation: {e}"
                for i, (h, e) in enumerate(zip(hints, explanations))
            ]
        )
        + "\nModel thinking:\n"
        + thinking
    )
    if "blank_object" in sample["target"]:
        fill_tips = (
            """
            Check whether any Reasoning Errors in LLM's thinking.
            Definition of Reasoning Error:
            A Reasoning Error occurs means LLM makes an incorrect inference while combining information from interpreted hints.
            Important rules:
            1. Model's thinking format is '1. Hint Interpretation Phase: ... 2. Reasoning Phase: ...', you just need to check content in '2. Reasoning Phase'. 
            2. The path tree and the order of hints may not match. It is normal that the order of path tree traversal differs from the order of actual inference.
            3. There maybe some implicit hints that don't explicitly exist in path tree, but they provide important constraint information(It may refer to the relative duration between events, the relationship between start or end times.).
            Procedure:
            1. Retrieve along the top-down path tree and check where information is missing and what information needs to make the path valid(Refer to standard answer).
            2. Then compare the difference between model's thinking and the retrieval process just now, and analyze the problems in model's thinking.
            """
            + "The candidate standard answer for the blank object are:"
            + "\n".join([f"- {opt}" for opt in sample["target"]["blank_candidate"]])
            + "Please analyze the common characteristics of these candidate hints that make the path valid."
            + f"And then compare to your answer {sample["answer_single"][0]}"
        )
        fill_tree = """
            Path tree (top-down order, follow the path tree step by step to check):
            Each node consists of 2 events and their Allen relation(And some implicit hints), representing the order of 2 start and 2 end time points. Becauce the time order is equivalent to allen relation.
            Line format: up node -> bottom node + bottom node + exclude relation
        """ + "\n".join(
            path_lines
        )
        tips = fill_tips + user + fill_tree
    elif "conflict_no" in sample["target"]:
        conflict_tips = (
            """
            Check whether any Reasoning Errors in LLM's thinking.
            Definition of Reasoning Error:
            A Reasoning Error occurs means LLM makes an incorrect inference while combining information from interpreted hints.
            Important rules:
            1. Model's thinking format is '1. Hint Interpretation Phase: ... 2. Reasoning Phase: ...', you just need to check content in '2. Reasoning Phase'. 
            2. The path tree and the order of hints may not match. It is normal that the order of path tree traversal differs from the order of actual inference.
            3. There maybe some implicit hints that don't explicitly exist in path tree, but they provide important constraint information(It may refer to the relative duration between events, the relationship between start or end times.).
            Procedure:
            1. Based on the standard answer and path tree, analyze why there is a contradiction.
            2. Analyze the thinking process to determine why the contradiction was not found whether you were misled somewhere or failed to realize that this point would give rise to a contradiction.
            """
            f"Standard answer: The conflict hint is hint {sample["target"]["conflict_no"]}:"
            + f"{hints[sample['target']['conflict_no']-1]}"
        )
        conflict_tree = """
            In the original question, I've told you 'All hints directly describe the relation between 2 events is absolutely correct.'
            'Directly describe' means you can directly determine the allen relation(Or complete the sorting of four time points including the start and end times of two events) between 2 event based on this hint without any other hints.
            So you can check along the path tree and think about why the hint in the standard answer inevitably lead to conflicts.
            The path tree(with original no-conflict hints) is traversed in a bottom-up order, so the first line you see represent the more basic nodes in the tree 
            Each node consists of 2 events and their Allen relation(And some implicit hints), representing the order of 2 start and 2 end time points. Becauce the time order is equivalent to allen relation.
            Line format: bottom node + bottom node + exclude relation -> up node
            """ + "\n".join(
            path_lines
        )
        tips = conflict_tips + user + conflict_tree
    else:
        single_tips = """
            Check whether any Reasoning Errors in LLM's thinking.
            Definition of Reasoning Error:
            A Reasoning Error occurs means LLM makes an incorrect inference while combining information from interpreted hints.
            Important rules:
            1. Model's thinking format is '1. Hint Interpretation Phase: ... 2. Reasoning Phase: ...', you just need to check content in '2. Reasoning Phase'. 
            2. If a hint is correctly interpreted but not used in the reasoning process when it should be used, this should be classified as a Reasoning Error.
            3. The path tree and the order of hints may not match. It is normal that the order of path tree traversal differs from the order of actual inference.
            4. There maybe some implicit hints that don't explicitly exist in path tree, but they provide important constraint information(It may refer to the relative duration between events, the relationship between start or end times.).
            Procedure:
            1. Examine the reasoning steps in the thinking process following the path tree.
            2. Identify the step where the reasoning becomes invalid.
            If any incorrect inference step or missing reasoning step is detected, classify the case as a Reasoning Error.
            Examples of Reasoning Errors include:
            - Deriving a relation that contradicts the inference path.
            - Improper use of hints during reasoning.   
            - Hallucinations occurring during reasoning lead to alterations in certain information.
            - Failing to derive a necessary intermediate relation or timeline. 
        """
        single_tree = """
            Path tree (bottom-up order, follow the path tree step by step to check):
            Note(How to use path tree):
            The path tree is traversed in a bottom-up order, so the first line you see represent the more basic nodes in the tree 
            Each node consists of 2 events and their Allen relation(And some implicit hints), representing the order of 2 start and 2 end time points. Becauce the time order is equivalent to allen relation.
            For each line (bottom node + bottom node + exclude relation -> up node), the following items need to be checked:
            1. Do you already have information about the two lower-level nodes?
            2. Do you already have the information needed to exclude relationships?
            3. Whether to infer the relationship between upper-level nodes based on the information from points 1 and 2.
            If 1 is detected, if the underlying node can be further subdivided, it will backtrack.
            If 2 is detected, confirm whether the corresponding exclusion relationship hint is understood.
            If 3 is detected, determine whether an error occurred during the inference process.
            """ + "\n".join(
            path_lines
        )
        tips = single_tips + user + single_tree
    return tips


def _build_judge_nlu_msg(sample):
    hints = sample.get("hints", []) or []
    explanations = sample.get("explanation", []) or []
    thinking = sample.get("thinking", "") or ""
    thinking_nlu = _separate_thinking(thinking)[0]

    system = allen_helper
    user = (
        """
        Your task is to check whether the model has made any Natural Language Understanding Errors (NLU Errors).
        Definition of Natural Language Understanding Error:
        A Natural Language Understanding Error occurs when the model incorrectly interprets the meaning of an individual hint.
        Specifically, an NLU Error occurs if the temporal relation or temporal order extracted from a single hint does not match the gold explanation provided for that hint.
        Important rules:
        1. NLU errors are evaluated at the level of a single hint. Each hint should be checked independently.
        2. Model's thinking format is '1. Hint Interpretation Phase: ... 2. Reasoning Phase: ...', you just need to check content in '1. Hint Interpretation Phase' for each hint.
        3. If a hint is correctly interpreted but later not used or incorrectly used during reasoning, this is NOT an NLU error.
        4. Failing to directly exclude any relationship is not an nlu error. The model is not explicitly required to directly exclude certain relationships; it is only required to interpret the basic meaning. 
        5. Missing information alone is not sufficient to conclude an NLU error. 
        Procedure:
        For each hint:
        1. Compare the model's interpretation in the thinking process with the provided gold explanation.
        2. Determine whether the extracted temporal relation or temporal information matches the explanation.
        If any mismatch is found, classify the case as an NLU Error and stop the analysis.
        Otherwise, conclude that no NLU Error is present. 
        Examples of NLU Errors include:
        - Misinterpreting the allen relation described in the hint.
        - Incorrect ordering start or end times for two events
        - Actively and incorrectly excluding a relation that should be retained. 
        - Actively and incorrectly retaining a relation that should be excluded.
        """
        + "Return JSON only. Schema: "
        '{"ok": bool, "error_description": string}. '
        "error_description include brief summary of every error you found."
        "If no issues, just return ok=true. "
        "Hints and explanations:\n"
        + "\n".join(
            [
                f"- Hint {i+1}: {h} | Explanation: {e}"
                for i, (h, e) in enumerate(zip(hints, explanations))
            ]
        )
        + "\nModel thinking:\n"
        + thinking_nlu
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return messages


def judge_nlu(sample, model):
    print(f"[debug] Judging NLU for sample {sample.get('id')} with model {model}")
    messages = _build_judge_nlu_msg(sample)
    parsed, raw = _call_llm_json(messages, model)
    if parsed is None:
        print(f"[debug] NLU judge parse failed for sample {sample.get('id')}")
        return {
            "ok": None,
            "raw": raw,
        }
    return parsed


def _build_judge_thinking_msg(sample):
    system = allen_helper
    tips = _build_tips(sample)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": tips},
    ]
    return messages


def judge_thinking(sample: Dict[str, Any], model: str) -> Dict[str, Any]:
    messages = _build_judge_thinking_msg(sample)
    path_lines = build_top_down_path_summaries(sample["paths"], sample["events"])
    parsed, raw = _call_llm_json(messages, model)
    if parsed is None:
        print(f"[debug] Thinking judge parse failed for sample {sample.get('id')}")
        parsed = {
            "ok": None,
            "raw": raw,
            "path_tree": path_lines,
        }
    parsed["path_tree"] = path_lines
    return parsed


def verify_sample(sample, model: str) -> Dict[str, Any]:
    print(f"[debug] Verifying sample {sample.get('id')} with model {model}")
    sample["error_type"] = 0
    nlu = judge_nlu(sample, model)
    if nlu.get("ok") is None:
        sample["nlu_raw"] = nlu.get("raw", "")
    elif nlu.get("ok") is False:
        print(f"[debug] NLU error detected for sample {sample.get('id')}")
        sample["error_type"] += 1
        sample["nlu_error_description"] = nlu.get("error_description", "")
        # return sample

    reason = judge_thinking(sample, model)
    if reason.get("ok") is not None and reason.get("ok") is False:
        print(f"[debug] Reasoning error detected for sample {sample.get('id')}")
        sample["error_type"] += 2
        sample["reasoning_error_description"] = reason.get("error_description", "")
    else:
        print(
            f"[debug] Reasoning uncertain for sample {sample.get('id')}, ok={reason.get('ok')}"
        )
        sample["reasoning_raw"] = reason.get("raw", "")
    sample["path_tree"] = reason.get("path_tree", [])

    return sample


def _split_indices_contiguous(total: int, workers: int):
    """Split [0, total) into contiguous blocks, same strategy as generate_response."""
    if total <= 0:
        return []
    workers = max(1, workers)
    n = total // workers
    slices = []
    for worker_id in range(workers):
        start = worker_id * n
        end = (worker_id + 1) * n if worker_id < workers - 1 else total
        if start >= total:
            break
        if end < start:
            end = start
        slices.append((worker_id, start, end))
    return slices


def main(path, workers=1, model="qwen3.5-plus"):
    if not path:
        raise ValueError("path is required")
    input_path = f"datasets/answers/{path}_with_answers.json"
    meta = {
        "inputs": input_path,
        "model": model,
        "total": 0,
        "nlu_errors": 0,
        "reasoning_errors": 0,
        "ok": 0,
    }
    report_samples = []

    temp_dir = f"datasets/temp/{path}_explain"
    _ensure_dir(temp_dir)

    data = _read_json(input_path)
    print(f"[debug] Loaded {len(data)} samples from {input_path}")

    total = len(data)
    worker_count = max(1, workers)
    slices = _split_indices_contiguous(total, worker_count)
    if not slices:
        print("[debug] 输入数据为空")
    else:
        print(
            f"[debug] Parallel verification with workers={worker_count}, slices={slices}"
        )

    def worker_task(worker_id: int, start: int, end: int):
        print(f"[debug] Worker {worker_id + 1} handling range [{start}, {end})")
        worker_out_path = f"{temp_dir}/{path}_{worker_id + 1}.json"
        local_results = []
        local_total = 0
        local_ok = 0
        local_nlu = 0
        local_reason = 0

        for index in range(start, end):
            sample = data[index]
            local_total += 1
            if "right" not in sample:
                # print(
                #     f"[debug] Worker {worker_id + 1} sample {sample.get('id')} missing 'right' field, skipping"
                # )
                continue
            if sample.get("right") is True:
                local_ok += 1
                # print(
                #     f"[debug] Worker {worker_id + 1} sample {sample.get('id')} correct, skipping"
                # )
                local_results.append(
                    {
                        "index": index,
                        "status": "ok",
                        "sample_id": sample.get("id"),
                    }
                )
                _atomic_dump_json(worker_out_path, local_results)
                continue

            result = verify_sample(sample, model)
            local_results.append(
                {
                    "index": index,
                    "status": "verified",
                    "sample_id": sample.get("id"),
                    "result": result,
                }
            )
            _atomic_dump_json(worker_out_path, local_results)
            if result["error_type"] & 1:
                local_nlu += 1
            elif result["error_type"] & 2:
                local_reason += 1

        final_results = []
        for item in local_results:
            if isinstance(item, dict) and item.get("status") == "verified":
                final_results.append((item.get("index", -1), item.get("result")))

        return {
            "results": final_results,
            "total": local_total,
            "ok": local_ok,
            "nlu_errors": local_nlu,
            "reasoning_errors": local_reason,
        }

    merged_results = []
    if slices:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(worker_task, worker_id, start, end)
                for worker_id, start, end in slices
                if end > start
            ]
            for future in as_completed(futures):
                chunk = future.result()
                meta["total"] += chunk["total"]
                meta["ok"] += chunk["ok"]
                meta["nlu_errors"] += chunk["nlu_errors"]
                meta["reasoning_errors"] += chunk["reasoning_errors"]
                merged_results.extend(chunk["results"])

    merged_results.sort(key=lambda item: item[0])
    report_samples = [item[1] for item in merged_results]
    write_samples = [item for item in report_samples if "error_type" in item]

    with open(
        f"datasets/explain/{path}_with_explanation.json", "w", encoding="utf-8"
    ) as f:
        json.dump(write_samples, f, ensure_ascii=False, indent=4)

    # 删除临时文件夹
    shutil.rmtree(temp_dir)

    print(
        "total={total}, ok={ok}, nlu_errors={nlu_errors}, reasoning_errors={reasoning_errors}".format(
            **meta
        )
    )


if __name__ == "__main__":
    main(path="sample", workers=1, model="qwen3.5-plus")
