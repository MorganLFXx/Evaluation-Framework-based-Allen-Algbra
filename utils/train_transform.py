import json
import argparse


def _detect_task_type(sample):
    target = sample.get("target", {})
    if "conflict_no" in target:
        return "conflict"
    if "blank_no" in target or "blank_object" in target:
        return "fill"
    return "single"


def _build_instruction(sample, task_type):
    if task_type == "single":
        l = sample["target"]["l"]
        r = sample["target"]["r"]
        return (
            "Please help me determine the allen relationship between "
            f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information."
        )

    if task_type == "conflict":
        return (
            "There is a conflict hint in the hints. "
            "Please help me find out the conflict hint."
            "Note: All hints directly describe the relation between 2 events is absolutely correct."
            "'Directly describe' means you can directly determine the allen relation"
            "(Or complete the sorting of four time points including the start and end times of two events) "
            "between 2 event based on this hint without any other hints. "
        )

    l_no, r_no = sample["target"]["blank_object"]
    event_l, event_r = sample["events"][l_no], sample["events"][r_no]
    return (
        f"Among these hints, there is one missing hint that describes the Allen relation between {event_l} and {event_r}."
        f"Based on the existing hints, please describe the order of the start and end time points of {event_l} and {event_r}."
    )


def _build_input(sample):
    hints = sample.get("hints", [])
    return "\n".join(f"{i + 1}.{hint}" for i, hint in enumerate(hints))


def _build_output(sample):
    thinking = sample.get("thinking", "")
    answer_text = sample.get("answer_single", [])[0]
    if thinking:
        return f"{thinking} So the answer is {answer_text}."
    else:
        raise ValueError("Missing thinking process in the sample.")


def _transform_samples(samples):
    transformed = []
    task_type = _detect_task_type(samples[0])
    for sample in samples:
        if (
            "answer_single" not in sample
            or len(sample["answer_single"]) == 0
            or "thinking" not in sample
        ):
            continue
        if "right" not in sample or sample["right"] is not True:
            continue
        transformed.append(
            {
                "instruction": _build_instruction(sample, task_type),
                "input": _build_input(sample),
                "output": _build_output(sample),
            }
        )
    return transformed


def merge(names, output_name="merged_train"):
    """
    Input: a list of names
    Output: a merged dataset json file
    """
    merged = []
    for name in names:
        path = f"datasets/train/{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list in {path}, got {type(data).__name__}.")
        merged.extend(data)

    print(
        f"Merging {len(names)} datasets into {output_name}.json. Total samples: {len(merged)}."
    )

    with open(f"datasets/train/{output_name}.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)


def main():
    """
    Input： A dataset json file
    Output: A list of below format:
        {
            "instruction": "",
            "input": "",
            "output": "",
        }
    """
    parser = argparse.ArgumentParser(
        description="Transform answer dataset into training format."
    )
    parser.add_argument("--name", type=str, help="输入文件名（单个）")
    parser.add_argument(
        "--names",
        type=str,
        nargs="+",
        help="用于 merge 的多个训练集名称（不含 .json 后缀）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="merge 输出文件名（不含 .json 后缀），默认 merged_train",
    )
    args = parser.parse_args()

    if args.names:
        output_name = args.output_name or "merged_train"
        merge(args.names, output_name)
        return

    if not args.name:
        parser.error("Please provide --name for transform, or --names for merge.")

    name = args.name
    with open(f"datasets/answers/{name}_with_answers.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    transformed = _transform_samples(data)
    with open(f"datasets/train/{name}.json", "w", encoding="utf-8") as f:
        json.dump(transformed, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
