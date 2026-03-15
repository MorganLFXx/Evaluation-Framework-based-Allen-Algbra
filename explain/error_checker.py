"""
检查模型生成的答案是否存在自然语言理解错误或推理错误，并给出相应的分析。
"""

import json
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.chat import call_api
from utils.format import parse_json_block
from explain.qa_checker import sample_check
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


def build_path_summaries(paths: List[Dict[str, Any]], events: List[str]) -> List[str]:
    """Build bottom-up path tree lines for LLM checking."""
    if not paths:
        return []

    def _event_name(events: List[str], index: int) -> str:
        if 0 <= index < len(events):
            return events[index]
        return f"event_{index}"

    def _rel_stmt(l_idx: int, rel: str, r_idx: int) -> str:
        left = _event_name(events, l_idx)
        right = _event_name(events, r_idx)
        return f"{left} {rel} {right}"

    def build_line(path: Dict[str, Any], left_rel: str, right_rel: str) -> str:
        base_l, base_r = path["base_event"]
        new_event = path["new_event"]
        target_stmt = _rel_stmt(base_l, path["target"], base_r)
        left_stmt = _rel_stmt(base_l, left_rel, new_event)
        right_stmt = _rel_stmt(new_event, right_rel, base_r)
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


def _call_llm_json(
    messages: List[Dict[str, str]], model: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    raw = call_api(messages, model)
    parsed = parse_json_block(raw)
    return parsed, raw


def judge_nlu(sample: Dict[str, Any], model: str) -> Dict[str, Any]:
    print(f"[debug] Judging NLU for sample {sample.get('id')} with model {model}")
    hints = sample.get("hints", []) or []
    explanations = sample.get("explanation", []) or []
    thinking = sample.get("thinking", "") or ""

    system = allen_helper
    user = (
        """
        Your task is to check whether the model has made any Natural Language Understanding Errors (NLU Errors).
        Definition of Natural Language Understanding Error:
        A Natural Language Understanding Error occurs when the model incorrectly interprets the meaning of an individual hint.
        Specifically, an NLU Error occurs if the temporal relation or temporal order extracted from a single hint does not match the gold explanation provided for that hint.
        Examples of NLU Errors include:
        - Misinterpreting the temporal relation described in the hint.
        - Incorrect ordering start or end times for two events
        - Incorrectly excluding a relation that should be retained.
        - Incorrectly retaining a relation that should be excluded.
        Important rules:
        1. NLU errors are evaluated at the level of a single hint. Each hint should be checked independently.
        2. Do NOT evaluate reasoning or multi-hint inference at this stage.
        3. If a hint is correctly interpreted but later not used during reasoning, this is NOT an NLU error.
        4. Missing information alone is not sufficient to conclude an NLU error unless the interpretation directly contradicts the gold explanation.
        Procedure:
        For each hint:
        1. Compare the model's interpretation in the thinking process with the provided gold explanation.
        2. Determine whether the extracted temporal relation or temporal information matches the explanation.
        If any mismatch is found, classify the case as an NLU Error and stop the analysis.
        Otherwise, conclude that no NLU Error is present. \n
        """
        + "Return JSON only. Schema: "
        '{"ok": bool, "error_type": string, "issues": [{"hint_index": int, "reason": string}], "confidence": number}. '
        "issues must include every hint whose interpretation conflicts with the explanation. "
        "If no issues, return an empty list and ok=true. "
        "error_type must be one of: nlu_error, none.\n"
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
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    parsed, raw = _call_llm_json(messages, model)
    if parsed is None:
        return {
            "ok": None,
            "error_type": "none",
            "issues": [],
            "reason": "parse_failed",
            "confidence": 0.0,
            "raw": raw,
        }
    print(
        f"[debug] NLU judge completed for sample {sample.get('id')}, ok={parsed.get('ok')}"
    )
    return parsed


def judge_thinking(
    sample: Dict[str, Any], path_summaries: List[str], model: str
) -> Dict[str, Any]:
    # 1) Use thinking + bottom-up tree to validate reasoning.
    # 2) If uncertain, include reasoning_content and re-judge.
    thinking = sample.get("thinking", "") or ""
    # reasoning_content = sample.get("reasoning_content", "") or ""
    hints = sample.get("hints", []) or []
    explanations = sample.get("explanation", []) or []
    path_lines = path_summaries if len(path_summaries) > 0 else []

    system = allen_helper
    user = (
        """
        Check whether the model has made any Reasoning Errors.
        Assumption:
        The interpretations of individual hints have already been checked and can be assumed to be correct unless clear evidence of misunderstanding appears.
        Definition of Reasoning Error:
        A Reasoning Error occurs when the model makes an incorrect inference while combining information from multiple hints to derive a conclusion.
        Examples of Reasoning Errors include:
        - Incorrectly combining temporal relations.
        - Deriving a relation that contradicts the inference path.
        - Improper use of hints during reasoning.   
        - Hallucinations occurring during reasoning lead to alterations in certain information.
        - Failing to derive a necessary intermediate relation or timeline.
        Important rules:
        1. Reasoning errors occur only at the multi-hint reasoning level.
        2. If a hint is correctly interpreted but not used in the reasoning process when it should be used, this should be classified as a Reasoning Error.
        3. If you find that a reasoning error actually originates from a misunderstanding of a single hint, then the error should be classified as an NLU Error.
        4. The path tree and the order of hints may not match. You should determine the line being checked and the corresponding hints. 
        Procedure:
        1. Examine the reasoning steps in the thinking process following the path tree.
        2. Identify the step where the reasoning becomes invalid.
        If any incorrect inference step or missing reasoning step is detected, classify the case as a Reasoning Error.\n
        """
        "Return JSON only. Schema: "
        '{"ok": bool, "error_type": string, "issues": ['
        '{"location": string, "reason": string}], "uncertain": bool, "confidence": number}. '
        "'location' means the specific part of path tree or hints, for example, 'line 2 of path tree' or 'hint 1&2'. "
        "error_type must be one of: reasoning_error, nlu_error(If you found NLU errors still exist), none.\n"
        "Hints and explanations:\n"
        + "\n".join(
            [
                f"- Hint {i+1}: {h} | Explanation: {e}"
                for i, (h, e) in enumerate(zip(hints, explanations))
            ]
        )
        + "\nPath tree (bottom-up order, follow the path tree step by step to check):\n"
        + "Note(How to use path tree):"
        + """
        The path tree is traversed in a bottom-up order, so the first line you see represent the more basic nodes in the tree 
        Each node consists of two events and their Allen relation, representing the sequence of two start and two end time points.Therefore, the time sequence of detecting equivalence to relational structures is also correct.
        For each line (i.e., bottom node + bottom node + exclude relationship-> up node), the following items need to be checked:
        1. Do you already have information about the two lower-level nodes?
        2. Do you already have the information needed to exclude relationships?
        3. Whether to infer the relationship between upper-level nodes based on the information from points 1 and 2
        If 1 is detected, if the underlying node can be further subdivided, it will backtrack; otherwise, it will check whether the corresponding hint is correctly understood.
        If 2 is detected, confirm whether the corresponding exclusion relationship hint is understood
        If 3 is detected, determine whether an error occurred during the inference process
        """
        + "\n".join(path_lines)
        + "\nModel thinking:\n"
        + thinking
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    parsed, raw = _call_llm_json(messages, model)
    if parsed is None:
        print(
            f"[debug] Thinking judge parse failed (primary) for sample {sample.get('id')}"
        )
        parsed = {
            "ok": None,
            "error_type": "none",
            "issues": [],
            "uncertain": True,
            "confidence": 0.0,
            "raw": raw,
        }

    if parsed.get("uncertain") is True:
        parsed["reason"] = "uncertain"
        print(f"[debug] Thinking judge uncertain for sample {sample.get('id')}")

    # TODO: token消耗过大，暂不启用
    # if parsed.get("uncertain") is True and reasoning_content:
    #     follow_user = (
    #         "Re-evaluate using the raw reasoning content below. "
    #         "Return JSON with the same schema.\n"
    #         + "Raw reasoning content:\n"
    #         + reasoning_content
    #     )
    #     follow_messages = [
    #         {"role": "system", "content": system},
    #         {"role": "user", "content": user},
    #         {"role": "assistant", "content": raw},
    #         {"role": "user", "content": follow_user},
    #     ]
    #     follow_parsed, follow_raw = _call_llm_json(follow_messages, model)
    #     if follow_parsed is None:
    #         return {
    #             "ok": None,
    #             "error_type": "none",
    #             "issues": [],
    #             "uncertain": True,
    #             "confidence": 0.0,
    #             "raw": follow_raw,
    #         }
    #     follow_parsed["raw"] = follow_raw
    #     return follow_parsed

    return parsed


def verify_sample(sample: Dict[str, Any], model: str) -> Dict[str, Any]:
    print(f"[debug] Verifying sample {sample.get('id')} with model {model}")
    paths = sample.get("paths", []) or []
    events = sample.get("events", []) or []

    result: Dict[str, Any] = {
        "id": sample.get("id"),
        "target": sample.get("target"),
        "answer_single": sample.get("answer_single"),
        "error_type": "none",
        "nlu_checks": [],
        "reasoning_check": None,
    }

    nlu = judge_nlu(sample, model)
    result["nlu_checks"].append(nlu)
    if nlu.get("ok") is False:
        print(f"[debug] NLU error detected for sample {sample.get('id')}")
        result["error_type"] = "nlu_error"
        result["reasoning_check"] = None
        return result

    path_summaries = build_path_summaries(paths, events)
    result["path_summaries"] = path_summaries
    # print(
    #     f"[debug] Path summaries ready for sample {sample.get('id')}, count={len(path_summaries)}, lines={path_summaries}"
    # )

    reason = judge_thinking(sample, path_summaries, model)
    result["reasoning_check"] = reason
    if reason.get("ok") is False:
        print(f"[debug] Reasoning error detected for sample {sample.get('id')}")
        result["error_type"] = "reasoning_error"
    else:
        print(
            f"[debug] Reasoning uncertain for sample {sample.get('id')}, ok={reason.get('ok')}"
        )
        result["error_type"] = "unknown"

    return result


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
    report: Dict[str, Any] = {
        "meta": {
            "inputs": input_path,
            "model": model,
            "total": 0,
            "nlu_errors": 0,
            "reasoning_errors": 0,
            "ok": 0,
        },
        "samples": [],
    }

    temp_dir = f"datasets/temp/{path}_explain"
    _ensure_dir(temp_dir)
    # print(f"[debug] Temp checkpoint dir: {temp_dir}")

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
        worker_out_path = os.path.join(temp_dir, f"{path}_{worker_id + 1}.json")
        local_results = []
        local_total = 0
        local_ok = 0
        local_nlu = 0
        local_reason = 0

        # resume existing worker checkpoint if present
        if os.path.exists(worker_out_path):
            try:
                with open(worker_out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    local_results = existing
            except Exception:
                local_results = []

        for index in range(start, end):
            sample = data[index]
            local_total += 1
            if sample_check(sample) is True:
                local_ok += 1
                print(
                    f"[debug] Worker {worker_id + 1} sample {sample.get('id')} correct, skipping"
                )
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
            if result["error_type"] == "nlu_error":
                local_nlu += 1
            elif result["error_type"] == "reasoning_error":
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
                report["meta"]["total"] += chunk["total"]
                report["meta"]["ok"] += chunk["ok"]
                report["meta"]["nlu_errors"] += chunk["nlu_errors"]
                report["meta"]["reasoning_errors"] += chunk["reasoning_errors"]
                merged_results.extend(chunk["results"])

    merged_results.sort(key=lambda item: item[0])
    report["samples"] = [item[1] for item in merged_results]

    with open(
        f"datasets/explain/{path}_with_explanation.json", "w", encoding="utf-8"
    ) as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

    # 删除临时文件夹
    shutil.rmtree(temp_dir)

    print(
        "Done. total={total}, ok={ok}, nlu_errors={nlu_errors}, reasoning_errors={reasoning_errors}".format(
            **report["meta"]
        )
    )


if __name__ == "__main__":
    main(path="sample", workers=1, model="qwen3.5-plus")
