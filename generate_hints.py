import random
from utils.relation import allen_relations

NEGATION_TEMPLATES = {
    "p": [],
    "P": [],
    "m": [],
    "M": [],
    "o": [],
    "O": [],
    "F": [],
    "f": [],
    "D": [],
    "d": [],
    "s": [],
    "S": [],
    "e": [],
}

HINT_TEMPLATES = {
    "p": [
        "'{event_l}{l_no}' ends before '{event_r}{r_no}' starts.",
        "Some time after '{event_l}{l_no}' ended, '{event_r}{r_no}' occurred.",
        "After '{event_l}{l_no}' had been underway for some time, Tom finally made up his mind to initiate '{event_r}{r_no}'.",
        "'{event_l}{l_no}' concluded ahead of '{event_r}{r_no}' kicking off.",
        "There was a gap between the finish of '{event_l}{l_no}' and the start of '{event_r}{r_no}'.",
    ],
    "P": [
        "'{event_l}{l_no}' starts after '{event_r}{r_no}' ends.",
        "'{event_r}{r_no}' ended before '{event_l}{l_no}' started.",
    ],
    "m": [
        "'{event_l}{l_no}' ends exactly when '{event_r}{r_no}' starts.",
        "'{event_r}{r_no}' began the moment '{event_l}{l_no}' wrapped up.",
    ],
    "M": [
        "'{event_l}{l_no}' starts exactly when '{event_r}{r_no}' ends.",
        "'{event_l}{l_no}' commenced right as '{event_r}{r_no}' wrapped up.",
    ],
    "o": [
        "'{event_l}{l_no}' starts before '{event_r}{r_no}' starts and ends after '{event_r}{r_no}' starts but before '{event_r}{r_no}' ends.",
        "'{event_l}{l_no}' and '{event_r}{r_no}' overlap in time. But '{event_l}{l_no}' starts first.",
    ],
    "O": [
        "'{event_l}{l_no}' starts after '{event_r}{r_no}' starts but before it ends and ends after '{event_r}{r_no}' ends.",
        "'{event_l}{l_no}' and '{event_r}{r_no}' overlap in time. But '{event_r}{r_no}' starts first.",
    ],
    "F": [
        "'{event_l}{l_no}' ends exactly when '{event_r}{r_no}' ends, but starts before '{event_r}{r_no}' starts.",
        "'{event_l}{l_no}' finishes at the same time as '{event_l}{l_no}' but began earlier.",
    ],
    "f": [
        "'{event_l}{l_no}' starts after '{event_r}{r_no}' starts and ends exactly when '{event_r}{r_no}' ends."
        "'{event_l}{l_no}' finishes at the same time as '{event_r}{r_no}' but began earlier.",
    ],
    "D": [
        "'{event_l}{l_no}' starts before '{event_r}{r_no}' starts and ends after '{event_r}{r_no}' ends."
        "During '{event_l}{l_no}', '{event_r}{r_no}' started and ended."
    ],
    "d": [
        "'{event_l}{l_no}' starts after '{event_r}{r_no}' starts and ends before '{event_r}{r_no}' ends."
        "The duration of '{event_l}{l_no}' is part of the duration of '{event_r}{r_no}'."
    ],
    "s": [
        "'{event_l}{l_no}' starts exactly when '{event_r}{r_no}' starts and ends before '{event_r}{r_no}' ends."
        "'{event_l}{l_no}' starts at the same time as '{event_r}{r_no}' but ends later."
    ],
    "S": [
        "'{event_l}{l_no}' starts exactly when '{event_r}{r_no}' starts and ends after '{event_r}{r_no}' ends."
        "'{event_l}{l_no}' starts at the same time as '{event_r}{r_no}' but ends earlier."
    ],
    "e": [
        "'{event_l}{l_no}' starts exactly when '{event_r}{r_no}' starts and ends exactly when '{event_r}{r_no}' ends."
        "'{event_l}{l_no}' and '{event_r}{r_no}' overlap completely in time."
    ],
}

"""
oFD, osd, DSO, dfO, pmo, OMP, Fef, seS
pmoFD, pmosd, DSOMP, dfOMP
full, concur
"""


def no_determine_length(rel):
    if rel not in ["F", " f", "D", "d", "s", "S", "e"]:
        choice = [
            "Cannot determine which event '{event_l}{l_no}' or '{event_r}{r_no}' lasts longer",
            "It is unclear which event '{event_l}{l_no}' or '{event_r}{r_no}' has a longer duration",
            "The lengths of events '{event_l}{l_no}' and '{event_r}{r_no}' cannot be compared definitively",
        ]
        return random.choice(choice)
    else:
        return None


def longer_than(rel):
    if rel in ["F", "D", "S"]:
        choice = [
            "You can be certain that '{event_l}{l_no}' lasts longer than '{event_r}{r_no}'.",
            "Event '{event_l}{l_no}' has a longer duration compared to '{event_r}{r_no}'.",
            "'{event_l}{l_no}' extends over a longer time span than '{event_r}{r_no}'",
        ]
        return random.choice(choice)
    else:
        return None


def shorter_than(rel):
    if rel in ["f", "d", "s"]:
        choice = [
            "You can be certain that '{event_l}{l_no}' lasts shorter than '{event_r}{r_no}'.",
            "Event '{event_l}{l_no}' has a shorter duration compared to '{event_r}{r_no}'.",
            "'{event_l}{l_no}' extends over a shorter time span than '{event_r}{r_no}'",
        ]
        return random.choice(choice)
    else:
        return None


def no_overlap(rel):
    if rel in ["p", "P", "m", "M"]:
        choice = [
            "There is no overlap between event '{event_l}{l_no}' and '{event_r}{r_no}'",
            "Events '{event_l}{l_no}' and '{event_r}{r_no}' do not overlap in time",
            "No temporal overlap exists between events '{event_l}{l_no}' and '{event_r}{r_no}'",
        ]
        return random.choice(choice)
    else:
        return None


def overlaps(rel):
    if rel in ["o", "O", "F", "f", "D", "d", "s", "S", "e"]:
        choice = [
            "Events '{event_l}{l_no}' and '{event_r}{r_no}' overlap in time",
            "There is a temporal overlap between events '{event_l}{l_no}' and '{event_r}{r_no}'",
            "At one point, both '{event_l}{l_no}' and '{event_r}{r_no}' were active.",
        ]
        return random.choice(choice)
    else:
        return None


def only_follow(rel):
    if rel in ["m", "M"]:
        choice = [
            "Although '{event_l}{l_no}' and '{event_r}{r_no}' are not overlapping, they are sequential.",
            "'{event_l}{l_no}' and '{event_r}{r_no}' are like day and night: connected but not overlapping.",
        ]
        return random.choice(choice)
    else:
        return None


def happen_before(rel):
    if rel in ["p", "m", "o", "F", "D"]:
        choice = [
            "'{event_l}{l_no}' happens before '{event_r}{r_no}'",
            "'{event_l}{l_no}' takes place prior to '{event_r}{r_no}'",
            "'{event_l}{l_no}' occurs earlier than '{event_r}{r_no}'",
        ]
        return random.choice(choice)
    else:
        return None


def happen_after(rel):
    if rel in ["P", "M", "O", "f", "d"]:
        choice = [
            "'{event_l}{l_no}' happens after '{event_r}{r_no}'",
            "'{event_l}{l_no}' takes place later than '{event_r}{r_no}'",
            "'{event_l}{l_no}' occurs subsequent to '{event_r}{r_no}'",
        ]
        return random.choice(choice)
    else:
        return None


def ends_before(rel):
    if rel in ["p", "m", "o", "s", "d"]:
        choices = [
            "'{event_l}{l_no}' ends before '{event_r}{r_no}' ends.",
            "'{event_l}{l_no}' concludes prior to the conclusion of '{event_r}{r_no}'.",
            "'{event_l}{l_no}' finishes earlier than '{event_r}{r_no}'.",
        ]
        return random.choice(choices)
    else:
        return None


def ends_after(rel):
    if rel in ["P", "M", "O", "S", "D"]:
        choices = [
            "'{event_l}{l_no}' ends after '{event_r}{r_no}' ends.",
            "'{event_l}{l_no}' concludes subsequent to the conclusion of '{event_r}{r_no}'.",
            "'{event_l}{l_no}' finishes later than '{event_r}{r_no}'.",
        ]
        return random.choice(choices)
    else:
        return None


def equals(rel):
    if rel == "e":
        choice = [
            "'{event_l}{l_no}' does not start before or after '{event_r}{r_no}', nor does it end before or after it.",
            "'{event_l}{l_no}' and '{event_r}{r_no}' have the same duration and occur simultaneously"
            "'{event_l}{l_no}' and '{event_r}{r_no}' have the same duration and end simultaneously",
        ]
        return random.choice(choice)
    else:
        return None


def starts(rel):
    if rel in ["s", "S", "e"]:
        choice = [
            "'{event_l}{l_no}' starts when '{event_r}{r_no}' starts.",
            "'{event_l}{l_no}' begins at the same time as '{event_r}{r_no}'.",
            "'{event_l}{l_no}' and '{event_r}{r_no}' share the same starting point.",
        ]
        return random.choice(choice)
    else:
        return None


def ends(rel):
    if rel in ["F", "f", "e"]:
        choice = [
            "'{event_l}{l_no}' ends when '{event_r}{r_no}' ends.",
            "'{event_l}{l_no}' concludes at the same time as '{event_r}{r_no}'.",
            "'{event_l}{l_no}' and '{event_r}{r_no}' share the same ending point.",
        ]
        return random.choice(choice)
    else:
        return None


def get_negation(rel: str, l_no: int, r_no: int, events: list) -> list:
    hints = []
    event_l = events[l_no]
    event_r = events[r_no]

    hints.append(
        f"It is not true that '{event_l}{l_no}' {allen_relations[rel]} '{event_r}{r_no}' ."
    )
    return hints


def get_easy_hint(rel: str, l_no: int, r_no: int, events: list, is_not: bool) -> list:
    """Generate hints based on relation and event numbers"""
    hints = []
    event_l = events[l_no]
    event_r = events[r_no]
    if is_not:
        return get_negation(rel, l_no, r_no, events)

    template = random.choice(HINT_TEMPLATES[rel])
    hints.append(
        template.format(event_l=event_l, l_no=l_no, event_r=event_r, r_no=r_no)
    )

    return hints


def generate_evidences(rel: str, l_no: int, r_no: int, events: list):
    funcs = [
        happen_before,
        happen_after,
        ends_before,
        ends_after,
        no_overlap,
        overlaps,
        only_follow,
        no_determine_length,
        longer_than,
        shorter_than,
        starts,
        ends,
        equals,
    ]
    evidences = []
    for func in funcs:
        evidence = func(rel)
        if evidence is None:
            continue
        evidences.append(
            evidence.format(
                event_l=events[l_no], l_no=l_no, event_r=events[r_no], r_no=r_no
            )
        )
    return evidences


def generate_negative_hints(formulas, events):
    """直接将否定关系转换为自然语言"""
    hints = []
    for i, formula in enumerate(formulas):
        l_no = formula["l"]
        r_no = formula["r"]
        rel = formula["rel"]
        generated_hints = get_easy_hint(
            rel, l_no, r_no, events, formula.get("type") == "not"
        )
        # add hint indices to formula
        hint_indices = []
        for hint in generated_hints:
            hints.append(hint)
            hint_indices.append(len(hints) - 1)
        formulas[i]["hints"] = hint_indices
    return hints


def generate_positive_hints(formulas, paths, events):
    """通过正面佐证实际成立的关系来体现否定关系"""
    hints = []
    # no need to 'not' formulas
    new_formulas = []
    for formula in formulas:
        if formula.get("type") != "not":
            new_formulas.append(formula)
    formulas = new_formulas

    for i, formula in enumerate(formulas):
        l_no = formula["l"]
        r_no = formula["r"]
        rel = formula["rel"]
        generated_hints = get_easy_hint(
            rel, l_no, r_no, events, formula.get("type") == "not"
        )
        # add hint indices to formula
        hint_indices = []
        for hint in generated_hints:
            hints.append(hint)
            hint_indices.append(len(hints) - 1)
        formulas[i]["hints"] = hint_indices

    # add further evidence
    for path in reversed(paths):
        evidences = generate_evidences(
            path["target"], path["base_event"][0], path["base_event"][1], events
        )
        # 不提供这些evidence对应的formula
        hints.extend(evidences)
    return hints
