import argparse
import json
import os
import glob
from utils.chat import call_api
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

allen_helper = """You are an expert in time relation judgment, well-versed in Allen's interval algebra.
This mathematical framework defines 13 fundamental types of temporal relationships：
precedes(p), preceded_by(P), meets(m), met_by(M), overlaps(o), overlapped_by(O), finished_by(F), finishes(f), contains(D), during(d), starts(s), started_by(S), equals(e).
Here are some things to note: 
1. 'A overlaps B' means that there is overlap between A and B but A starts before B. 'A overlapped_by B' means A and B still overlap, but B starts before A. 
2. 'A starts B' means A and B start at the same time but A ends before B. 'A started_by B' means A and B start at the same time but B ends before A.
3. 'A finishes B' means A and B end at the same time but A starts after B. 'A finished_by B' means A and B end at the same time but B starts after A.
The correspondence between uppercase and lowercase letters of the same letter is inverse. For example, A p B is equivalent to B P A.
"""
# TIME_GRANULARITY = "The basic time granularity is day. For example, A(2020.2.1-2022.2.3) and B(2022.2.3-2024.4.5) have the relation 'meets' because A ends when B starts."

few_shot_examples = """Here are an example:
Target: 0 precedes 1
Hints: 
1.‘0’ and ‘2’ overlap in time. But ‘0’ starts first.
2.‘2’ finishes at the same time as ‘1’ but began earlier.
3.There is no overlap between ‘0’ and ‘1’
4.There is no point in time when both events ‘0’ and ‘1’ are occurring

Answer:
Hint 1 means 0 overlaps 2.
Hint 2 means 2 finished_by 1.
So, by combining hint 1 and hint 2, we can deduce that the relationship between 0 and 1 can be described in the following ways:
- 0 precedes 1 (p)
- 0 meets 1 (m)
- 0 finished_by 1 (o)
Then, hint 3 states that there is no overlap between '0' and '1', which eliminates the possibilities of '0 overlaps 1 (o)'.
Then, hint 4 states that there is no point in time when both events '0' and '1' are occurring, which eliminates the possibilities of '0 meets 1 (m)'.
So the only possible relationship left is '0 precedes 1 (p)'.
"""

post_question = """I will provide all hints step by step. 
For each hint, you must guess all possible relationships answer and only answer directly the abbreviations of these relationships.
You should only answer directly the abbreviations of final answer after all hints have been provided.
Remember no need to provide me with the thought process. Just provide your thoughtfully considered answer.
If there are more than six possibilities, you only need to answer 'I can not determine'.
"""

detail_post_question = """I will provide all hints step by step. 
For each hint, you must guess all possible relationships answer and give your reasoning. 
You should provide your thoughtfully considered thinking process, explaining how each hint influences your reasoning, before finally answering with the abbreviations of final answer after all hints have been provided.
If there are more than six possibilities, you only need to answer 'I can not determine'.
"""


def multi_chat(sample, model):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    question = (
        f"Please help me determine the allen relationship between '\n"
        f"{sample['events'][l]}{l}' and '{sample['events'][r]}{r}' based on following hints."
    )
    hints = sample["hints"]
    messages = [
        {"role": "system", "content": allen_helper + few_shot_examples},
    ]
    question += post_question + "\n"
    for i in range(len(hints)):
        if i == 0:
            messages.append({"role": "user", "content": question + hints[i]})
        else:
            messages.append({"role": "user", "content": hints[i]})
        result = call_api(messages, model)
        # print(result)
        messages.append({"role": "assistant", "content": result})
        answers.append(result)
        sleep(1)
    return answers


def single_chat(sample, model):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    hints = sample["hints"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}{l}' and '{sample['events'][r]}{r}' based on following hints steps by steps."
    )
    # question += post_question + "\n"
    question += detail_post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    messages = [
        # {"role": "system", "content": allen_helper + few_shot_examples},
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    try:
        result = call_api(messages, model)
    except Exception as e:
        result = "API调用失败"
    # print(result)
    answers.append(result)
    sleep(1)
    return answers


def process_sample(index, sample, chat_type, model):
    print(f"== 正在处理第 {index + 1} 个用例 ==")
    if chat_type == "multi":
        return multi_chat(sample, model)
    if chat_type == "single":
        return single_chat(sample, model)
    raise ValueError(f"Unsupported chat_type: {chat_type}")


def _atomic_dump_json(path: str, data) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp_path, path)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _split_indices_contiguous(total: int, workers: int):
    """Split [0, total) into contiguous blocks.

    n = total // workers
    thread 0 -> [0, n)
    thread 1 -> [n, 2n)
    ...
    last thread -> [k*n, total)
    """
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


def _recover_answers_from_temp(
    samples, answer_key: str, output_dir: str, name: str
) -> int:
    """Recover already-generated answers from per-thread temp files.

    Expected temp format (per line-item):
    - {"index": i, "sample": { ... , answer_key: ... }}
    - {"index": i, "skipped": true, "error": "..."}

    Only entries containing a valid `sample[answer_key]` are restored.
    """
    pattern = os.path.join(output_dir, f"{name}_*.json")
    paths = sorted(glob.glob(pattern))
    if not paths:
        return 0

    restored = 0
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int) or not (0 <= index < len(samples)):
                continue
            sample_obj = item.get("sample")
            if not isinstance(sample_obj, dict):
                continue
            if answer_key not in sample_obj:
                continue

            # Only update the answer field to avoid overwriting other fields.
            samples[index][answer_key] = sample_obj[answer_key]
            restored += 1

    return restored


def main():
    parser = argparse.ArgumentParser(description="Run script with parameters")
    parser.add_argument("--name", type=str, help="需要生成答案的文件名")
    parser.add_argument(
        "--chat_type",
        type=str,
        choices=["single", "multi"],
        required=True,
        help="chat类型(single/multi)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行调用线程数",
    )
    parser.add_argument(
        "--merge_only",
        action="store_true",
        help="只从temp恢复并整合输出，不再调用API",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="调用的模型名称",
    )
    args = parser.parse_args()

    samples = json.load(open(f"datasets/{args.name}.json", "r"))

    answer_key = f"answer_{args.chat_type}"

    output_dir = f"datasets/temp/{args.name}"
    _ensure_dir(output_dir)

    # 从 temp 恢复已生成的答案（用于异常终止后的断点续跑）
    restored = _recover_answers_from_temp(samples, answer_key, output_dir, args.name)
    if restored:
        print(f"已从temp恢复答案条目: {restored}")

    processed_indices = {
        index for index, sample in enumerate(samples) if answer_key in sample
    }
    if processed_indices:
        print(f"已存在答案的样本数: {len(processed_indices)} / {len(samples)}")

    if args.merge_only:
        final_path = f"datasets/answers/{args.name}_with_answers.json"
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=4, ensure_ascii=False)
        print(f"已完成整合并保存到 {final_path}")
        return

    total = len(samples)
    worker_count = max(1, args.workers)
    slices = _split_indices_contiguous(total, worker_count)
    if not slices:
        print("输入数据为空")
        return

    progress_lock = Lock()

    def worker_task(worker_id: int, start: int, end: int):
        thread_no = worker_id + 1
        thread_out_path = os.path.join(output_dir, f"{args.name}_{thread_no}.json")
        thread_results = []

        # If file already exists, load it so we can continue appending.
        if os.path.exists(thread_out_path):
            try:
                with open(thread_out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    thread_results = existing
            except Exception:
                thread_results = []

        print(f"线程 {thread_no} 负责区间: [{start}, {end})")

        for index in range(start, end):
            if index in processed_indices:
                continue

            try:
                answers = process_sample(
                    index, samples[index], args.chat_type, args.model
                )
                with progress_lock:
                    samples[index][answer_key] = answers
                    processed_indices.add(index)

                thread_results.append({"index": index, "sample": samples[index]})
                _atomic_dump_json(thread_out_path, thread_results)
            except Exception as e:
                # 错误处理：遇到错误跳过即可
                print(
                    f"  ❌ 线程 {thread_no} 处理第 {index + 1} 个用例出错，已跳过: {e}"
                )
                thread_results.append(
                    {"index": index, "skipped": True, "error": str(e)}
                )
                _atomic_dump_json(thread_out_path, thread_results)
                continue

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(worker_task, worker_id, start, end)
            for worker_id, start, end in slices
            if end > start
        ]
        for future in as_completed(futures):
            future.result()

    # 答案整合：所有线程都处理完后，输出最终答案文件
    final_path = f"datasets/answers/{args.name}_with_answers.json"
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)

    print(f"Generated answers and saved to {final_path}")


if __name__ == "__main__":
    main()
