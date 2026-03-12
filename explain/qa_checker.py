import json
import argparse
import csv


def sample_check(sample):
    if sample["answer_single"][0].strip().startswith("<think>"):
        return False
    return sample["answer_single"][0].strip() == sample["target"]["rel"]


def model_error_overlap_check():
    """
    比较不同模型在相同数据集上的错误重叠度。
    1) 输入多个文件名（不含 _with_answers.json）
    2) 样例仅包含 target 和 answer
    3) 不同文件中相同 id 表示同一问题
    """
    parser = argparse.ArgumentParser(
        description="Check overlap of model errors on the same dataset"
    )
    parser.add_argument(
        "--names",
        nargs="+",
        required=True,
        help="待校验的数据集文件名（不含 _with_answers.json）",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=5,
        help="每组重合样例最多展示的数量",
    )
    args = parser.parse_args()

    def normalize_answer_tokens(answer):
        if answer is None:
            return []
        text = str(answer).strip()
        if not text or text.startswith("<think>"):
            return []
        text = text.replace(",", " ")
        tokens = [t.strip() for t in text.split() if t.strip()]
        return tokens

    def answer_display(tokens):
        if not tokens:
            return "None"
        if len(tokens) == 1:
            return tokens[0]
        return ",".join(tokens)

    error_sets = {}
    error_details = {}

    for name in args.names:
        with open(
            f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8"
        ) as f:
            data = json.load(f)

        current_errors = {}
        for idx, item in enumerate(data):
            target = item.get("target", {}).get("rel")
            raw_answer = None
            if "answer_single" in item and item["answer_single"]:
                raw_answer = item["answer_single"][0]

            tokens = normalize_answer_tokens(raw_answer)
            is_correct = len(tokens) == 1 and tokens[0] == target
            if not is_correct:
                sample_id = item.get("id", idx)
                current_errors[sample_id] = {
                    "id": sample_id,
                    "target": target,
                    "answer": answer_display(tokens),
                }

        error_sets[name] = set(current_errors.keys())
        error_details[name] = current_errors
        print(f"{name}: errors {len(current_errors)}/{len(data)}")

    names = list(error_sets.keys())
    if len(names) < 2:
        print("需要至少两个数据集才能计算重合情况。")
        return

    print("\nPairwise overlap:")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            left, right = names[i], names[j]
            overlap = error_sets[left] & error_sets[right]
            print(f"{left} & {right}: {len(overlap)}")
            if args.show > 0 and overlap:
                for sample_id in list(overlap)[: args.show]:
                    info = error_details[left].get(sample_id) or error_details[
                        right
                    ].get(sample_id)
                    print(
                        f"  sample id={info['id']}, target={info['target']}, answer={info['answer']}"
                    )

    common = set.intersection(*(error_sets[name] for name in names))
    print(f"\nCommon overlap (all models): {len(common)}")
    if args.show > 0 and common:
        for sample_id in list(common)[: args.show]:
            info = error_details[names[0]].get(sample_id)
            if info is None:
                continue
            print(
                f"  sample id={info['id']}, target={info['target']}, answer={info['answer']}"
            )


def overlap_check():
    """
    得到的每个数据集的错误信息如下，包括其中每个错误样例的target和answer：
            错误样例: target=D, answer=o,F,D
            错误样例: target=o, answer=o, F, D
            错误样例: target=O, answer=d, f, O
            错误样例: target=F, answer=D F
            错误样例: target=D, answer=p m
            错误样例: target=O, answer=d,f,O
    我希望检查不同数据集的错误结果的重合情况，看看是否有一些特别难的样例在不同数据集中都出现了错误。
    注：请注意，target的格式是标准的，但answer的格式可能会有一些差异，比如有的用逗号分隔，有的用空格分隔，有的答案前后有空格等，请你注意排除这一影响。
    """
    parser = argparse.ArgumentParser(
        description="Check overlap of error samples across datasets"
    )
    parser.add_argument(
        "--names",
        nargs="+",
        required=True,
        help="待校验的数据集文件名（不含 _with_answers.json）",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=5,
        help="每组重合样例最多展示的数量",
    )
    args = parser.parse_args()

    def normalize_answer_tokens(answer):
        if answer is None:
            return []
        text = str(answer).strip()
        if not text or text.startswith("<think>"):
            return []
        text = text.replace(",", " ")
        tokens = [t.strip() for t in text.split() if t.strip()]
        return tokens

    def answer_display(tokens):
        if not tokens:
            return "None"
        if len(tokens) == 1:
            return tokens[0]
        return ",".join(tokens)

    def sample_signature(item):
        signature_payload = {
            "target": item.get("target"),
            "events": item.get("events"),
            "paths": item.get("paths"),
        }
        return json.dumps(signature_payload, sort_keys=True, ensure_ascii=False)

    error_sets = {}
    error_details = {}

    for name in args.names:
        with open(
            f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8"
        ) as f:
            data = json.load(f)

        current_errors = {}
        for idx, item in enumerate(data):
            target = item.get("target", {}).get("rel")
            raw_answer = None
            if "answer_single" in item and item["answer_single"]:
                raw_answer = item["answer_single"][0]

            tokens = normalize_answer_tokens(raw_answer)
            is_correct = len(tokens) == 1 and tokens[0] == target
            if not is_correct:
                sig = sample_signature(item)
                current_errors[sig] = {
                    "id": item.get("id", idx),
                    "target": target,
                    "answer": answer_display(tokens),
                }

        error_sets[name] = set(current_errors.keys())
        error_details[name] = current_errors
        print(f"{name}: errors {len(current_errors)}/{len(data)}")

    names = list(error_sets.keys())
    if len(names) < 2:
        print("需要至少两个数据集才能计算重合情况。")
        return

    print("\nPairwise overlap:")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            left, right = names[i], names[j]
            overlap = error_sets[left] & error_sets[right]
            print(f"{left} & {right}: {len(overlap)}")
            if args.show > 0 and overlap:
                for sig in list(overlap)[: args.show]:
                    info = error_details[left].get(sig) or error_details[right].get(sig)
                    print(
                        f"  sample id={info['id']}, target={info['target']}, answer={info['answer']}"
                    )

    common = set.intersection(*(error_sets[name] for name in names))
    print(f"\nCommon overlap (all datasets): {len(common)}")
    if args.show > 0 and common:
        for sig in list(common)[: args.show]:
            info = error_details[names[0]].get(sig)
            if info is None:
                continue
            print(
                f"  sample id={info['id']}, target={info['target']}, answer={info['answer']}"
            )


# deprecated
# def count():
#     parser = argparse.ArgumentParser(description="Run script with parameters")
#     parser.add_argument("--name", type=str, required=True, help="校验的文件名")
#     args = parser.parse_args()
#     with open(
#         f"datasets/answers/{args.name}_with_answers.json", "r", encoding="utf-8"
#     ) as f:
#         data = json.load(f)

#     level1 = 0
#     level2 = 0
#     right = 0
#     level1_true = 0
#     level2_true = 0
#     i, j = 0, 0
#     for item in data:
#         check = 1 if sample_check(item) else 0
#         if len(item["paths"]) == 1:
#             if item["level"] == 1:
#                 level1 += 1
#                 level1_true += check
#                 if check == 0 and i < 20:
#                     answer = item["answer_single"][0].strip()
#                     if answer.startswith("<think>"):
#                         answer = "None"
#                     print(
#                         f"level1错误样例: target={item['target']['rel']}, answer={answer}"
#                     )
#                     i += 1
#             elif item["level"] == 2:
#                 level2 += 1
#                 level2_true += check
#                 if check == 0 and j < 20:
#                     answer = item["answer_single"][0].strip()
#                     if answer.startswith("<think>"):
#                         answer = "None"
#                     print(
#                         f"level2错误样例: target={item['target']['rel']}, answer={answer}"
#                     )
#                     j += 1
#         else:
#             right += check
#             if check == 0:
#                 answer = item["answer_single"][0].strip()
#                 if answer.startswith("<think>"):
#                     answer = "None"
#                 print(
#                     f"id {item['id']}: target={item['target']['rel']}, answer={answer}"
#                 )

#     if len(data[0]["paths"]) == 1:
#         print(f"Level 1 Accuracy: {level1_true}/{level1} = {level1_true/level1:.4f}")
#         print(f"Level 2 Accuracy: {level2_true}/{level2} = {level2_true/level2:.4f}")
#     else:
#         print(f"Overall Accuracy: {right}/{len(data)} = {right/len(data):.4f}")


def answer_verify(name):
    if not name:
        raise ValueError("name is required")
    with open(f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        item["right"] = sample_check(item)
        check = 1 if item["right"] else 0
        right += check
    json.dump(
        data,
        open(f"datasets/answers/{name}_with_answers.json", "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=4,
    )
    print(f"Accuracy: {right}/{len(data)} = {right/len(data):.4f}")
    return right


def link_count():
    right_map = {}
    error_map = {}
    new_test = []
    with open(
        f"datasets/answers/test_link_len_dsv32" + "_with_answers.json",
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)
    for item in data:
        check = 1 if sample_check(item) else 0
        link_len = len(item["paths"])
        if check == 0:
            if len(item["paths"]) <= 3:
                new_test.append(item)
            answer = item["answer_single"][0].strip()
            if answer.startswith("<think>"):
                answer = "None"
            path_info = f"{item['paths'][0]['path'][0]}{item['paths'][0]['path'][1]}"
            print(
                f"id {item['id']}: target={item['target']['rel']}, path={path_info}, answer={answer}, len={link_len}, right={item['right']}"
            )
        if item["right"]:
            right_map[link_len] = right_map.get(link_len, 0) + check
        else:
            error_map[link_len] = error_map.get(link_len, 0) + check

    for item in right_map.items():
        link_len, correct = item
        if link_len == 1:
            total = 10
        else:
            total = 40
        print(
            f"Link Length {link_len}: Accuracy {correct}/{total} = {correct/total:.4f}"
        )
    for item in error_map.items():
        link_len, correct = item
        if link_len == 1:
            total = 10
        else:
            total = 40
        print(
            f"Error Link Length {link_len}: Accuracy {correct}/{total} = {correct/total:.4f}"
        )

    i = 0
    for item in new_test:
        del item["answer_single"]
        item["id"] = i
        i += 1

    with open(f"datasets/test_link_len_error_qwen.json", "w", encoding="utf-8") as f:
        json.dump(new_test, f, ensure_ascii=False, indent=4)


def main(mode="answer_verify", name=None, names=None, show=5):
    if mode == "answer_verify":
        answer_verify(name)
    # elif mode == "overlap_check":
    #     overlap_check(names, show)
    # elif mode == "model_error_overlap_check":
    #     model_error_overlap_check(names, show)
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    # link_count()
    # count()
    # model_error_overlap_check()
    # overlap_check()


if __name__ == "__main__":
    main(mode="answer_verify", name="sample")
