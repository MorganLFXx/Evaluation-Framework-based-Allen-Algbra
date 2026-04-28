import random

from generate.generate_response import detail_post_question, allen_helper

example = {
    "target": {"l": 0, "r": 1, "rel": "s"},
    "events": [
        "P0",
        "J1",
        "Y2",
        "T3",
        "W4",
        "V5",
        "S6",
        "Z7",
        "L8",
        "C9",
        "N10",
        "G11",
    ],
    "paths": [
        {
            "target": "s",
            "path": ["f", "o"],
            "excluded": ["o", "d"],
            "parent": -1,
            "left": 1,
            "right": 2,
            "base_event": [0, 1],
            "new_event": 2,
        },
        {
            "target": "f",
            "path": ["O", "o"],
            "excluded": ["o", "F", "D", "s", "e", "S", "d", "O"],
            "parent": 0,
            "left": 3,
            "right": -1,
            "base_event": [0, 2],
            "new_event": 3,
        },
        {
            "target": "o",
            "path": ["o", "F"],
            "excluded": ["p", "m"],
            "parent": 0,
            "left": 7,
            "right": 5,
            "base_event": [2, 1],
            "new_event": 4,
        },
        {
            "target": "O",
            "path": ["S", "O"],
            "excluded": [],
            "parent": 1,
            "left": 6,
            "right": 4,
            "base_event": [0, 3],
            "new_event": 5,
        },
        {
            "target": "O",
            "path": ["D", "O"],
            "excluded": ["D", "S"],
            "parent": 3,
            "left": -1,
            "right": -1,
            "base_event": [5, 3],
            "new_event": 6,
        },
        {
            "target": "F",
            "path": ["D", "d"],
            "excluded": ["o", "D", "s", "e", "S", "d", "f", "O"],
            "parent": 2,
            "left": 9,
            "right": -1,
            "base_event": [4, 1],
            "new_event": 7,
        },
        {
            "target": "S",
            "path": ["D", "O"],
            "excluded": ["D", "O"],
            "parent": 3,
            "left": 8,
            "right": -1,
            "base_event": [0, 5],
            "new_event": 8,
        },
        {
            "target": "o",
            "path": ["f", "o"],
            "excluded": ["s", "d"],
            "parent": 2,
            "left": -1,
            "right": -1,
            "base_event": [2, 4],
            "new_event": 9,
        },
        {
            "target": "D",
            "path": ["D", "F"],
            "excluded": [],
            "parent": 6,
            "left": -1,
            "right": -1,
            "base_event": [0, 8],
            "new_event": 10,
        },
        {
            "target": "D",
            "path": ["o", "S"],
            "excluded": ["o", "F"],
            "parent": 5,
            "left": -1,
            "right": -1,
            "base_event": [4, 7],
            "new_event": 11,
        },
    ],
    "id": 0,
    "hints": [
        "'P0' and 'J1' share the same starting point.",
        "'T3' and 'Y2' overlap in time. 'T3' starts first. And we can't tell which one lasts longer.",
        "'P0' begins later than 'Y2'(Only related to the start time. Not the whole event).",
        "'P0' concludes at the same time as 'Y2'.",
        "There is a temporal overlap between events 'Y2' and 'J1'",
        "'P0' starts after 'T3' starts.",
        "There is a temporal overlap between events 'P0' and 'T3'",
        "The lengths of events 'P0' and 'T3' cannot be compared",
        "The duration of 'S6' is part of the duration of 'V5' and their start time and end time are different.",
        "'S6' and 'T3' overlap in time. 'T3' starts first. And we can't tell which one lasts longer.",
        "'V5' starts after 'T3' starts.",
        "The duration of 'Z7' is part of the duration of 'J1' and their start time and end time are different.",
        "'W4' triggers earlier than 'J1'(Only related to the start time. Not the whole event)",
        "'W4' ends when 'J1' ends.",
        "'L8' and 'V5' overlap in time. 'V5' starts first. And we can't tell which one lasts longer.",
        "'P0' starts when 'V5' starts.",
        "'Y2' starts after 'C9' starts and ends exactly when 'C9' ends.",
        "'C9' starts before 'W4' starts and ends after 'W4' starts but before 'W4' ends.",
        "'Y2' triggers earlier than 'W4'(Only related to the start time. Not the whole event)",
        "The duration of 'N10' is part of the duration of 'P0' and their start time and end time are different.",
        "'N10' finishes at the same time as 'L8' and began earlier.",
        "'P0' starts before 'L8' starts.",
        "'P0' finishes later than 'L8'.",
        "You can be certain that 'P0' lasts longer than 'L8'.",
        "'W4' and 'G11' overlap in time. 'W4' starts first. And we can't tell which one lasts longer.",
        "'G11' starts exactly when 'Z7' starts and ends after 'Z7' ends.",
        "'W4' concludes after the conclusion of 'Z7'.",
    ],
}


def build_question(sample, shuffle=False):
    # build control/treatment question from example
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information."
        "During this process, guess the implicit relationships among events along the necessary path as accurately as possible."
    )
    hints = list(sample["hints"])
    if shuffle:
        random.shuffle(hints)
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    question += detail_post_question + "\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def get_whole_rels(sample):
    """
    将 paths 二叉树中的关系全部展开为 (left_event, right_event, rel) 三元组。

    对于每个 path 节点会提取三条关系：
    1) base_event[0] --target--> base_event[1]
    2) base_event[0] --path[0]--> new_event
    3) new_event --path[1]--> base_event[1]

    返回值：按树的 DFS 顺序输出，去重后的关系三元组列表。
    """
    events = sample.get("events", [])
    paths = sample.get("paths", [])
    if not events or not paths:
        return []

    rels = []
    seen = set()

    def _append_rel(l_idx, r_idx, rel):
        if not (0 <= l_idx < len(events) and 0 <= r_idx < len(events)):
            return
        triple = (events[l_idx], events[r_idx], rel)
        if triple in seen:
            return
        seen.add(triple)
        rels.append(triple)

    visited = set()

    def dfs(node_idx):
        if node_idx in visited or not (0 <= node_idx < len(paths)):
            return
        visited.add(node_idx)

        node = paths[node_idx]
        left_idx = node.get("left", -1)
        right_idx = node.get("right", -1)

        if left_idx != -1:
            dfs(left_idx)
        if right_idx != -1:
            dfs(right_idx)

        base = node.get("base_event", [])
        path_rels = node.get("path", [])
        new_event = node.get("new_event", -1)
        target = node.get("target")

        if len(base) != 2 or len(path_rels) != 2 or target is None:
            return

        l_base, r_base = int(base[0]), int(base[1])
        new_event = int(new_event)

        # 目标关系
        _append_rel(l_base, r_base, target)
        # 组成关系
        _append_rel(l_base, new_event, path_rels[0])
        _append_rel(new_event, r_base, path_rels[1])

    roots = [i for i, p in enumerate(paths) if p.get("parent", -1) == -1]
    if not roots:
        roots = [0]

    for root in roots:
        dfs(root)

    return rels


def get_key_rels(sample):
    # 获取所有关键节点的关系组
    # 关键节点：左子树或右子树至少有一个不是叶子节点的节点
    # return: list of (left_event, right_event, rel) that are in key nodes
    events = sample.get("events", [])
    paths = sample.get("paths", [])
    if not events or not paths:
        return []

    def _is_leaf(node_idx):
        if not (0 <= node_idx < len(paths)):
            return True
        node = paths[node_idx]
        return node.get("left", -1) == -1 and node.get("right", -1) == -1

    def _is_key_node(node_idx):
        if not (0 <= node_idx < len(paths)):
            return False
        node = paths[node_idx]
        left_idx = node.get("left", -1)
        right_idx = node.get("right", -1)
        return (left_idx != -1 and not _is_leaf(left_idx)) or (
            right_idx != -1 and not _is_leaf(right_idx)
        )

    roots = {i for i, p in enumerate(paths) if p.get("parent", -1) == -1}
    if not roots:
        roots = {0}

    key_rels = []
    seen = set()
    visited = set()

    def _append_group(node):
        base = node.get("base_event", [])
        path_rels = node.get("path", [])
        new_event = node.get("new_event", -1)
        target = node.get("target")

        if len(base) != 2 or len(path_rels) != 2 or target is None:
            return

        l_base, r_base = int(base[0]), int(base[1])
        new_event = int(new_event)
        if not (
            0 <= l_base < len(events)
            and 0 <= r_base < len(events)
            and 0 <= new_event < len(events)
        ):
            return

        triples = [
            (events[l_base], events[r_base], target),
            (events[l_base], events[new_event], path_rels[0]),
            (events[new_event], events[r_base], path_rels[1]),
        ]

        for tri in triples:
            if tri in seen:
                continue
            seen.add(tri)
            key_rels.append(tri)

    def dfs(node_idx):
        if node_idx in visited or not (0 <= node_idx < len(paths)):
            return
        visited.add(node_idx)

        node = paths[node_idx]
        left_idx = node.get("left", -1)
        right_idx = node.get("right", -1)

        if left_idx != -1:
            dfs(left_idx)
        if right_idx != -1:
            dfs(right_idx)

        if _is_key_node(node_idx):
            _append_group(node)

    for root in roots:
        dfs(root)

    return key_rels


def main():
    print(get_key_rels(example))


if __name__ == "__main__":
    main()
