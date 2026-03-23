import random
import enum
import re


class StartTime(enum.Enum):
    BEFORE = "before"
    AFTER = "after"
    START = "same"


class EndTime(enum.Enum):
    BEFORE = "before"
    AFTER = "after"
    END = "same"


class Overlap(enum.Enum):
    YES = "yes"
    NO = "no"


class Duration(enum.Enum):
    LONGER = "longer"
    SHORTER = "shorter"
    EQUAL = "equal"
    NO_DETERMINE = "no determine"


class Meet(enum.Enum):
    YES = "yes"
    NO = "no"


RELATION_DEFINITIONS = {
    "p": {
        "start": StartTime.BEFORE,
        "end": EndTime.BEFORE,
        "overlap": Overlap.NO,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.NO,
    },
    "P": {
        "start": StartTime.AFTER,
        "end": EndTime.AFTER,
        "overlap": Overlap.NO,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.NO,
    },
    "m": {
        "start": StartTime.BEFORE,
        "end": EndTime.BEFORE,
        "overlap": Overlap.NO,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.YES,
    },
    "M": {
        "start": StartTime.AFTER,
        "end": EndTime.AFTER,
        "overlap": Overlap.NO,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.YES,
    },
    "o": {
        "start": StartTime.BEFORE,
        "end": EndTime.BEFORE,
        "overlap": Overlap.YES,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.NO,
    },
    "O": {
        "start": StartTime.AFTER,
        "end": EndTime.AFTER,
        "overlap": Overlap.YES,
        "duration": Duration.NO_DETERMINE,
        "meet": Meet.NO,
    },
    "f": {
        "start": StartTime.AFTER,
        "end": EndTime.END,
        "overlap": Overlap.YES,
        "duration": Duration.SHORTER,
        "meet": Meet.NO,
    },
    "F": {
        "start": StartTime.BEFORE,
        "end": EndTime.END,
        "overlap": Overlap.YES,
        "duration": Duration.LONGER,
        "meet": Meet.NO,
    },
    "s": {
        "start": StartTime.START,
        "end": EndTime.BEFORE,
        "overlap": Overlap.YES,
        "duration": Duration.SHORTER,
        "meet": Meet.NO,
    },
    "S": {
        "start": StartTime.START,
        "end": EndTime.AFTER,
        "overlap": Overlap.YES,
        "duration": Duration.LONGER,
        "meet": Meet.NO,
    },
    "d": {
        "start": StartTime.AFTER,
        "end": EndTime.BEFORE,
        "overlap": Overlap.YES,
        "duration": Duration.SHORTER,
        "meet": Meet.NO,
    },
    "D": {
        "start": StartTime.BEFORE,
        "end": EndTime.AFTER,
        "overlap": Overlap.YES,
        "duration": Duration.LONGER,
        "meet": Meet.NO,
    },
    "e": {
        "start": StartTime.START,
        "end": EndTime.END,
        "overlap": Overlap.YES,
        "duration": Duration.EQUAL,
        "meet": Meet.NO,
    },
}


HINT_TEMPLATES = {
    "p": [
        "'{event_l}' ends before '{event_r}' starts.",
        "Some time after '{event_l}' ended, '{event_r}' occurred.",
        "'{event_l}' ended before '{event_r}' started.",
        "'{event_l}' concluded ahead of '{event_r}' kicking off.",
        "There was a gap between the finish of '{event_l}' and the start of '{event_r}'.",
    ],
    "P": [
        "'{event_l}' starts after '{event_r}' ends.",
        "Some time after '{event_r}' ended, '{event_l}' occurred.",
        "'{event_r}' ended before '{event_l}' started.",
        "'{event_r}' concluded ahead of '{event_l}' kicking off.",
        "There was a gap between the finish of '{event_r}' and the start of '{event_l}'.",
    ],
    "m": [
        "'{event_l}' ends exactly when '{event_r}' starts.",
        "'{event_r}' began the moment '{event_l}' wrapped up.",
        "There is no time interval between the termination of '{event_l}' and the initiation of '{event_r}'",
    ],
    "M": [
        "'{event_l}' starts exactly when '{event_r}' ends.",
        "'{event_l}' commenced right as '{event_r}' wrapped up.",
        "There is no time interval between the termination of '{event_r}' and the initiation of '{event_l}'",
    ],
    "o": [
        "'{event_l}' starts before '{event_r}' starts and ends after '{event_r}' starts but before '{event_r}' ends.",
        "'{event_l}' and '{event_r}' overlap in time. '{event_l}' starts first. And we can't tell which one lasts longer.",
    ],
    "O": [
        "'{event_l}' starts after '{event_r}' starts but before it ends and ends after '{event_r}' ends.",
        "'{event_l}' and '{event_r}' overlap in time. '{event_r}' starts first. And we can't tell which one lasts longer.",
    ],
    "F": [
        "'{event_l}' ends exactly when '{event_r}' ends, but starts before '{event_r}' starts.",
        "'{event_l}' finishes at the same time as '{event_r}' and began earlier.",
    ],
    "f": [
        "'{event_l}' starts after '{event_r}' starts and ends exactly when '{event_r}' ends.",
        "'{event_r}' finishes at the same time as '{event_l}' and began earlier.",
    ],
    "D": [
        "'{event_l}' starts before '{event_r}' starts and ends after '{event_r}' ends.",
        "The duration of '{event_r}' is part of the duration of '{event_l}' and their start time and end time are different.",
        "During '{event_l}', '{event_r}' started and ended.",
    ],
    "d": [
        "'{event_l}' starts after '{event_r}' starts and ends before '{event_r}' ends.",
        "The duration of '{event_l}' is part of the duration of '{event_r}' and their start time and end time are different.",
        "During '{event_r}', '{event_l}' started and ended.",
    ],
    "s": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends before '{event_r}' ends.",
        "'{event_l}' starts at the same time as '{event_r}' but ends earlier.",
    ],
    "S": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends after '{event_r}' ends.",
        "'{event_l}' starts at the same time as '{event_r}' but ends later.",
    ],
    "e": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends exactly when '{event_r}' ends.",
        "'{event_l}' and '{event_r}' overlap completely in time.",
    ],
}

EXPLANATION_TEMPLATES = {
    "p": "'{event_l}' precedes '{event_r}' or Start('{event_l}') < End('{event_l}') < Start('{event_r}') < End('{event_r}').",
    "P": "'{event_r}' precedes '{event_l}' or Start('{event_r}') < End('{event_r}') < Start('{event_l}') < End('{event_l}').",
    "o": "'{event_l}' overlaps '{event_r}' or Start('{event_l}') < Start('{event_r}') < End('{event_l}') < End('{event_r}').",
    "O": "'{event_r}' overlaps '{event_l}' or Start('{event_r}') < Start('{event_l}') < End('{event_r}') < End('{event_l}').",
    "m": "'{event_l}' meets '{event_r}' or Start('{event_l}') < End('{event_l}') = Start('{event_r}') < End('{event_r}').",
    "M": "'{event_r}' meets '{event_l}' or Start('{event_r}') < End('{event_r}') = Start('{event_l}') < End('{event_l}').",
    "s": "'{event_l}' starts '{event_r}' or Start('{event_l}') = Start('{event_r}') < End('{event_l}') < End('{event_r}').",
    "S": "'{event_l}' is started by '{event_r}' or Start('{event_l}') = Start(''{event_r}') < End('{event_r}') < End('{event_l}').",
    "d": "'{event_l}' during '{event_r}' or Start('{event_r}') < Start(''{event_l}') < End('{event_l}') < End('{event_r}').",
    "D": "'{event_l}' contains '{event_r}' or Start('{event_l}') < Start('{event_r}') < End('{event_r}') < End('{event_l}').",
    "f": "'{event_l}' finishes '{event_r}' or Start('{event_r}') < Start('{event_l}') < End('{event_l}') = End('{event_r}').",
    "F": "'{event_l}' is finished by '{event_r}' or Start('{event_l}') < Start('{event_r}') < End('{event_l}') = End('{event_r}').",
    "e": "'{event_l}' equals '{event_r}' or Start('{event_l}') = Start('{event_r}') < End('{event_l}') = End('{event_r}').",
}


def get_rels_explanations(rels: list, event_l, event_r, events) -> list:
    explanations = []
    for rel in rels:
        explanation = EXPLANATION_TEMPLATES[rel].format(
            event_l=events[event_l], event_r=events[event_r]
        )
        explanations.append(explanation)
    return explanations


"""
oFD, osd, DSO, dfO, pmo, OMP, Fef, seS
pmoFD, pmosd, DSOMP, dfOMP
full, concur
"""

ATTR_HINT_TEMPLATES = {
    StartTime.BEFORE: [
        "'{event_l}' starts before '{event_r}' starts.",
        "'{event_l}' triggers earlier than '{event_r}'(Only related to the start time. Not the whole event)",
        "'{event_l}' begins earlier than '{event_r}'(Only related to the start time. Not the whole event).",
    ],
    StartTime.AFTER: [
        "'{event_l}' starts after '{event_r}' starts.",
        "'{event_l}' triggers later thn '{event_r}'(Only related to the start time. Not the whole event)",
        "'{event_l}' begins later than '{event_r}'(Only related to the start time. Not the whole event).",
    ],
    StartTime.START: [
        "'{event_l}' starts when '{event_r}' starts.",
        "'{event_l}' begins at the same time as '{event_r}'.",
        "'{event_l}' and '{event_r}' share the same starting point.",
    ],
    EndTime.BEFORE: [
        "'{event_l}' ends before '{event_r}' ends.",
        "'{event_l}' concludes prior to the conclusion of '{event_r}'.",
        "'{event_l}' finishes earlier than '{event_r}'.",
    ],
    EndTime.AFTER: [
        "'{event_l}' ends after '{event_r}' ends.",
        "'{event_l}' concludes after the conclusion of '{event_r}'.",
        "'{event_l}' finishes later than '{event_r}'.",
    ],
    EndTime.END: [
        "'{event_l}' ends when '{event_r}' ends.",
        "'{event_l}' concludes at the same time as '{event_r}'.",
        "'{event_l}' and '{event_r}' share the same ending point.",
    ],
    Overlap.YES: [
        "Events '{event_l}' and '{event_r}' overlap in time",
        "There is a temporal overlap between events '{event_l}' and '{event_r}'",
        "During a period of time, both '{event_l}' and '{event_r}' were active.",
    ],
    Overlap.NO: [
        "There is no overlap between '{event_l}' and '{event_r}'",
        "'{event_l}' and '{event_r}' do not overlap in time",
        "No temporal overlap exists between events '{event_l}' and '{event_r}'",
    ],
    Duration.LONGER: [
        "You can be certain that '{event_l}' lasts longer than '{event_r}'.",
        "Event '{event_l}' has a longer duration compared to '{event_r}'.",
        "'{event_l}' extends over a longer time span than '{event_r}'",
    ],
    Duration.SHORTER: [
        "You can be certain that '{event_l}' lasts shorter than '{event_r}'.",
        "Event '{event_l}' has a shorter duration compared to '{event_r}'.",
        "'{event_l}' extends over a shorter time span than '{event_r}'",
    ],
    Duration.EQUAL: [
        "'{event_l}' does not start before or after '{event_r}', nor does it end before or after it.",
        "'{event_l}' and '{event_r}' have the same duration and begin simultaneously",
        "'{event_l}' and '{event_r}' have the same duration and end simultaneously",
    ],
    Duration.NO_DETERMINE: [
        "Cannot determine which event '{event_l}' or '{event_r}' lasts longer",
        "It is unclear which event '{event_l}' or '{event_r}' has a longer duration",
        "The lengths of events '{event_l}' and '{event_r}' cannot be compared",
    ],
    Meet.YES: [
        "'{event_l}' and '{event_r}' are seamlessly connected at this temporal point(This hint does not indicate which event occurred first.).",
        "'{event_l}' and '{event_r}' achieved seamless integration at a specific single point in time.(This hint does not indicate which event occurred first.).",
        "'{event_l}' and '{event_r}' are like day and night: connected but not overlapping.(This hint does not indicate which event occurred first.)",
    ],
    Meet.NO: [
        "There exists no temporal point of coincidence between '{event_l}' and '{event_r}' whatsoever.",
        "Events '{event_l}' and '{event_r}' do not meet at any time",
        "At no time do events '{event_l}' and '{event_r}' coincide",
    ],
}


def no_determine_length():
    choice = ATTR_HINT_TEMPLATES[Duration.NO_DETERMINE]
    return {
        "hint": random.choice(choice),
        "explanation": "The relative length of '{event_l}' and '{event_r}' cannot be determined. So the Allen relation between events '{event_l}' and '{event_r}' is a relation independent of their relative lengths. Exclude relationships that can determine relative length. For example: f,F,s,S,e,d,D",
    }


def longer_than():
    choice = ATTR_HINT_TEMPLATES[Duration.LONGER]
    return {
        "hint": random.choice(choice),
        "explanation": "'{event_l}' has a longer duration compared to '{event_r}'. So '{event_r}' must be part of '{event_l}'. Only relations that indicate one event is part of another are F, D, S.",
    }


def shorter_than():
    choice = ATTR_HINT_TEMPLATES[Duration.SHORTER]
    return {
        "hint": random.choice(choice),
        "explanation": "'{event_l}' has a shorter duration compared to '{event_r}'. So '{event_l}' must be part of '{event_r}'. Only relations that indicate one event is part of another are f, d, s.",
    }


def no_meeting():
    choice = ATTR_HINT_TEMPLATES[Meet.NO]
    return {
        "hint": random.choice(choice),
        "explanation": "There is no temporal point of coincidence between '{event_l}' and '{event_r}'. So '{event_l}' and '{event_r}' do not meet at any time which excludes relationship m,M.",
    }


def no_overlap():
    choice = ATTR_HINT_TEMPLATES[Overlap.NO]
    return {
        "hint": random.choice(choice),
        "explanation": "There is no temporal overlap between '{event_l}' and '{event_r}'. So '{event_l}' and '{event_r}' do not overlap in time which excludes relationships o,O,f,F,d,D,s,S,e and so on.",
    }


def overlaps():
    choice = ATTR_HINT_TEMPLATES[Overlap.YES]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know '{event_l}' and '{event_r}' overlap in time which excludes relationships p,P,m,M.",
    }


def only_follow():
    choice = ATTR_HINT_TEMPLATES[Meet.YES]
    return {
        "hint": random.choice(choice),
        "explanation": "We can observe that '{event_l}' and '{event_r}' are seamlessly connected which indicates that they are related by the 'meet' relationship (m or M).",
    }


def start_before():
    choice = ATTR_HINT_TEMPLATES[StartTime.BEFORE]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know the start time of '{event_l}' is before the start time of '{event_r}'.",
    }


def start_after():
    choice = ATTR_HINT_TEMPLATES[StartTime.AFTER]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know the start time of '{event_l}' is after the start time of '{event_r}'.",
    }


def ends_before():
    choice = ATTR_HINT_TEMPLATES[EndTime.BEFORE]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know the end time of '{event_l}' is before the end time of '{event_r}'.",
    }


def ends_after():
    choice = ATTR_HINT_TEMPLATES[EndTime.AFTER]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know the end time of '{event_l}' is after the end time of '{event_r}'.",
    }


def equals():
    choice = ATTR_HINT_TEMPLATES[Duration.EQUAL]
    return {
        "hint": random.choice(choice),
        "explanation": "It is clear that '{event_l}' equals '{event_r}'.",
    }


def starts():
    choice = ATTR_HINT_TEMPLATES[StartTime.START]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know '{event_l}' starts at the same time as '{event_r}'.",
    }


def ends():
    choice = ATTR_HINT_TEMPLATES[EndTime.END]
    return {
        "hint": random.choice(choice),
        "explanation": "We can know '{event_l}' ends at the same time as '{event_r}'.",
    }


ATTRIBUTE_ORDER = ["start", "end", "overlap", "duration", "meet"]

# Core attributes for each relation (minimal clues) based on hint.md
RELATION_CORE_ATTRS = {
    "p": ["start", "overlap", "meet"],
    "P": ["start", "overlap", "meet"],
    "m": ["start", "meet"],
    "M": ["start", "meet"],
    "o": ["start", "overlap", "duration"],
    "O": ["start", "overlap", "duration"],
    "f": ["start", "end"],
    "F": ["start", "end"],
    "s": ["start", "end"],
    "S": ["start", "end"],
    "d": ["start", "end", "duration"],
    "D": ["start", "end", "duration"],
    "e": ["duration"],
}

ATTRIBUTE_HINT = {
    "start": {
        StartTime.BEFORE: start_before,
        StartTime.AFTER: start_after,
        StartTime.START: starts,
    },
    "end": {
        EndTime.BEFORE: ends_before,
        EndTime.AFTER: ends_after,
        EndTime.END: ends,
    },
    "duration": {
        Duration.LONGER: longer_than,
        Duration.SHORTER: shorter_than,
        Duration.EQUAL: equals,
        Duration.NO_DETERMINE: no_determine_length,
    },
    "overlap": {
        Overlap.YES: overlaps,
        Overlap.NO: no_overlap,
    },
    "meet": {
        Meet.YES: only_follow,
        Meet.NO: no_meeting,
    },
}


def match_event(hint: str):
    """
    Match the two event in a hint.
    Event format: One or several uppercase letters followed by a number
    Return type: tuple of two events str
    """
    events = []
    quoted_matches = re.findall(r"'([A-Z]+\d+)'", hint)
    for event in quoted_matches:
        if event not in events:
            events.append(event)
    return events[0], events[1]


def restore_template(hint: str):
    """
    Convert a hint to its template form.
    Replace the two events with '{event_l}' and '{event_r}'.
    """
    events = match_event(hint)
    if not events:
        return None
    event_l, event_r = events
    template1 = hint.replace(f"'{event_l}'", "'{event_l}'")
    template1 = template1.replace(f"'{event_r}'", "'{event_r}'")

    template2 = hint.replace(f"'{event_l}'", "'{event_r}'")
    template2 = template2.replace(f"'{event_r}'", "'{event_l}'")

    return template1, template2  # because we aren't sure the position of l and r


def swap_rel_hint(hint: str):
    """
    Swap the positions of two events in a hint.
    Note: How about 'equal' relation
    """
    events = match_event(hint)
    if not events:
        return None
    event_l, event_r = events
    template1, template2 = restore_template(hint)

    if template1 in HINT_TEMPLATES["e"] or template2 in HINT_TEMPLATES["e"]:
        non_equal_rel = random.choice([rel for rel in HINT_TEMPLATES if rel != "e"])
        non_equal_template = random.choice(HINT_TEMPLATES[non_equal_rel])
        return non_equal_template.format(event_l=event_l, event_r=event_r)

    return template2.format(event_l=event_l, event_r=event_r)


relation_templates = {
    item for templates in HINT_TEMPLATES.values() for item in templates
}


def judge_relation_hint(hint: str):
    """
    Judge whether a hint is a relation hint.
    Note: relation hint means hints in HINT_TEMPLATES
    Need: match_event()
    Step: 1. Check if the hint is in HINT_TEMPLATES 2. If yes, match the two events in the hint 3. Flip the positions of two events.
    """
    template1, template2 = restore_template(hint)

    if template1 not in relation_templates and template2 not in relation_templates:
        return False

    return True


def convert_anti_hint(hint: str):
    """
    Convert a hint to its antisense form.
    Need: match_backward(), judge_relation_hint(), match_event()
    Step: If the hint is not a relation hint, convert it to its antisense form(Refer to the ATTRIBUTE_HINT dictionary).
    """
    # if judge_relation_hint(hint):
    #     return swap_rel_hint(hint)

    event_l, event_r = match_event(hint)
    template1, template2 = restore_template(hint)
    hint_attr = None

    for attr in ATTR_HINT_TEMPLATES:
        if (
            template1 in ATTR_HINT_TEMPLATES[attr]
            or template2 in ATTR_HINT_TEMPLATES[attr]
        ):
            hint_attr = attr

    opposite_funcs = []
    for item in ATTRIBUTE_HINT.keys():
        if hint_attr in ATTRIBUTE_HINT[item].keys():
            for attr_val in ATTRIBUTE_HINT[item].keys():
                if attr_val != hint_attr:
                    opposite_funcs.append(ATTRIBUTE_HINT[item][attr_val])
    return (
        random.choice(opposite_funcs)()
        .get("hint", "")
        .format(event_l=event_l, event_r=event_r)
    )


def _attribute_to_func(rel: str, attr: str):
    attr_val = RELATION_DEFINITIONS[rel][attr]
    return ATTRIBUTE_HINT[attr][attr_val]


def get_core_attributes(rel: str):
    return RELATION_CORE_ATTRS.get(rel, ATTRIBUTE_ORDER)


def build_attribute_hint(rel: str, attr: str, events: list, l_no: int, r_no: int):
    func = _attribute_to_func(rel, attr)
    if func is None:
        return None
    info = func()
    if not info:
        return None
    return {
        "hint": info["hint"].format(event_l=events[l_no], event_r=events[r_no]),
        "explanation": info["explanation"].format(
            event_l=events[l_no], event_r=events[r_no]
        ),
    }


def pick_discriminating_attributes(target_rel: str, excluded_rel: str):
    """Pick minimal attributes that differ between target and excluded relations."""
    target_def = RELATION_DEFINITIONS[target_rel]
    excluded_def = RELATION_DEFINITIONS[excluded_rel]

    core_attrs = get_core_attributes(excluded_rel)
    diffs = [attr for attr in core_attrs if target_def[attr] != excluded_def[attr]]
    if diffs:
        return diffs[:1]

    fallback_diffs = [
        attr for attr in ATTRIBUTE_ORDER if target_def[attr] != excluded_def[attr]
    ]
    return fallback_diffs[:1]


def main():
    pass


if __name__ == "__main__":
    main()
