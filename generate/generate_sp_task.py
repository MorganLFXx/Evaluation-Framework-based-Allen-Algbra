import json
import random
import copy
from turtle import right

from ray import get
from generate.hint import judge_relation_hint, convert_anti_hint, get_rels_explanations
from generate.generate_hints import get_relation_hint, generate_hint
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
    candidate_path_no = []

    for i in range(len(sample["paths"])):
        path = sample["paths"][i]
        if path["left"] == -1 or path["right"] == -1:
            candidate_path_no.append(i)

    path_no = random.choice(candidate_path_no)
    deleted_path = sample["paths"][path_no]
    for p in new_sample["paths"]:
        if p == sample["paths"][path_no]:
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
            )["hint"]
            new_hints.append(bridge_hint)

            target_hint = get_relation_hint(
                target,
                base_left,
                base_right,
                new_sample["events"],
            )["hint"]
            new_hints.append(target_hint)
        else:
            p_hints = generate_hint(p, new_sample["events"], "indirect pos")["hint"]
            new_hints.extend(p_hints["hint"])

    del new_sample["explanation"]  # no need
    new_sample["hints"] = new_hints
    return new_sample


def generate_conflict(sample):
    """
    Generate a conflict-detect question.
    Given: 1. Original hints with one hint replaced 2. Target relation
    Replaced hint: Convert to antisense hint
    Need: convert_anti_hint()
    Step: 1. Randomly select a hint to replace 2. Replace it with its antisense form 3. Save the replaced hint as 'conflict_hint' and 'conflict num' 4. Add a new hint 'target_hint' to the hints list
    """
    new_sample = copy.deepcopy(sample)
    del new_sample["explanation"]  # no need
    hints = new_sample.get("hints", [])

    candidate_ids = []
    for i in range(len(hints)):
        if not judge_relation_hint(hints[i]):
            candidate_ids.append(i)

    if not candidate_ids:
        # If there are no non-relation hints, we cannot create a conflict. Return the original sample.
        new_sample["target"]["conflict_no"] = -1
        return new_sample
    conflict_id = random.choice(candidate_ids)
    original_hint = hints[conflict_id]
    conflict_hint = convert_anti_hint(original_hint)

    hints[conflict_id] = conflict_hint
    new_sample["target"]["conflict_no"] = conflict_id
    new_sample["target"]["original_hint"] = original_hint

    target = new_sample.get("target", {})
    target_rel = target.get("rel")
    target_hint = get_target_hint(target_rel, new_sample["events"])["hint"]
    hints.append(target_hint)

    new_sample["hints"] = hints
    return new_sample


def generate_fillblank_task():
    """
    1. Load an existing dataset
    2. For each sample, generate a fill-in-the-blank question
    3. Save the new dataset
    """
    with open("datasets/debug_bases_1.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    output = [generate_fill(sample) for sample in data]

    with open("datasets/debug_fillblank_1.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print(
        "Fill-in-the-blank task generated and saved to datasets/debug_fillblank_1.json"
    )


def generate_conflict_task():
    """
    1. Load an existing dataset
    2. For each sample, generate a conflict-detect question
    3. Save the new dataset
    """
    with open("datasets/debug_bases_1.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    output = [generate_conflict(sample) for sample in data]

    with open("datasets/debug_conflict_1.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    print("Conflict-detect task generated and saved to datasets/debug_conflict_1.json")


def main():
    generate_fillblank_task()
    generate_conflict_task()


if __name__ == "__main__":
    main()
