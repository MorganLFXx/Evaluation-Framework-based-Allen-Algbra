import random
import copy
import json
from utils.relation import random_relation, get_composition, composition_table, full
from utils.db import get_event_by_rel
from generate.generate_hints import generate_hints


def random_event_name(used_names=None):
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
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    ]
    if used_names is not None:
        available = [e for e in events_list if e not in used_names]
        if available:
            name = random.choice(available)
        else:
            name = f"{random.choice(events_list)}{random.choice(events_list)}"
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
            events[i] = random_event_name(used_names) + str(i)

    hints, explanations = generate_hints(sample["paths"], events, hint_type)
    sample["hints"] = hints
    sample["explanation"] = explanations
    return sample


def main(n, name, depth=1, hint="indirect pos"):
    if not name:
        raise ValueError("name is required")
    # print arguments
    print(f"Generating {n} samples into {name}.json with depth {depth}")

    trees = []
    for i in range(n):
        # 递归生成路径树
        tree = None
        for _ in range(depth):
            tree = generate_tree(tree)
            tree["id"] = i
        trees.append(tree)
    for i in range(len(trees)):
        trees[i] = generate_data(trees[i], hint)

    with open(f"datasets/{name}.json", "w") as f:
        json.dump(trees, f, indent=4, ensure_ascii=False)
    print(f"Generated {n} samples and saved to {name}.json")


def main_base():
    # 用于生成所有基本事件
    id = 0
    datas = []
    for pair in composition_table.items():
        key, value = pair
        if value == full:
            continue
        rel1, rel2 = key
        for rel in value:
            events = ["", "", ""]
            target = {"l": 0, "r": 1, "rel": rel}
            excluded = [r for r in value if r != rel]
            new_path = {
                "target": rel,
                "path": [rel1, rel2],
                "excluded": excluded,
                "parent": -1,
                "left": -1,
                "right": -1,
                "base_event": [0, 1],
                "new_event": 2,
            }
            sample = {
                "id": id,
                "target": target,
                "events": events,
                "paths": [new_path],
            }
            id += 1
            data = generate_data(sample, "indirect pos")
            datas.append(data)
    print(f"Generated {len(datas)} base samples.")
    with open("datasets/test_bases.json", "w") as f:
        json.dump(datas, f, indent=4, ensure_ascii=False)


def main_link_length():
    # 用于检查不同链路长度造成的影响，基于同一个target生成不同长度的路径树
    # 截取10个bases
    with open("datasets/answers/test_bases_4b2_with_answers.json", "r") as f:
        samples = json.load(f)
    right_bases = []
    error_bases = []
    for sample in samples:
        if not "right" in sample:
            continue
        check = 1 if sample["right"] == True else 0
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
    right_bases = random.sample(right_bases, 2)
    error_bases = random.sample(error_bases, 2)

    # 基于每个right/error base生成不同链路长度的样例,每个不同样例的不同链路长度生成20个样例
    # 每个base作为开头
    new_data = []
    depth_list = range(3, 31, 3)
    id = 0
    for base in right_bases:
        first_base = generate_data(base, hint_type="indirect pos")
        first_base["id"] = id
        first_base["chose_right"] = True
        first_base["is_base"] = True
        id += 1
        new_data.append(first_base)
        for depth in depth_list:
            for _ in range(10):
                tree = copy.deepcopy(base)
                while len(tree["paths"]) < depth:
                    tree = generate_tree(tree)
                tree = generate_data(tree, hint_type="indirect pos")
                tree["id"] = id
                tree["chose_right"] = True
                tree["is_base"] = False
                id += 1
                new_data.append(tree)
    for base in error_bases:
        first_base = generate_data(base, hint_type="indirect pos")
        first_base["id"] = id
        first_base["chose_right"] = False
        first_base["is_base"] = True
        id += 1
        new_data.append(first_base)
        for depth in depth_list:
            for _ in range(10):
                tree = copy.deepcopy(base)
                while len(tree["paths"]) < depth:
                    tree = generate_tree(tree)
                tree = generate_data(tree, hint_type="indirect pos")
                tree["id"] = id
                tree["chose_right"] = False
                tree["is_base"] = False
                id += 1
                new_data.append(tree)

    with open("datasets/test_len_dense.json", "w") as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)


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
    # main(n=1, name="sample", depth=1, hint="direct neg")
    # all real base sample
    # main_all_real()
    # all base samples
    # main_base()
    # link length samples
    main_link_length()
