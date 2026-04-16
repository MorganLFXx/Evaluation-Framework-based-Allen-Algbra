import random

from generate.generate_response import detail_post_question_conflict, allen_helper

example = {
    "target": {"l": 0, "r": 1, "rel": "d", "conflict_no": 22},
    "events": [
        "M0",
        "B1",
        "I2",
        "O3",
        "S4",
        "L5",
        "X6",
        "Y7",
        "C8",
        "H9",
        "Q10",
        "V11",
    ],
    "paths": [
        {
            "target": "d",
            "path": ["e", "d"],
            "excluded": [],
            "parent": -1,
            "left": 1,
            "right": 2,
            "base_event": [0, 1],
            "new_event": 2,
        },
        {
            "target": "e",
            "path": ["f", "F"],
            "excluded": ["F", "f"],
            "parent": 0,
            "left": 7,
            "right": 3,
            "base_event": [0, 2],
            "new_event": 3,
        },
        {
            "target": "d",
            "path": ["m", "d"],
            "excluded": ["o", "s"],
            "parent": 0,
            "left": -1,
            "right": -1,
            "base_event": [2, 1],
            "new_event": 4,
        },
        {
            "target": "F",
            "path": ["D", "p"],
            "excluded": ["p", "m", "o", "D"],
            "parent": 1,
            "left": 4,
            "right": 5,
            "base_event": [3, 2],
            "new_event": 5,
        },
        {
            "target": "D",
            "path": ["D", "f"],
            "excluded": ["S", "O"],
            "parent": 3,
            "left": 8,
            "right": 6,
            "base_event": [3, 5],
            "new_event": 6,
        },
        {
            "target": "p",
            "path": ["o", "D"],
            "excluded": ["m", "o", "F", "D"],
            "parent": 3,
            "left": -1,
            "right": -1,
            "base_event": [5, 2],
            "new_event": 7,
        },
        {
            "target": "f",
            "path": ["f", "e"],
            "excluded": [],
            "parent": 4,
            "left": 9,
            "right": -1,
            "base_event": [6, 5],
            "new_event": 8,
        },
        {
            "target": "f",
            "path": ["P", "s"],
            "excluded": ["d", "O", "M", "P"],
            "parent": 1,
            "left": -1,
            "right": -1,
            "base_event": [0, 3],
            "new_event": 9,
        },
        {
            "target": "D",
            "path": ["D", "f"],
            "excluded": ["S", "O"],
            "parent": 4,
            "left": -1,
            "right": -1,
            "base_event": [3, 6],
            "new_event": 10,
        },
        {
            "target": "f",
            "path": ["D", "d"],
            "excluded": ["o", "F", "D", "s", "e", "S", "d", "O"],
            "parent": 6,
            "left": -1,
            "right": -1,
            "base_event": [6, 8],
            "new_event": 11,
        },
    ],
    "id": 1705,
    "hints": [
        "'M0' triggers later thn 'B1'(Only related to the start time. Not the whole event)",
        "'M0' concludes prior to the conclusion of 'B1'.",
        "You can be certain that 'M0' lasts shorter than 'B1'.",
        "'M0' and 'I2' have the same duration and end simultaneously",
        "There is no time interval between the termination of 'I2' and the initiation of 'S4'",
        "The duration of 'S4' is part of the duration of 'B1' and their start time and end time are different.",
        "'I2' starts after 'B1' starts.",
        "'O3' ends when 'I2' ends.",
        "'O3' starts before 'L5' starts.",
        "'L5' starts before 'Y7' starts and ends after 'Y7' starts but before 'Y7' ends.",
        "During 'Y7', 'I2' started and ended and their start time and end time are different.",
        "There is no overlap between 'L5' and 'I2'",
        "At no time do events 'L5' and 'I2' coincide",
        "'C8' and 'L5' overlap completely in time.",
        "'X6' starts after 'L5' starts.",
        "'X6' ends when 'L5' ends.",
        "There was a gap between the finish of 'H9' and the start of 'M0'.",
        "'H9' starts at the same time as 'O3' but ends earlier.",
        "'M0' and 'O3' share the same ending point.",
        "During 'O3', 'Q10' started and ended and their start time and end time are different.",
        "'Q10' starts after 'X6' starts and ends exactly when 'X6' ends.",
        "'O3' and 'X6' share the same ending point.",
        "During 'X6', 'V11' started and ended and their start time and end time are different.",
        "During 'C8', 'V11' started and ended and their start time and end time are different.",
        "'X6' starts after 'C8' starts.",
        "'X6' ends when 'C8' ends.",
        "'M0' starts after 'B1' starts and ends before 'B1' ends.",
    ],
    "answer_single": [7],
    "right": False,
}


def build_question(sample, shuffle=False):
    # build control/treatment question from example
    question = (
        "There is a conflict hint in the hints. "
        "Please help me find out the conflict hint."
        f"Note: All hints directly describe the relation between 2 events is absolutely correct."
        f"'Directly describe' means you can directly determine the allen relation(Or complete the sorting of four time points including the start and end times of two events) between 2 event based on this hint without any other hints. "
    )
    hints = list(sample["hints"])
    if shuffle:
        random.shuffle(hints)
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
    question += detail_post_question_conflict + "\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    return messages


def locate_conflict(sample):
    """
    input: conflict_no(gold or response)
    output: events pair(l,r,rel) that are in conflict
    """
    conflict_no = sample["target"]["conflict_no"]
    conflict_hint = sample["hints"][conflict_no - 1]
    # match 2 events in conflict_hint, they were warpped by single quote in the hint
    events_in_conflict = set()
    start = 0
    while True:
        start = conflict_hint.find("'", start)
        if start == -1:
            break
        end = conflict_hint.find("'", start + 1)
        if end == -1:
            break
        event = conflict_hint[start + 1 : end]
        events_in_conflict.add(event)
        start = end + 1
    events_in_conflict = list(events_in_conflict)
    events_no = []
    for event in events_in_conflict:
        for i, e in enumerate(sample["events"]):
            if e == event:
                events_no.append(i)
                break
    events_no = sorted(events_no)

    # match conflict source
    pairs = []
    for path in sample["paths"]:
        path_base_events = sorted(path["base_event"])
        if path_base_events == events_no:
            events = sample["events"]
            pairs.append(
                (
                    events[path["base_event"][0]],
                    events[path["base_event"][1]],
                    path["target"],
                )
            )  # conflict
            pairs.append(
                (
                    events[path["base_event"][0]],
                    events[path["new_event"]],
                    path["path"][0],
                )
            )  # cause conflict
            pairs.append(
                (
                    events[path["new_event"]],
                    events[path["base_event"][1]],
                    path["path"][1],
                )
            )  # cause conflict
            break
    return pairs


def get_whole_rels(sample, conflict_pairs):
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

    # remove conflict pairs from rels
    conflict_set = set((l, r) for l, r, _ in conflict_pairs)
    rels = [rel for rel in rels if (rel[0], rel[1]) not in conflict_set]
    return rels


def get_key_rels(sample):
    # 获取所有关键节点的关系组
    # 关键节点：左子树或右子树至少有一个不是叶子节点的节点
    # 记得除去根节点
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

    key_rel_groups = []
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

        return [
            (events[l_base], events[r_base], target),
            (events[l_base], events[new_event], path_rels[0]),
            (events[new_event], events[r_base], path_rels[1]),
        ]

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
            group = _append_group(node)
            if group:
                key_rel_groups.append((node_idx, group))

    for root in roots:
        dfs(root)

    # remove root node groups after collection
    key_rel_groups = [
        group for node_idx, group in key_rel_groups if node_idx not in roots
    ]
    return key_rel_groups


def main():
    conflict_pairs = locate_conflict(example)
    print(get_whole_rels(example, conflict_pairs))


if __name__ == "__main__":
    main()
