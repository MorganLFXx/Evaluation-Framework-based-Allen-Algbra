import random

# Allen's Interval Algebra relations

allen_relations = {
    "p": "precedes",
    "m": "meets",
    "o": "overlaps",
    "F": "finished_by",
    "D": "contains",
    "s": "starts",
    "e": "equals",
    "S": "started_by",
    "d": "during",
    "f": "finishes",
    "O": "overlapped_by",
    "M": "met_by",
    "P": "preceded_by",
}

full = "pmoFDseSdfOMP"
concur = "oFDseSdfO"

composition_table = {
    # p x rel
    ("p", "p"): "p",
    ("p", "m"): "p",
    ("p", "o"): "p",
    ("p", "F"): "p",
    ("p", "D"): "p",
    ("p", "s"): "p",
    ("p", "e"): "p",
    ("p", "S"): "p",
    ("p", "d"): "pmosd",
    ("p", "f"): "pmosd",
    ("p", "O"): "pmosd",
    ("p", "M"): "pmosd",
    ("p", "P"): full,
    # m x rel
    ("m", "p"): "p",
    ("m", "m"): "p",
    ("m", "o"): "p",
    ("m", "F"): "p",
    ("m", "D"): "p",
    ("m", "s"): "m",
    ("m", "e"): "m",
    ("m", "S"): "m",
    ("m", "d"): "osd",
    ("m", "f"): "osd",
    ("m", "O"): "osd",
    ("m", "M"): "Fef",
    ("m", "P"): "DSOMP",
    # o x rel
    ("o", "p"): "p",
    ("o", "m"): "p",
    ("o", "o"): "pmo",
    ("o", "F"): "pmo",
    ("o", "D"): "pmoFD",
    ("o", "s"): "o",
    ("o", "e"): "o",
    ("o", "S"): "oFD",
    ("o", "d"): "osd",
    ("o", "f"): "osd",
    ("o", "O"): concur,
    ("o", "M"): "DSO",
    ("o", "P"): "DSOMP",
    # F x rel
    ("F", "p"): "p",
    ("F", "m"): "m",
    ("F", "o"): "o",
    ("F", "F"): "F",
    ("F", "D"): "D",
    ("F", "s"): "o",
    ("F", "e"): "F",
    ("F", "S"): "D",
    ("F", "d"): "osd",
    ("F", "f"): "Fef",
    ("F", "O"): "DSO",
    ("F", "M"): "DSO",
    ("F", "P"): "DSOMP",
    # D x rel
    ("D", "p"): "pmoFD",
    ("D", "m"): "oFD",
    ("D", "o"): "oFD",
    ("D", "F"): "D",
    ("D", "D"): "D",
    ("D", "s"): "oFD",
    ("D", "e"): "D",
    ("D", "S"): "D",
    ("D", "d"): concur,
    ("D", "f"): "DSO",
    ("D", "O"): "DSO",
    ("D", "M"): "DSO",
    ("D", "P"): "DSOMP",
    # s x rel
    ("s", "p"): "p",
    ("s", "m"): "p",
    ("s", "o"): "pmo",
    ("s", "F"): "pmo",
    ("s", "D"): "pmoFD",
    ("s", "s"): "s",
    ("s", "e"): "s",
    ("s", "S"): "seS",
    ("s", "d"): "d",
    ("s", "f"): "d",
    ("s", "O"): "dfO",
    ("s", "M"): "M",
    ("s", "P"): "P",
    # e x rel
    ("e", "p"): "p",
    ("e", "m"): "m",
    ("e", "o"): "o",
    ("e", "F"): "F",
    ("e", "D"): "D",
    ("e", "s"): "s",
    ("e", "e"): "e",
    ("e", "S"): "S",
    ("e", "d"): "d",
    ("e", "f"): "f",
    ("e", "O"): "O",
    ("e", "M"): "M",
    ("e", "P"): "P",
    # S x rel
    ("S", "p"): "pmoFD",
    ("S", "m"): "oFD",
    ("S", "o"): "oFD",
    ("S", "F"): "D",
    ("S", "D"): "D",
    ("S", "s"): "seS",
    ("S", "e"): "S",
    ("S", "S"): "S",
    ("S", "d"): "dfO",
    ("S", "f"): "O",
    ("S", "O"): "O",
    ("S", "M"): "M",
    ("S", "P"): "P",
    # d x rel
    ("d", "p"): "p",
    ("d", "m"): "p",
    ("d", "o"): "pmosd",
    ("d", "F"): "pmosd",
    ("d", "D"): full,
    ("d", "s"): "d",
    ("d", "e"): "d",
    ("d", "S"): "dfOMP",
    ("d", "d"): "d",
    ("d", "f"): "d",
    ("d", "O"): "dfOMP",
    ("d", "M"): "P",
    ("d", "P"): "P",
    # f x rel
    ("f", "p"): "p",
    ("f", "m"): "m",
    ("f", "o"): "osd",
    ("f", "F"): "Fef",
    ("f", "D"): "DSOMP",
    ("f", "s"): "d",
    ("f", "e"): "f",
    ("f", "S"): "OMP",
    ("f", "d"): "d",
    ("f", "f"): "f",
    ("f", "O"): "OMP",
    ("f", "M"): "P",
    ("f", "P"): "P",
    # O x rel
    ("O", "p"): "pmoFD",
    ("O", "m"): "oFD",
    ("O", "o"): concur,
    ("O", "F"): "DSO",
    ("O", "D"): "DSOMP",
    ("O", "s"): "dfO",
    ("O", "e"): "O",
    ("O", "S"): "OMP",
    ("O", "d"): "dfO",
    ("O", "f"): "O",
    ("O", "O"): "OMP",
    ("O", "M"): "P",
    ("O", "P"): "P",
    # M x rel
    ("M", "p"): "pmoFD",
    ("M", "m"): "seS",
    ("M", "o"): "dfO",
    ("M", "F"): "M",
    ("M", "D"): "P",
    ("M", "s"): "dfO",
    ("M", "e"): "M",
    ("M", "S"): "P",
    ("M", "d"): "dfO",
    ("M", "f"): "M",
    ("M", "O"): "P",
    ("M", "M"): "P",
    ("M", "P"): "P",
    # P x rel
    ("P", "p"): full,
    ("P", "m"): "dfOMP",
    ("P", "o"): "dfOMP",
    ("P", "F"): "P",
    ("P", "D"): "P",
    ("P", "s"): "dfOMP",
    ("P", "e"): "P",
    ("P", "S"): "P",
    ("P", "d"): "dfOMP",
    ("P", "f"): "P",
    ("P", "O"): "P",
    ("P", "M"): "P",
    ("P", "P"): "P",
}


def random_relation() -> str:
    """Generate a random Allen's interval relation."""
    import random

    relations = list(allen_relations.keys())
    return random.choice(relations)


def get_time_relation(A, B) -> str:
    start_A = A.start_year
    end_A = A.end_year
    start_B = B.start_year
    end_B = B.end_year
    if end_A < start_B:
        return "p"  # precedes
    if start_A > end_B:
        return "P"  # preceded_by
    if end_A == start_B:
        return "m"  # meets
    if start_A == end_B:
        return "M"  # met_by
    if start_A < start_B and end_A > start_B and end_A < end_B:
        return "o"  # overlaps
    if start_A > start_B and start_A < end_B and end_A > end_B:
        return "O"  # overlapped_by
    if end_A == end_B and start_A < start_B:
        return "F"  # finished_by
    if end_A == end_B and start_A > start_B:
        return "f"  # finishes
    if start_A < start_B and end_A > end_B:
        return "D"  # contains
    if start_A > start_B and end_A < end_B:
        return "d"  # during
    if start_A == start_B and end_A < end_B:
        return "s"  # starts
    if start_A == start_B and end_A > end_B:
        return "S"  # started_by
    if start_A == start_B and end_A == end_B:
        return "e"  # equals
    else:
        print(start_A, end_A, start_B, end_B)
        raise ValueError(
            "Unable to determine the relation between the given intervals."
        )


def is_transitive_relation(rel: str) -> bool:
    """Check if the given Allen's interval relation is transitive."""
    transitive_relations = {"p", "P", "e", "s", "S", "f", "F", "d", "D"}
    return rel in transitive_relations


def random_transitive_relation() -> str:
    """Generate a random transitive Allen's interval relation."""
    import random

    transitive_relations = ["p", "P", "s", "S", "f", "F", "d", "D"]
    return random.choice(transitive_relations)


def get_inverse_relation(rel: str) -> str:
    """Get the inverse of the given Allen's interval relation."""
    return rel.swapcase()


def get_composition(rel: str):
    """Get the composition values contains rel and random return one"""
    compositions = []
    for item in composition_table.items():
        key, value = item
        if rel in value:
            compositions.append(item)
    if compositions:
        return random.choice(compositions)
    else:
        raise ValueError(f"No composition found for relation: {rel}")


def get_negation(rel: str, l_no: int, r_no: int, events: list) -> list:
    hints = []
    event_l = events[l_no]
    event_r = events[r_no]
    hints.append(
        f"It is not true that '{event_l}{l_no}' {allen_relations[rel]} '{event_r}{r_no}' ."
    )

    return hints


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


def get_hint(rel: str, l_no: int, r_no: int, events: list, is_not: bool) -> list:
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


def main():
    get_composition("p")


if __name__ == "__main__":
    main()
