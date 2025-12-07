import random
import argparse
import json
from utils.relation import random_relation, get_composition, get_hint


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


def generate_formulas(target, events):
    """generate formulas based on target"""
    l_no = target["l"]
    r_no = target["r"]
    # add a new event
    new_event_no = len(events)
    new_event = random_event_name()
    events.append(new_event)

    formulas = []
    # choose composition
    composition = get_composition(target["rel"])
    key, value = composition
    rel1, rel2 = key
    # 正确路径
    formulas.append({"l": l_no, "r": new_event_no, "rel": rel1, "hints": []})
    formulas.append({"l": new_event_no, "r": r_no, "rel": rel2, "hints": []})
    # 排除多余路径
    for char in value:
        if char == target["rel"]:
            continue
        formulas.append({"l": l_no, "r": r_no, "rel": char, "type": "not", "hints": []})

    return formulas


def generate_sample(sample):
    events = []
    target = {}
    formulas = []
    hints = []
    # 判断是否base sample，生成target
    if sample is None:
        for _ in range(2):
            events.append(random_event_name())
        l_no = 0
        r_no = 1
        target["l"] = l_no
        target["r"] = r_no
        target["rel"] = random_relation()
        formulas = generate_formulas(target, events)
    else:
        target = sample["target"].copy()
        events = sample["events"].copy()
        # 抽取一个formula用于生成更多formula
        excluded_formula_no = random.randint(0, len(sample["formulas"]) - 1)
        # TODO 后面再接着改，用一个not equal+一组composition就可以转换not type了
        while sample["formulas"][excluded_formula_no]["type"] == "not":
            excluded_formula_no = random.randint(0, len(sample["formulas"]) - 1)
        excluded_formula = sample["formulas"][excluded_formula_no]
        excluded_hints = excluded_formula["hints"]
        # 排除被抽取的formula
        original_formulas = []
        for i, formula in enumerate(sample["formulas"]):
            if i != excluded_formula_no:
                original_formulas.append(formula.copy())
        # 排除被抽取的formula对应的hints
        original_hints = []
        for i, hint in enumerate(sample["hints"]):
            if i not in excluded_hints:
                original_hints.append(hint)
        hints = original_hints
        formulas = generate_formulas(excluded_formula, events)
        formulas.extend(original_formulas)

    # generate hints
    for i, formula in enumerate(formulas):
        l_no = formula["l"]
        r_no = formula["r"]
        rel = formula["rel"]
        generated_hints = get_hint(
            rel, l_no, r_no, events, formula.get("type") == "not"
        )
        # add hint indices to formula
        hint_indices = []
        for hint in generated_hints:
            hints.append(hint)
            hint_indices.append(len(hints) - 1)
        formulas[i]["hints"] = hint_indices

    return {
        "target": target,
        "events": events,
        "formulas": formulas,
        "hints": hints,
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
    parser.add_argument("--n", type=int, help="生成样例数量")
    parser.add_argument("--name", type=str, help="生成的文件名")
    parser.add_argument("--depth", type=str, help="样例递归深度")
    args = parser.parse_args()

    # print arguments
    print(f"Generating {args.n} samples into {args.name}.json with depth {args.depth}")

    samples = []
    for i in range(args.n):
        sample = None
        for _ in range(int(args.depth) + 1):
            sample = generate_sample(sample)
        samples.append(sample)
    # output to json file
    with open(f"datasets/{args.name}.json", "w") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    print(f"Generated {args.n} samples and saved to {args.name}.json")


if __name__ == "__main__":
    main()
