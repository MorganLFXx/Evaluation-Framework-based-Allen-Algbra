import argparse
from ctypes.wintypes import HINSTANCE
from email import message
import json
from multiprocessing.connection import answer_challenge
import os
from utils.chat import call_pony_api
from time import sleep

allen_helper = """You are an expert in time relation judgment, well-versed in Allen's interval algebra.
This mathematical framework defines 13 fundamental types of temporal relationships：
precedes(p), preceded_by(P), meets(m), met_by(M), overlaps(o), overlapped_by(O), finished_by(F), finishes(f), contains(D), during(d), starts(s), started_by(S), equals(e).
Here are some things to note: 1. 'A overlaps B' means that there is overlap between A and B but A starts before B 2. 'starts' means A and B start at the same time but A ends before B 3. 'finishes' means A and B end at the same time but A starts after B.
The basic time granularity is day. For example, A(2020.2.1-2022.2.3) and B(2022.2.3-2024.4.5) have the relation 'meets' because A ends when B starts.
The correspondence between uppercase and lowercase letters of the same letter is inverse. For example, A p B is equivalent to B P A.
"""

post_question = """I will provide all hints step by step. 
Each time, you must guess all possible relationships answer and only answer directly the abbreviations of these relationships.
Remember no need to provide me with the thought process. Just provide your thoughtfully considered answer.
If there are more than six possibilities, you only need to answer 'I can not determine'.
"""


def multi_chat(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    question = f"Please help me determine the allen relationship between {sample["events"][l]}{l} and {sample["events"][r]}{r} based on following hints."
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
        print(result)
        messages.append({"role": "assistant", "content": result})
        answers.append(result)
        sleep(1)
    return answers


def single_chat(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    hints = sample["hints"]
    question = f"Please help me determine the allen relationship between {sample["events"][l]}{l} and {sample["events"][r]}{r} based on following hints."
    question += post_question + "\n"
    for i in range(len(hints)):
        question += hints[i]
        messages = [
            {"role": "system", "content": allen_helper},
            {"role": "user", "content": question},
        ]
        result = call_pony_api(messages)
        print(result)
        answers.append(result)
        sleep(1)
    print(answers[-1])
    return answers


def main():
    temp_path = "datasets/temp_response.json"
    parser = argparse.ArgumentParser(description="Run script with parameters")
    parser.add_argument("--name", type=str, help="需要生成答案的文件名")
    parser.add_argument("--chat_type", type=str, help="chat类型(single/multi)")
    args = parser.parse_args()
    if os.path.exists(f"datasets/{args.name}_with_answers.json"):
        samples = json.load(open(f"datasets/{args.name}_with_answers.json", "r"))
    else:
        samples = json.load(open(f"datasets/{args.name}.json", "r"))

    # 恢复进度（如果存在临时文件）
    start_index = 0
    if os.path.exists(temp_path):
        with open(temp_path, "r", encoding="utf-8") as f:
            temp_data = json.load(f)
            samples = temp_data["samples"]
            start_index = temp_data["next_index"]
        print(f"从临时文件恢复，继续从第 {start_index + 1} 个用例开始")

    for i in range(start_index, len(samples)):
        sample = samples[i]
        print(f"== 正在处理第 {i+1} 个用例 ==")
        try:
            if args.chat_type == "multi":
                answers = multi_chat(sample)
            elif args.chat_type == "single":
                answers = single_chat(sample)
            sample[f"answer_{args.chat_type}"] = answers

            # 保存临时进度
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"samples": samples, "next_index": i + 1},
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

        except Exception as e:
            print(f"  ❌ 第 {i+1} 个用例出错: {e}")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"samples": samples, "next_index": i},
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
            raise e

    with open(f"datasets/{args.name}_with_answers.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)

    if os.path.exists(temp_path):
        os.remove(temp_path)

    print(f"Generated answers and saved to {args.name}_with_answers.json")


if __name__ == "__main__":
    main()
