import random
import argparse
import json
from utils.relation import random_relation, get_composition
from utils.db import get_event_by_rel
from generate_hints import generate_negative_hints, generate_positive_hints


def random_event_name():
    # year events
    events_list = [
        "regional war",
        "siege",
        "revolution",
        "engineering project",
        "invention process",
        "construction",
        "book writing",
        "tour to study",
        "long-term travel",
        ""
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
    events = sample["events"] if sample else []
    target = sample["target"] if sample else {}
    formulas = []
    paths = sample["paths"] if sample else []
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
        # 抽取一个formula用于生成更多formula
        # TODO not的情况呢
        chosen = []
        for i, formula in enumerate(sample["formulas"]):
            if formula["type"] != "not":
                chosen.append(i)
        parent = random.choice(chosen)
        new_target = sample["formulas"][parent].copy()

    # 基于抽取的formula生成更多formula
    res = generate_formulas(new_target, events, parent)
    if sample is None:
        formulas.extend(res["formulas"])
    else:
        for i in range(0, parent):
            formulas.append(sample["formulas"][i].copy())
        formulas.extend(res["formulas"])
        for i in range(parent + 1, len(sample["formulas"])):
            formulas.append(sample["formulas"][i].copy())
    # record path info
    path_info = res["path"]
    path_info["id"] = len(paths)
    paths.append(path_info)

    # for i in range(len(events)):
    #     if events[i] == "":
    #         events[i] = random_event_name()
    # generate hints TODO
    # hints = generate_negative_hints(formulas, events)
    # hints = generate_positive_hints(formulas, paths, events)

    return {
        "target": target,
        "events": events,
        "formulas": formulas,
        "paths": paths,
    }


"""
1. 判断是否base
2. 生成target (new/complex)
3. 基于target生成formulas(这步应该抽象出来)
3.5. 补充到原来的formulas
4. 生成hints (补充到原来的hints)
"""


def generate_data(sample):
    events = sample["events"]
    for i in range(len(events)):
        if events[i] == "":
            events[i] = random_event_name()

    sample["hints"] = generate_negative_hints(sample["formulas"], events)
    # sample["hints"] = generate_positive_hints(
    #     sample["formulas"], sample["paths"], events
    # )

    return sample


def generate_all_base_samples():
    from utils.relation import full, composition_table

    samples = []
    rels = [rel for rel in full]
    for i in range(len(rels)):
        for j in range(len(rels)):
            compose = composition_table.get((rels[i], rels[j]))
            if compose == full:
                continue
            for c in compose:
                target = {"l": 0, "r": 1, "rel": c}
                formulas = [
                    {"l": 0, "r": 2, "rel": rels[i], "type": "", "hints": []},
                    {"l": 2, "r": 1, "rel": rels[j], "type": "", "hints": []},
                ]
                for k in compose:
                    if k != c:
                        formulas.append(
                            {"l": 0, "r": 1, "rel": k, "type": "not", "hints": []}
                        )
                sample = {
                    "target": target,
                    "events": ["", "", ""],
                    "formulas": formulas,
                }
                samples.append(sample)

    with open(f"datasets/all_base_samples.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    print(f"Generated {len(samples)} base samples and saved to all_base_samples.json")


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
    # 将生成hints的部分在递归生成公式后进行
    for i in range(len(samples)):
        samples[i] = generate_data(samples[i])
    # output to json file
    with open(f"datasets/{args.name}.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    print(f"Generated {args.n} samples and saved to {args.name}.json")


def main_all_base():
    with open("datas/all_base_samples_levels.json", "r") as f:
        samples = json.load(f)

    for sample in samples:
        events = sample["events"]
        for i in range(len(events)):
            if events[i] == "":
                events[i] = random_event_name()

        sample["hints"] = generate_negative_hints(sample["formulas"], events)
        sample["id"] = samples.index(sample)

    with open("datasets/test_base.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)


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
    # # general sample
    # main()
    # # all base sample
    main_all_base()
    # # all real base sample
    # main_all_real()
