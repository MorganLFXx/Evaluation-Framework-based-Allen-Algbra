base_sample = {
    "target": {"l": 0, "r": 1, "rel": "P"},
    "events": ["Meeting", "Conference", "Workshop"],
    "hints": [
        "event 0 takes place from 2022.9.12 to 2022.12.5.",
        "event 2 occurs from 2022.8.20 to 2022.12.5.",
        "event 2 was overlapped by event 1.",
        "There is no overlap between event 0 and event 1.",
    ],
    "paths": [
        {
            "target": "P",  # target relation
            "path": ["f", "O"],  # composition path
            "excluded": ["O", "M"],  # relations to be excluded
            "parent": -1,  # parent path index, -1 if root
            "left": 1,  # paths[1] is left child
            "right": -1,  # no right if -1
            "base_event": [0, 1],  # base events for target relation
            "new_event": 2,  # new event introduced in this path
        },
        {
            "target": "f",
            "path": "fe",
            "parent": 0,
            "base_event": [0, 2],
            "new_event": 3,
            "excluded": "",
        },
    ],
}
