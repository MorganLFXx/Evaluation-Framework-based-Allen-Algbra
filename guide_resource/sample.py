# sample example
base_sample = {
    "target": {"l": 0, "r": 1, "rel": "s"},
    "events": ["D", "I", "M"],
    "id": 11,
    "level": 2,
    "paths": [
        {
            "target": "s",  # target relation
            "path": ["p", "d"],  # composition path
            "excluded": ["p", "m", "o", "d"],  # relations to be excluded
            "parent": -1,
            "left": -1,  # no left if -1
            "right": -1,  # no right if -1
            "base_event": [0, 1],  # base events for target relation
            "new_event": 2,  # new event introduced in this path
        }
    ],
    "hints": [
        "Some time after 'D' ended, 'M' occurred.",
        "'M' starts after 'I' starts and ends before 'I' ends.The duration of 'M' is part of the duration of 'I'.",
        "'D' and 'I' share the same starting point.",
    ],
    "explanation": [
        "D precedes M",
        "M during I",
        "D and I start together",
    ],
    "answer_single": ["s"],
}
# base_sample = {
#     "target": {"l": 0, "r": 1, "rel": "P"},
#     "events": ["Meeting", "Conference", "Workshop"],
#     "hints": [
#         "event 0 takes place from 2022.9.12 to 2022.12.5.",
#         "event 2 occurs from 2022.8.20 to 2022.12.5.",
#         "event 2 was overlapped by event 1.",
#         "There is no overlap between event 0 and event 1.",
#     ],
#     "paths": [
#         {
#             "target": "P",  # target relation
#             "path": ["f", "O"],  # composition path
#             "excluded": ["O", "M"],  # relations to be excluded
#             "parent": -1,  # parent path index, -1 if root
#             "left": 1,  # paths[1] is left child
#             "right": -1,  # no right if -1
#             "base_event": [0, 1],  # base events for target relation
#             "new_event": 2,  # new event introduced in this path
#         },
#     ],
# }
