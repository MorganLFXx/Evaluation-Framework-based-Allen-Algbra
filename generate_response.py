import argparse
import json
import os
from utils.chat import call_pony_api
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed

allen_helper = """You are an expert in time relation judgment, well-versed in Allen's interval algebra.
This mathematical framework defines 13 fundamental types of temporal relationships：
precedes(p), preceded_by(P), meets(m), met_by(M), overlaps(o), overlapped_by(O), finished_by(F), finishes(f), contains(D), during(d), starts(s), started_by(S), equals(e).
Here are some things to note: 
1. 'A overlaps B' means that there is overlap between A and B but A starts before B. 'A overlapped_by B' means A and B still overlap, but B starts before A. 
2. 'A starts B' means A and B start at the same time but A ends before B. 'A started_by B' means A and B start at the same time but B ends before A.
3. 'finishes' means A and B end at the same time but A starts after B. 'finished_by' means A and B end at the same time but B starts after A.
The correspondence between uppercase and lowercase letters of the same letter is inverse. For example, A p B is equivalent to B P A.
"""
# TIME_GRANULARITY = "The basic time granularity is day. For example, A(2020.2.1-2022.2.3) and B(2022.2.3-2024.4.5) have the relation 'meets' because A ends when B starts."

# few_shot_examples = """Here are an example:

# """

post_question = """I will provide all hints step by step. 
Each time, you must guess all possible relationships answer and only answer directly the abbreviations of these relationships.
Remember no need to provide me with the thought process. Just provide your thoughtfully considered answer.
If there are more than six possibilities, you only need to answer 'I can not determine'.
"""


def multi_chat(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    question = f"Please help me determine the allen relationship between '{sample["events"][l]}{l}' and '{sample["events"][r]}{r}' based on following hints."
    hints = sample["hints"]
    messages = [
        {"role": "system", "content": allen_helper},
    ]
    question += post_question + "\n"
    for i in range(len(hints)):
        if i == 0:
            messages.append({"role": "user", "content": question + hints[i]})
        else:
            messages.append({"role": "user", "content": hints[i]})
        result = call_pony_api(messages)
        # print(result)
        messages.append({"role": "assistant", "content": result})
        answers.append(result)
        sleep(1)
    return answers


def single_chat(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    hints = sample["hints"]
    question = f"Please help me determine the allen relationship between '{sample["events"][l]}{l}' and '{sample["events"][r]}{r}' based on following hints."
    question += post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    result = call_pony_api(messages)
    # print(result)
    answers.append(result)
    sleep(1)
    return answers


def process_sample(index, sample, chat_type):
    print(f"== 正在处理第 {index + 1} 个用例 ==")
    if chat_type == "multi":
        return multi_chat(sample)
    if chat_type == "single":
        return single_chat(sample)
    raise ValueError(f"Unsupported chat_type: {chat_type}")


def dump_progress(samples, processed_indices, temp_path):
    next_index = next(
        (i for i in range(len(samples)) if i not in processed_indices),
        len(samples),
    )
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "samples": samples,
                "next_index": next_index,
                "completed_indices": sorted(processed_indices),
            },
            f,
            indent=4,
            ensure_ascii=False,
        )


def main():
    temp_path = "datasets/temp_response.json"
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
    args = parser.parse_args()
    if os.path.exists(f"datasets/{args.name}_with_answers.json"):
        samples = json.load(open(f"datasets/{args.name}_with_answers.json", "r"))
    else:
        samples = json.load(open(f"datasets/{args.name}.json", "r"))

    answer_key = f"answer_{args.chat_type}"
    processed_indices = set()

    if os.path.exists(temp_path):
        with open(temp_path, "r", encoding="utf-8") as f:
            temp_data = json.load(f)
            samples = temp_data["samples"]
            processed_indices.update(temp_data.get("completed_indices", []))
            next_index_hint = temp_data.get("next_index")
            if next_index_hint is not None and not temp_data.get("completed_indices"):
                processed_indices.update(range(next_index_hint))
        processed_indices.update(
            index for index, sample in enumerate(samples) if answer_key in sample
        )
        next_unprocessed = next(
            (i for i in range(len(samples)) if i not in processed_indices),
            len(samples),
        )
        if next_unprocessed < len(samples):
            print(f"从临时文件恢复，继续从第 {next_unprocessed + 1} 个用例开始")
        else:
            print("临时文件表明所有用例已完成")
    else:
        processed_indices = {
            index for index, sample in enumerate(samples) if answer_key in sample
        }

    remaining_indices = [i for i in range(len(samples)) if i not in processed_indices]
    processed_since_last_dump = 0

    if remaining_indices:
        max_workers = max(1, args.workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    process_sample,
                    index,
                    samples[index],
                    args.chat_type,
                ): index
                for index in remaining_indices
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    answers = future.result()
                    samples[index][answer_key] = answers
                    processed_indices.add(index)
                    processed_since_last_dump += 1
                    if processed_since_last_dump >= 10:
                        dump_progress(samples, processed_indices, temp_path)
                        processed_since_last_dump = 0
                except Exception as e:
                    print(f"  ❌ 第 {index + 1} 个用例出错: {e}")
                    dump_progress(samples, processed_indices, temp_path)
                    raise
    else:
        print("所有用例已处理完成")

    if processed_since_last_dump > 0 and remaining_indices:
        dump_progress(samples, processed_indices, temp_path)

    with open(f"datasets/{args.name}_with_answers.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    print(f"Generated answers and saved to {args.name}_with_answers.json")


if __name__ == "__main__":
    main()
