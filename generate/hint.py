import random
import enum


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
        "'{event_l}' concluded ahead of '{event_r}' kicking off.",
        "There was a gap between the finish of '{event_l}' and the start of '{event_r}'.",
    ],
    "P": [
        "'{event_l}' starts after '{event_r}' ends.",
        "'{event_r}' ended before '{event_l}' started.",
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
        "During '{event_l}', '{event_r}' started and ended.",
    ],
    "d": [
        "'{event_l}' starts after '{event_r}' starts and ends before '{event_r}' ends.",
        "The duration of '{event_l}' is part of the duration of '{event_r}' and their start time and end time are different.",
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
    "p": "'{event_l}' precedes '{event_r}'",
    "P": "'{event_r}' precedes '{event_l}'",
    "o": "'{event_l}' overlaps '{event_r}'",
    "O": "'{event_r}' overlaps '{event_l}'",
    "m": "'{event_l}' meets '{event_r}'",
    "M": "'{event_r}' meets '{event_l}'",
    "s": "'{event_l}' starts '{event_r}'",
    "S": "'{event_l}' is started by '{event_r}'",
    "d": "'{event_l}' during '{event_r}'",
    "D": "'{event_l}' contains '{event_r}'",
    "f": "'{event_l}' finishes '{event_r}'",
    "F": "'{event_l}' is finished by '{event_r}'",
    "e": "'{event_l}' equals '{event_r}'",
}

"""
oFD, osd, DSO, dfO, pmo, OMP, Fef, seS
pmoFD, pmosd, DSOMP, dfOMP
full, concur
"""


def no_determine_length(rel):
    if rel not in ["F", "f", "D", "d", "s", "S", "e"]:
        choice = [
            # "Cannot determine which event '{event_l}' or '{event_r}' lasts longer",
            # "It is unclear which event '{event_l}' or '{event_r}' has a longer duration",
            # "The lengths of events '{event_l}' and '{event_r}' cannot be compared",
            "The Allen relation between '{event_l}' and '{event_r}' specifies temporal ordering, not relative duration.",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "The relative length of '{event_l}' and '{event_r}' cannot be determined. So the Allen relation between events '{event_l}' and '{event_r}' is a relation independent of their relative lengths. Exclude relationships that can determine relative length. For example: f,F,s,S,e,d,D",
        }
    else:
        return None


def longer_than(rel):
    if rel in ["F", "D", "S"]:
        choice = [
            "You can be certain that '{event_l}' lasts longer than '{event_r}'.",
            "Event '{event_l}' has a longer duration compared to '{event_r}'.",
            "'{event_l}' extends over a longer time span than '{event_r}'",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "'{event_l}' has a longer duration compared to '{event_r}'. So '{event_r}' must be part of '{event_l}'. Only relations that indicate one event is part of another are F, D, S.",
        }
    else:
        return None


def shorter_than(rel):
    if rel in ["f", "d", "s"]:
        choice = [
            "You can be certain that '{event_l}' lasts shorter than '{event_r}'.",
            "Event '{event_l}' has a shorter duration compared to '{event_r}'.",
            "'{event_l}' extends over a shorter time span than '{event_r}'",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "'{event_l}' has a shorter duration compared to '{event_r}'. So '{event_l}' must be part of '{event_r}'. Only relations that indicate one event is part of another are f, d, s.",
        }
    else:
        return None


def no_meeting(rel):
    if rel in ["p", "P"]:
        choice = [
            "There exists no temporal point of coincidence between '{event_l}' and '{event_r}' whatsoever.",
            "Events '{event_l}' and '{event_r}' do not meet at any time",
            "At no time do events '{event_l}' and '{event_r}' coincide",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "There is no temporal point of coincidence between '{event_l}' and '{event_r}'. So '{event_l}' and '{event_r}' do not meet at any time which excludes relationship m,M.",
        }
    else:
        return None


def no_overlap(rel):
    if rel in ["p", "P", "m", "M"]:
        choice = [
            "There is no overlap between '{event_l}' and '{event_r}'",
            "'{event_l}' and '{event_r}' do not overlap in time",
            "No temporal overlap exists between events '{event_l}' and '{event_r}'",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "There is no temporal overlap between '{event_l}' and '{event_r}'. So '{event_l}' and '{event_r}' do not overlap in time which excludes relationships o,O,f,F,d,D,s,S,e and so on.",
        }
    else:
        return None


def overlaps(rel):
    if rel in ["o", "O", "F", "f", "D", "d", "s", "S", "e"]:
        choice = [
            "Events '{event_l}' and '{event_r}' overlap in time",
            "There is a temporal overlap between events '{event_l}' and '{event_r}'",
            "During a period of time, both '{event_l}' and '{event_r}' were active.",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can know '{event_l}' and '{event_r}' overlap in time which excludes relationships p,P,m,M.",
        }
    else:
        return None


def only_follow(rel):
    if rel in ["m", "M"]:
        choice = [
            "'{event_l}' and '{event_r}' are seamlessly connected at this temporal point(And we don't know which one starts first).",
            "'{event_l}' and '{event_r}' seamlessly transition at a single point in time(And we don't know which one starts first).",
            "'{event_l}' and '{event_r}' are like day and night: connected but not overlapping.(We don't know which one starts first.)",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can observe that '{event_l}' and '{event_r}' are seamlessly connected which indicates that they are related by the 'meet' relationship (m or M).",
        }
    else:
        return None


def start_before(rel):
    if rel in ["p", "m", "o", "F", "D"]:
        choice = [
            "'{event_l}' starts before'{event_r}'",
            "'{event_l}' triggers earlier than '{event_r}'(Only related to the start time. Not the whole event)",
            "'{event_l}' begins earlier than '{event_r}'(Only related to the start time. Not the whole event).",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can know the start time of '{event_l}' is before the start time of '{event_r}'.",
        }
    else:
        return None


def start_after(rel):
    if rel in ["P", "M", "O", "f", "d"]:
        choice = [
            "'{event_l}' starts after '{event_r}'",
            "'{event_l}' triggers later than '{event_r}'(Only related to the start time. Not the whole event)",
            "'{event_l}' begins later than '{event_r}'(Only related to the start time. Not the whole event).",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can know the start time of '{event_l}' is after the start time of '{event_r}'.",
        }
    else:
        return None


def ends_before(rel):
    if rel in ["p", "m", "o", "s", "d"]:
        choices = [
            "'{event_l}' ends before '{event_r}' ends.",
            "'{event_l}' concludes prior to the conclusion of '{event_r}'.",
            "'{event_l}' finishes earlier than '{event_r}'.",
        ]
        return {
            "hint": random.choice(choices),
            "explanation": "We can know the end time of '{event_l}' is before the end time of '{event_r}'.",
        }
    else:
        return None


def ends_after(rel):
    if rel in ["P", "M", "O", "S", "D"]:
        choices = [
            "'{event_l}' ends after '{event_r}' ends.",
            "'{event_l}' concludes after the conclusion of '{event_r}'.",
            "'{event_l}' finishes later than '{event_r}'.",
        ]
        return {
            "hint": random.choice(choices),
            "explanation": "We can know the end time of '{event_l}' is after the end time of '{event_r}'.",
        }
    else:
        return None


def equals(rel):
    if rel == "e":
        choice = [
            "'{event_l}' does not start before or after '{event_r}', nor does it end before or after it.",
            "'{event_l}' and '{event_r}' have the same duration and begin simultaneously",
            "'{event_l}' and '{event_r}' have the same duration and end simultaneously",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "It is clear that '{event_l}' equals '{event_r}'.",
        }
    else:
        return None


def starts(rel):
    if rel in ["s", "S", "e"]:
        choice = [
            "'{event_l}' starts when '{event_r}' starts.",
            "'{event_l}' begins at the same time as '{event_r}'.",
            "'{event_l}' and '{event_r}' share the same starting point.",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can know '{event_l}' starts at the same time as '{event_r}'.",
        }
    else:
        return None


def ends(rel):
    if rel in ["F", "f", "e"]:
        choice = [
            "'{event_l}' ends when '{event_r}' ends.",
            "'{event_l}' concludes at the same time as '{event_r}'.",
            "'{event_l}' and '{event_r}' share the same ending point.",
        ]
        return {
            "hint": random.choice(choice),
            "explanation": "We can know '{event_l}' ends at the same time as '{event_r}'.",
        }
    else:
        return None


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


def _attribute_to_func(rel: str, attr: str):
    if attr == "start":
        start_val = RELATION_DEFINITIONS[rel]["start"]
        if start_val == StartTime.BEFORE:
            return start_before
        if start_val == StartTime.AFTER:
            return start_after
        return starts
    if attr == "end":
        end_val = RELATION_DEFINITIONS[rel]["end"]
        if end_val == EndTime.BEFORE:
            return ends_before
        if end_val == EndTime.AFTER:
            return ends_after
        return ends
    if attr == "overlap":
        overlap_val = RELATION_DEFINITIONS[rel]["overlap"]
        return overlaps if overlap_val == Overlap.YES else no_overlap
    if attr == "duration":
        duration_val = RELATION_DEFINITIONS[rel]["duration"]
        if duration_val == Duration.LONGER:
            return longer_than
        if duration_val == Duration.SHORTER:
            return shorter_than
        if duration_val == Duration.EQUAL:
            return equals
        return no_determine_length
    if attr == "meet":
        meet_val = RELATION_DEFINITIONS[rel]["meet"]
        return only_follow if meet_val == Meet.YES else no_meeting
    return None


def get_core_attributes(rel: str):
    return RELATION_CORE_ATTRS.get(rel, ATTRIBUTE_ORDER)


def build_attribute_hint(rel: str, attr: str, events: list, l_no: int, r_no: int):
    func = _attribute_to_func(rel, attr)
    if func is None:
        return None
    info = func(rel)
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
