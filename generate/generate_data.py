import random
import copy
import argparse
import json
from utils.relation import random_relation, get_composition
from utils.db import get_event_by_rel
from generate.generate_hints import generate_hints


def random_event_name(used_names=None):
    # year events
    # events_list = [
    #     "regional war",
    #     "siege",
    #     "government revolution",
    #     "engineering project",
    #     "invention process",
    #     "construction",
    #     "book writing",
    #     "tour to study",
    #     "long-term travel",
    #     "long-distance migration",
    # ]
    events_list = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
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


def build_base_tree(target_rel):
    events = ["", ""]
    target = {"l": 0, "r": 1, "rel": target_rel}
    paths = []
    new_path = generate_path(target, events, parent=-1)
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

    hints, explanations = generate_hints(sample["paths"], events, hint_type)
    sample["hints"] = hints
    sample["explanation"] = explanations
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
        # 递归生成路径树
        tree = None
        for _ in range(args.depth):
            tree = generate_tree(tree)
            tree["id"] = i
        trees.append(tree)
    for i in range(len(trees)):
        trees[i] = generate_data(trees[i], args.hint)

    with open(f"datasets/{args.name}.json", "w") as f:
        json.dump(trees, f, indent=4, ensure_ascii=False)
    print(f"Generated {args.n} samples and saved to {args.name}.json")


def main_base():
    # 用于生成所有基本事件
    with open("datas/all_base_samples.json", "r") as f:
        samples = json.load(f)
    for sample in samples:
        events = sample["events"]
        used_names = set(e for e in events if e != "")
        for i in range(len(events)):
            if events[i] == "":
                events[i] = random_event_name(used_names)
        sample = generate_data(sample, hint_type="direct neg")
    with open("datasets/test_base_neg.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)


def main_link_length():
    # 用于检查不同链路长度造成的影响，基于同一个target生成不同长度的路径树
    depth_list = [3, 8, 15]
    with open("datasets/answers/test_100_d5_fix_with_answers.json", "r") as f:
        samples = json.load(f)
    right_bases = []
    error_bases = []
    for sample in samples:
        check = (
            1 if sample["answer_single"][0].strip() == sample["target"]["rel"] else 0
        )
        target = {
            "target": sample["target"],
            "events": sample["events"][:3],
            "paths": sample["paths"][:1],
        }
        target["paths"][0]["left"] = -1
        target["paths"][0]["right"] = -1
        if check == 1:
            right_bases.append(target)
        else:
            error_bases.append(target)
    # 截取10个right bases
    right_bases = right_bases[:10]
    error_bases = error_bases[:10]
    # 基于每个right base生成不同链路长度的样例,每个不同样例的不同链路长度生成5个样例
    new_right = []
    for i in range(10):
        new_sample = generate_data(right_bases[i], hint_type="indirect pos")
        new_right.append(new_sample)
        new_right[i]["id"] = i
        new_right[i]["right"] = True
    for i in range(10, 20):
        new_sample = generate_data(error_bases[i - 10], hint_type="indirect pos")
        new_right.append(new_sample)
        new_right[i]["id"] = i
        new_right[i]["right"] = False
    id = 20

    for base in right_bases:
        for depth in depth_list:
            for _ in range(4):
                tree = copy.deepcopy(base)
                while len(tree["paths"]) < depth:
                    tree = generate_tree(tree)
                tree = generate_data(tree, hint_type="indirect pos")
                tree["id"] = id
                tree["right"] = True
                id += 1
                new_right.append(tree)
    for base in error_bases:
        for depth in depth_list:
            for _ in range(4):
                tree = copy.deepcopy(base)
                while len(tree["paths"]) < depth:
                    tree = generate_tree(tree)
                tree = generate_data(tree, hint_type="indirect pos")
                tree["id"] = id
                tree["right"] = False
                id += 1
                new_right.append(tree)

    with open("datasets/test_link_len.json", "w") as f:
        json.dump(new_right, f, indent=4, ensure_ascii=False)


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
    # all real base sample
    # main_all_real()
    # all base samples
    # main_base()
    # link length samples
    # main_link_length()
