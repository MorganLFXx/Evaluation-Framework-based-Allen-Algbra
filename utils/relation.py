import calendar
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


def random_relation() -> str:
    """Generate a random Allen's interval relation."""
    import random

    relations = list(allen_relations.keys())
    return random.choice(relations)


def get_time_relation(A, B) -> str:
    # Determine the Allen's interval relation between two TimeIntervals A and B.
    # start_A = (A.start_year, A.start_month or 1, A.start_day or 1)
    # end_A = (
    #     A.end_year,
    #     A.end_month or 12,
    #     A.end_day or calendar.monthrange(A.end_year, A.end_month or 12)[1],
    # )
    # start_B = (B.start_year, B.start_month or 1, B.start_day or 1)
    # end_B = (
    #     B.end_year,
    #     B.end_month or 12,
    #     B.end_day or calendar.monthrange(B.end_year, B.end_month or 12)[1],
    # )
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


# def relation_composition(rel1: str, rel2: str) -> str:
#     """Compose two Allen's interval relations."""
#     # TODO
#     composition_table = {
#         # This is a simplified version; a full table would be more complex
#         ("p", "p"): "p",
#         ("p", "m"): "p",
#         ("m", "p"): "p",
#         ("m", "m"): "m",
#         # Add more combinations as needed
#     }
#     # return composition_table.get((rel1, rel2), "unknown")
#     raise NotImplementedError("Full relation composition table is not implemented yet.")

