import random

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


def get_inverse_relation(rel: str) -> str:
    """Get the inverse of the given Allen's interval relation."""
    return rel.swapcase()


def get_composition(rel: str):
    """Get the composition values contains rel and random return one"""
    compositions = []
    for item in composition_table.items():
        key, value = item
        if rel in value and value != full:
            compositions.append(item)
    if compositions:
        return random.choice(compositions)
    else:
        raise ValueError(f"No composition found for relation: {rel}")


def main():
    get_composition("p")


if __name__ == "__main__":
    main()
