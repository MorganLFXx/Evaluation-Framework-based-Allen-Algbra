import random
import argparse
import json
from utils.relation import random_relation, get_composition
from generate_hints import generate_negative_hints


def random_event_name():
    # year events
    events_list = [
        "Graduate study",
        "Field research",
        "Software development",
        "Policy implementation",
        "Clinical training",
        "Infrastructure build",
        "Language immersion",
        "Startup incubation",
        "Forest restoration",
        "Curriculum redesign",
        "Robotics prototyping",
        "Urban planning",
        "Data collection",
        "Apprenticeship",
        "Grant funding period",
    ]
    return random.choice(events_list)


def generate_formulas(target, events, parent):
    """generate formulas based on target"""
    l_no = target["l"]
    r_no = target["r"]
    # add a new event
    new_event_no = len(events)
    events.append("")
    formulas = []

    # choose composition
    composition = get_composition(target["rel"])
    key, value = composition
    rel1, rel2 = key
    # 正确路径
    formulas.append(
        {"l": l_no, "r": new_event_no, "rel": rel1, "type": "", "hints": []}
    )
    formulas.append(
        {"l": new_event_no, "r": r_no, "rel": rel2, "type": "", "hints": []}
    )
    path = rel1 + rel2
    # 排除多余路径
    excluded = ""
    for char in value:
        if char == target["rel"]:
            continue
        formulas.append({"l": l_no, "r": r_no, "rel": char, "type": "not", "hints": []})
        excluded += char

    return {
        "formulas": formulas,
        "path": {
            "target": target["rel"],
            "path": path,
            "excluded": excluded,
            "parent": parent,
            "base_event": [l_no, r_no],
            "new_event": new_event_no,
        },
    }


def generate_sample(sample):
    events = []
    target = {}
    formulas = []
    hints = []
    paths = []
    # 判断是否base sample，生成target
    if sample is None:
        l_no = 0
        r_no = 1
        for _ in range(2):
            events.append("")
        target["l"] = l_no
        target["r"] = r_no
        target["rel"] = random_relation()
        parent = -1
        new_target = target.copy()
    else:
        target = sample["target"].copy()
        events = sample["events"].copy()
        paths = sample["paths"].copy()

        # 抽取一个formula用于生成更多formula
        # TODO not的情况呢
        chosen = []
        for i, formula in enumerate(sample["formulas"]):
            if formula["type"] != "not":
                chosen.append(i)
        parent = random.choice(chosen)
        parent_formula = sample["formulas"][parent]
        excluded_hints = parent_formula["hints"]
        # 排除被抽取的formula
        for i, formula in enumerate(sample["formulas"]):
            if i != parent:
                formulas.append(formula.copy())
        # 排除被抽取的formula对应的hints
        for i, hint in enumerate(sample["hints"]):
            if i not in excluded_hints:
                hints.append(hint)
        new_target = parent_formula

    # 基于抽取的formula生成更多formula
    res = generate_formulas(new_target, events, parent)
    formulas.extend(res["formulas"])
    # record path info
    path_info = res["path"]
    path_info["id"] = len(paths)
    paths.append(path_info)

    # generate hints TODO
    hints = generate_negative_hints(formulas, events)

    return {
        "target": target,
        "events": events,
        "formulas": formulas,
        "hints": hints,
        "paths": paths,
    }


"""
1. 判断是否base
2. 生成target (new/complex)
3. 基于target生成formulas(这步应该抽象出来)
3.5. 补充到原来的formulas
4. 生成hints (补充到原来的hints)
"""


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
    args = parser.parse_args()

    # print arguments
    print(f"Generating {args.n} samples into {args.name}.json with depth {args.depth}")

    samples = []
    for i in range(args.n):
        sample = None
        for _ in range(args.depth):
            sample = generate_sample(sample)
            sample["id"] = i
        samples.append(sample)
    # output to json file
    with open(f"datasets/{args.name}.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    print(f"Generated {args.n} samples and saved to {args.name}.json")


if __name__ == "__main__":
    main()
