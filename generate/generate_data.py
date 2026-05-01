import random
import copy
import json
from utils.relation import random_relation, get_composition, composition_table, full
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
            while name in used_names:
                name = f"{random.choice(events_list)}{random.choice(events_list)}"
        used_names.add(name)
        return name
    return random.choice(events_list)


def generate_path(target, events, parent):
    """generate paths based on target"""
    l_no = target["l"]
    r_no = target["r"]
    new_event_no = len(events)
    events.append("")

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
        parent = random.randint(0, len(paths) - 1)
        while paths[parent]["left"] != -1 and paths[parent]["right"] != -1:
            parent = random.randint(0, len(paths) - 1)
        cur_path = paths[parent]

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
    print(f"Generating {n} samples into {name}.json with depth {depth}")

    trees = []
    for i in range(n):
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


if __name__ == "__main__":
    # general sample
    main(n=1, name="sample", depth=1, hint="direct neg")
