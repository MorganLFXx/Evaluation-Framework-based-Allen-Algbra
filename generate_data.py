import random
import argparse
import json
from utils.relation import random_relation, get_composition
from utils.db import get_event_by_rel
from generate_hints import generate_hints


def random_event_name(used_names=None):
    # year events
    events_list = [
        "regional war",
        "siege",
        "government revolution",
        "engineering project",
        "invention process",
        "construction",
        "book writing",
        "tour to study",
        "long-term travel",
        "long-distance migration",
    ]
    if used_names is not None:
        available = [e for e in events_list if e not in used_names]
        if available:
            name = random.choice(available)
        else:
            name = f"{random.choice(events_list)}_{len(used_names)}"
        used_names.add(name)
        return name
    return random.choice(events_list)


def generate_path(target, events, parent):
    """generate paths based on target"""
    l_no = target["l"]
    r_no = target["r"]
    # add a new event
    new_event_no = len(events)
    events.append("")

    # choose composition
    composition = get_composition(target["rel"])
    key, value = composition  # e.g.: (p,p):p
    rel1, rel2 = key
    path = [rel1, rel2]
    excluded = [rel for rel in value if rel != target["rel"]]
    return {
        "target": target["rel"],
        "path": path,
        "excluded": excluded,
        "parent": parent,
        "left": -1,
        "right": -1,
        "base_event": [l_no, r_no],
        "new_event": new_event_no,
    }


def generate_tree(sample):
    events = sample["events"] if sample else []
    target = sample["target"] if sample else {}
    paths = sample["paths"] if sample else []
    # 判断是否base sample，生成target
    if sample is None:
        l_no, r_no = 0, 1
        for _ in range(2):
            events.append("")
        target["l"] = l_no
        target["r"] = r_no
        target["rel"] = random_relation()
        parent = -1
        new_target = target.copy()
    else:
        # 抽取父节点
        parent = random.randint(0, len(paths) - 1)
        while paths[parent]["left"] != -1 and paths[parent]["right"] != -1:
            parent = random.randint(0, len(paths) - 1)
        cur_path = paths[parent]

        # 确认左右节点位置
        if cur_path["left"] != -1:
            child_side = "right"
        elif cur_path["right"] != -1:
            child_side = "left"
        else:
            child_side = random.choice(["left", "right"])
        cur_path[child_side] = len(paths)

        new_target = {}
        new_target["l"] = (
            cur_path["base_event"][0] if child_side == "left" else cur_path["new_event"]
        )
        new_target["r"] = (
            cur_path["new_event"] if child_side == "left" else cur_path["base_event"][1]
        )
        new_target["rel"] = (
            cur_path["path"][0] if child_side == "left" else cur_path["path"][1]
        )

    new_path = generate_path(new_target, events, parent)
    paths.append(new_path)

    return {
        "target": target,
        "events": events,
        "paths": paths,
    }


"""
# get tree
1. 判断是否base
2. 生成target (new/complex)
3. 基于target生成paths(补充formulas留到递归生成结束)

# get hints
1. 补充formulas(?)
2. 生成hints (补充到原来的hints)
"""


def generate_data(sample, hint_type):
    events = sample["events"]
    used_names = set(e for e in events if e != "")
    for i in range(len(events)):
        if events[i] == "":
            events[i] = random_event_name(used_names)

    sample["hints"] = generate_hints(sample["paths"], events, hint_type)
    return sample


def main():
    parser = argparse.ArgumentParser(description="Run script with parameters")
    parser.add_argument("--n", type=int, default=1, help="生成样例数量")
    parser.add_argument("--name", type=str, required=True, help="生成的文件名")
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="样例递归深度，每基于target生成一次formula算一层",
    )
    parser.add_argument("--hint", type=str, help="提示类型", default="direct neg")
    args = parser.parse_args()
    # print arguments
    print(f"Generating {args.n} samples into {args.name}.json with depth {args.depth}")

    trees = []
    for i in range(args.n):
        tree = None
        for _ in range(args.depth):
            tree = generate_tree(tree)
            tree["id"] = i
        trees.append(tree)
    # 递归生成路径树
    for i in range(len(trees)):
        trees[i] = generate_data(trees[i], args.hint)

    with open(f"datasets/{args.name}.json", "w") as f:
        json.dump(trees, f, indent=4, ensure_ascii=False)
    print(f"Generated {args.n} samples and saved to {args.name}.json")


# def main_all_real():
# with open("datas/all_base_samples.json", "r") as f:
#     samples = json.load(f)

# for sample in samples:
#     events = sample["events"]
#     real_events = get_event_by_rel(sample["target"]["rel"])
#     events[0] = real_events["from"]
#     events[1] = real_events["to"]
#     events[2] = random_event_name()
#     events[
#         2
#     ] += "(This is a fictional event without actual time, but the event relationships it provides are real.)"

#     sample["hints"] = generate_negative_hints(sample["formulas"], events)
#     sample["id"] = samples.index(sample)
# with open("datasets/test_reals.json", "r") as f:
#     samples = json.load(f)
# for sample in samples:
#     virtual_event = random_event_name()
#     sample["events"][2] = virtual_event
#     hints = [
#         f"{virtual_event} is a fictional event without actual time, but the event relationships it provides are real."
#     ]
#     hints.extend(generate_negative_hints(sample["formulas"], sample["events"]))
#     sample["hints"] = hints
#     sample["id"] = samples.index(sample)

# with open("datasets/test_reals_virtual.json", "w") as f:
#     json.dump(samples, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    # general sample
    main()
    # # all real base sample
    # main_all_real()
