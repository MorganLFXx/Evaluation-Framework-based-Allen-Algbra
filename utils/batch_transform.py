"""仅用于实验中方便平台使用平台的批量推理功能，非正式工具"""

import json
import os
import argparse

from generate.generate_response import (
    detail_post_question,
    allen_helper,
    post_question_conflict,
    post_question_fill,
    detail_post_question_conflict,
    detail_post_question_fill,
)
from utils.format import parse_json_block

model_problem = (
    "I can not determine.(The model may be overthinking or the output is truncated.)"
)


def item2single(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    hints = sample["hints"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information steps by steps."
    )
    question += detail_post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def item2singleQA(sample):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    hints = sample["hints"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information steps by steps."
    )
    question += detail_post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    ground_truth = sample["target"]["rel"]

    return {
        "question": question,
        "ground_truth": ground_truth,
    }


def item2conflict(sample):
    question = (
        "There is a conflict hint in the hints. "
        "Please help me find out the conflict hint."
        f"Note: All hints directly describe the relation between 2 events is absolutely correct."
        f"'Directly describe' means you can directly determine the allen relation between 2 event based on this hint without any other hints. "
    )
    hints = sample["hints"]
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    # question += post_question_conflict + "\n"
    question += detail_post_question_conflict
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def item2conflictQA(sample):
    question = (
        "There is a conflict hint in the hints. "
        "Please help me find out the conflict hint."
        f"Note: All hints directly describe the relation between 2 events is absolutely correct."
        f"'Directly describe' means you can directly determine the allen relation between 2 event based on this hint without any other hints. "
    )
    hints = sample["hints"]
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    question += detail_post_question_conflict
    ground_truth = sample["target"]["conflict_no"]
    return {
        "question": question,
        "ground_truth": ground_truth,
    }


def item2fill(sample):
    l_no, r_no = sample["target"]["blank_object"]
    event_l, event_r = sample["events"][l_no], sample["events"][r_no]
    question = (
        f"Among these hints, there is one missing hint that describes the Allen relation between {event_l} and {event_r}."
        f"Based on the existing hints, please describe the order of the start and end time points of {event_l} and {event_r}."
    )
    hints = sample["hints"]
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    # question += post_question_fill + "\n"
    question += detail_post_question_fill + "\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def item2fillQA(sample):
    l_no, r_no = sample["target"]["blank_object"]
    event_l, event_r = sample["events"][l_no], sample["events"][r_no]
    question = (
        f"Among these hints, there is one missing hint that describes the Allen relation between {event_l} and {event_r}."
        f"Based on the existing hints, please describe the order of the start and end time points of {event_l} and {event_r}."
    )
    hints = sample["hints"]
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    question += detail_post_question_fill + "\n"
    ground_truth = sample["target"]["blank_candidate"]
    # process: sample["target"]["blank_candidate"] is like ["'D0' during 'I2' or Start(I2)<Start(D0)<End(D0)<End(I2).","'D0' finishes 'I2' or Start(I2)<Start(D0)<End(D0)=End(I2).","'I2' overlaps 'D0' or Start(I2)<Start(D0)<End(I2)<End(D0)."]
    # I just want the part after "or ", so I split by " or " and take the second part
    ground_truth = [gt.split(" or ")[1] if " or " in gt else gt for gt in ground_truth]
    return {
        "question": question,
        "ground_truth": ground_truth,
    }


def item2question(sample):
    if "conflict_no" in sample["target"]:
        return item2conflict(sample)
    elif "blank_object" in sample["target"]:
        return item2fill(sample)
    else:
        return item2single(sample)


def item2qa(sample):
    if "conflict_no" in sample["target"]:
        return item2conflictQA(sample)
    elif "blank_object" in sample["target"]:
        return item2fillQA(sample)
    else:
        return item2singleQA(sample)


def json_to_jsonl(name):
    """
    将 JSON 文件转换为 JSONL 文件
    :param json_file_path: 输入的 JSON 文件路径
    :param jsonl_file_path: 输出的 JSONL 文件路径
    """
    json_file_path = f"datasets/{name}.json"
    jsonl_file_path = f"datasets/jsonl/{name}.jsonl"
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file_path}")
        return

    try:
        with open(jsonl_file_path, "w", encoding="utf-8") as f:
            i = 0
            for item in json_data:
                messages = item2question(item)
                transformed_item = {
                    "custom_id": i,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "qwen3.5-plus",
                        "messages": messages,
                        "max_tokens": 55000,
                        "enable_thinking": True,
                        "response_format": {"type": "json_object"},
                    },
                }
                f.write(json.dumps(transformed_item, ensure_ascii=False) + "\n")
                i += 1
        print(f"转换成功！JSONL 文件已保存至：{jsonl_file_path}")
    except Exception as e:
        print(f"写入文件失败：{e}")


def jsonl_to_json(name):
    with open(
        f"datasets/answers/{name}_with_answers.jsonl", "r", encoding="utf-8"
    ) as f:
        data = [json.loads(line) for line in f]
    with open(f"datasets/{name}.json", "r", encoding="utf-8") as f:
        original_data = json.load(f)
    for item in data:
        custom_id = int(item["custom_id"])
        _item = original_data[custom_id]
        response = item["response"]["body"]["choices"][0]["message"]["content"]
        if "thinking" in response:
            answer = parse_json_block(response)
            if answer is not None and "answer_single" in answer:
                _item["answer_single"] = [answer.get("answer_single", "")]
                _item["thinking"] = answer.get("thinking", "")
            else:
                _item["answer_single"] = []
        else:
            answer = parse_json_block(response)
            answer = response if answer is None else answer.get("answer_single", "")
            _item["answer_single"] = [answer]
    with open(f"datasets/answers/{name}_with_answers.json", "w", encoding="utf-8") as f:
        json.dump(original_data, f, ensure_ascii=False, indent=4)


def check_bad_samples(name):
    with open(f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8") as f:
        answers = json.load(f)

    new_data = []
    i = 0
    for item in answers:
        if (
            "answer_single" not in item
            or len(item["answer_single"]) == 0
            or item["answer_single"][0] == model_problem
        ):
            item["old_id"] = item["id"]
            item["id"] = i
            i += 1
            del item["answer_single"]
            new_data.append(item)
    print(len(new_data))
    with open(f"datasets/{name}_bad_samples.json", "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)


def merge_bad_samples(name):
    with open(f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8") as f:
        answers = json.load(f)
    with open(
        f"datasets/answers/{name}_bad_samples_with_answers.json", "r", encoding="utf-8"
    ) as f:
        bad_samples = json.load(f)
    for item in bad_samples:
        id = item["old_id"]
        answers[id]["answer_single"] = item["answer_single"]
        answers[id]["thinking"] = item["thinking"]
        answers[id]["right"] = item["right"]

    with open(f"datasets/answers/{name}_with_answers.json", "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=4)

    # rm temp file
    os.remove(f"datasets/answers/{name}_bad_samples_with_answers.json")
    os.remove(f"datasets/{name}_bad_samples.json")


def dataset_reformat(name):
    json_file_path = f"datasets/{name}.json"
    jsonl_file_path = f"datasets/jsonl/{name}.jsonl"
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file_path}")
        return

    try:
        with open(jsonl_file_path, "w", encoding="utf-8") as f:
            i = 0
            for item in json_data:
                transformed_item = item2qa(item)
                transformed_item["id"] = item["id"]
                f.write(json.dumps(transformed_item, ensure_ascii=False) + "\n")
                i += 1
        print(f"转换成功！JSONL 文件已保存至：{jsonl_file_path}")
    except Exception as e:
        print(f"写入文件失败：{e}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch transform tools for Allen inference datasets."
    )
    parser.add_argument(
        "--n2l",
        action="store_true",
        help="Convert datasets/<name>.json to datasets/jsonl/<name>.jsonl",
    )
    parser.add_argument(
        "--l2n",
        action="store_true",
        help="Merge datasets/answers/<name>_with_answers.jsonl into datasets/<name>.json",
    )
    parser.add_argument(
        "--bad",
        action="store_true",
        help="Extract bad samples from datasets/answers/<name>_with_answers.json",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge repaired bad samples back into datasets/answers/<name>_with_answers.json",
    )
    parser.add_argument(
        "--name",
        default="error_samples_batch",
        help=("Dataset base name. "),
    )
    parser.add_argument(
        "--reformat",
        action="store_true",
        help="Reformat datasets/<name>.json to datasets/jsonl/<name>.jsonl with question and ground truth for evaluation.",
    )

    args = parser.parse_args()
    operations = [args.n2l, args.l2n, args.bad, args.merge, args.reformat]
    if sum(operations) == 0:
        parser.error(
            "Please specify one operation flag: -n2l, -l2n, -bad, -merge, or -reformat"
        )

    if args.n2l:
        json_to_jsonl(args.name)
    elif args.l2n:
        jsonl_to_json(args.name)
    elif args.bad:
        check_bad_samples(args.name)
    elif args.merge:
        merge_bad_samples(args.name)
    elif args.reformat:
        dataset_reformat(args.name)


if __name__ == "__main__":
    main()
