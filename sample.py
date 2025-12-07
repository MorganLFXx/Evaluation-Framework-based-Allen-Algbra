def generate_sample():
    base_sample = {
        "target": {"l": 0, "r": 1, "rel": "P"},
        "events": ["Meeting", "Conference", "Workshop"],
        "formulas": [
            {"l": 0, "r": 2, "rel": "f", "hints": [0, 1]},
            {"l": 2, "r": 1, "rel": "O", "hints": [2]},
            {"l": 0, "r": 1, "rel": "O", "type": "not", "hints": [4]},
            {"l": 0, "r": 1, "rel": "M", "type": "not", "hints": [4]},
        ],
        "hints": [
            "event 0 takes place from 2022.9.12 to 2022.12.5.",
            "event 2 occurs from 2022.8.20 to 2022.12.5.",
            "event 2 was overlapped by event 1.",
            "There is no overlap between event 0 and event 1.",
        ],
    }


# how to recursively generate more complex samples?
def generate_complex_sample(base_sample, formula_num: int):
    # based on the choosed formulas, generate more complex samples
    target = {
        "l": base_sample["formulas"][formula_num]["l"],
        "r": base_sample["formulas"][formula_num]["r"],
        "rel": base_sample["formulas"][formula_num]["rel"],
    }

    