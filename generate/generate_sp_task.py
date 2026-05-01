import json
import random
import copy
import argparse

from generate.hint import get_rels_explanations
from generate.generate_hints import (
    get_relation_hint,
    generate_hint,
    generate_exclude_hint,
)
from utils.relation import get_left_node, get_right_node


def get_target_hint(target_rel, events, l_no=0, r_no=1):
    return get_relation_hint(target_rel, l_no, r_no, events)


def generate_fill(sample):
    """
    Generate a fill-in-the-blank question.
    Given： 1. Original hints with one hint deleted 2. Target relation
    Deleted hint: related to a relation hint
    Expect Answer: The deleted relation and its excluded relations
    """
    new_sample = copy.deepcopy(sample)
    new_hints = []
    new_explanations = []
    candidate_path_no = []

    for i in range(len(sample["paths"])):
        path = sample["paths"][i]
        if path["left"] == -1 or path["right"] == -1:
            candidate_path_no.append(i)

    path_no = random.choice(candidate_path_no)
    deleted_path = sample["paths"][path_no]
    for p in new_sample["paths"]:
        if p == deleted_path:
            target = deleted_path["target"]
            base_left, base_right = deleted_path["base_event"]
            new_event = deleted_path["new_event"]
            if p["left"] == -1:
                bridge_rel = deleted_path["path"][1]
                blank_left, blank_right = base_left, new_event
                blank_rels = get_left_node(bridge_rel, target)
                hint_left, hint_right = new_event, base_right
            else:
                bridge_rel = deleted_path["path"][0]
                blank_left, blank_right = new_event, base_right
                blank_rels = get_right_node(bridge_rel, target)
                hint_left, hint_right = base_left, new_event

            new_sample["target"]["blank_object"] = [blank_left, blank_right]
            new_sample["target"]["blank_candidate"] = get_rels_explanations(
                blank_rels,
                blank_left,
                blank_right,
                new_sample["events"],
            )

            bridge_hint = get_relation_hint(
                bridge_rel,
                hint_left,
                hint_right,
                new_sample["events"],
            )
            new_hints.append(bridge_hint["hint"])
            new_explanations.append(bridge_hint["explanation"])

            target_hint = get_relation_hint(
                target,
                base_left,
                base_right,
                new_sample["events"],
            )
            new_hints.append(target_hint["hint"])
            new_explanations.append(target_hint["explanation"])
        else:
            p_hints = generate_hint(p, new_sample["events"], "indirect pos")
            hint_texts = [h["hint"] for h in p_hints]
            explanation_texts = [h["explanation"] for h in p_hints]
            new_hints.extend(hint_texts)
            new_explanations.extend(explanation_texts)

    new_sample["hints"] = new_hints
    new_sample["explanation"] = new_explanations
    return new_sample


def generate_conflict(sample):
    """
    Generate a conflict-detect question.
    Given: 1. Original hints with one hint replaced 2. Target relation
    Replaced hint: Convert to antisense hint
    Need: convert_anti_hint()
    Step: 1. Choose a leaf-parent hint to replace 2. Replace it with its antisense form 3. Save the replaced hint as 'conflict_hint' and 'conflict num' 4. Add a new hint 'target_hint' to the hints list
    """
    new_sample = copy.deepcopy(sample)
    del new_sample["explanation"]
    hints = []
    explanations = []

    # find candidate paths
    candidate_path_no = []
    for i in range(len(sample["paths"])):
        path = sample["paths"][i]
        if path["left"] == -1 and path["right"] == -1:
            candidate_path_no.append(i)
    if not candidate_path_no:
        print(new_sample["id"], "no candidate path for conflict generation")
        new_sample["target"]["conflict_no"] = -1
        return new_sample
    path_no = random.choice(candidate_path_no)
    replaced_path = sample["paths"][path_no]

    for p in new_sample["paths"]:
        if p == replaced_path:
            left_hint = get_relation_hint(
                p["path"][0], p["base_event"][0], p["new_event"], new_sample["events"]
            )
            right_hint = get_relation_hint(
                p["path"][1], p["new_event"], p["base_event"][1], new_sample["events"]
            )
            candidate_targets = replaced_path["excluded"]
            candidate_targets.append(replaced_path["target"])
            conflict_hint = generate_exclude_hint(
                candidate_targets,
                p["base_event"][0],
                p["base_event"][1],
                new_sample["events"],
            )
            hints.append(left_hint["hint"])
            explanations.append(left_hint["explanation"])
            hints.append(right_hint["hint"])
            explanations.append(right_hint["explanation"])
            hints.append(conflict_hint["hint"])
            explanations.append(conflict_hint["explanation"])
            # Hint No. from 1
            new_sample["target"]["conflict_no"] = len(hints)
        else:
            p_hints = generate_hint(p, new_sample["events"], "indirect pos")
            hints.extend([h["hint"] for h in p_hints])
            explanations.extend([h["explanation"] for h in p_hints])

    target = new_sample.get("target", {})
    target_rel = target.get("rel")
    target_hint = get_target_hint(target_rel, new_sample["events"])
    hints.append(target_hint["hint"])
    explanations.append(target_hint["explanation"])

    new_sample["hints"] = hints
    new_sample["explanations"] = explanations
    return new_sample


def generate_fillblank_task(name):
    """
    1. Load an existing dataset
    2. For each sample, generate a fill-in-the-blank question
    3. Save the new dataset
    """
    with open(f"datasets/{name}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    output = [generate_fill(sample) for sample in data]

    with open(f"datasets/{name}_fillblank.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(
        f"Fill-in-the-blank task generated and saved to datasets/{name}_fillblank.json"
    )


def generate_conflict_task(name):
    """
    1. Load an existing dataset
    2. For each sample, generate a conflict-detect question
    3. Save the new dataset
    """
    with open(f"datasets/{name}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    output = [generate_conflict(sample) for sample in data]

    with open(f"datasets/{name}_conflict.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(f"Conflict-detect task generated and saved to datasets/{name}_conflict.json")


def main():
    parser = argparse.ArgumentParser(description="Generate special tasks from dataset")
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="基础数据集文件名（不含 .json）",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["conflict", "fill"],
        required=True,
        help="任务类型：conflict/fill",
    )
    args = parser.parse_args()

    if args.type == "conflict":
        generate_conflict_task(args.name)
    elif args.type == "fill":
        generate_fillblank_task(args.name)


if __name__ == "__main__":
    main()
