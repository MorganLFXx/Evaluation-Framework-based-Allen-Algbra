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
        "After '{event_l}' had been underway for some time, Tom finally made up his mind to initiate '{event_r}'.",
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
    ],
    "M": [
        "'{event_l}' starts exactly when '{event_r}' ends.",
        "'{event_l}' commenced right as '{event_r}' wrapped up.",
    ],
    "o": [
        "'{event_l}' starts before '{event_r}' starts and ends after '{event_r}' starts but before '{event_r}' ends.",
        "'{event_l}' and '{event_r}' overlap in time. But '{event_l}' starts first.",
    ],
    "O": [
        "'{event_l}' starts after '{event_r}' starts but before it ends and ends after '{event_r}' ends.",
        "'{event_l}' and '{event_r}' overlap in time. But '{event_r}' starts first.",
    ],
    "F": [
        "'{event_l}' ends exactly when '{event_r}' ends, but starts before '{event_r}' starts.",
        "'{event_l}' finishes at the same time as '{event_l}' but began earlier.",
    ],
    "f": [
        "'{event_l}' starts after '{event_r}' starts and ends exactly when '{event_r}' ends."
        "'{event_l}' finishes at the same time as '{event_r}' but began earlier.",
    ],
    "D": [
        "'{event_l}' starts before '{event_r}' starts and ends after '{event_r}' ends."
        "During '{event_l}', '{event_r}' started and ended."
    ],
    "d": [
        "'{event_l}' starts after '{event_r}' starts and ends before '{event_r}' ends."
        "The duration of '{event_l}' is part of the duration of '{event_r}'."
    ],
    "s": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends before '{event_r}' ends."
        "'{event_l}' starts at the same time as '{event_r}' but ends later."
    ],
    "S": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends after '{event_r}' ends."
        "'{event_l}' starts at the same time as '{event_r}' but ends earlier."
    ],
    "e": [
        "'{event_l}' starts exactly when '{event_r}' starts and ends exactly when '{event_r}' ends."
        "'{event_l}' and '{event_r}' overlap completely in time."
    ],
}

"""
oFD, osd, DSO, dfO, pmo, OMP, Fef, seS
pmoFD, pmosd, DSOMP, dfOMP
full, concur
"""


def no_determine_length(rel):
    if rel not in ["F", "f", "D", "d", "s", "S", "e"]:
        choice = [
            "Cannot determine which event '{event_l}' or '{event_r}' lasts longer",
            "It is unclear which event '{event_l}' or '{event_r}' has a longer duration",
            "The lengths of events '{event_l}' and '{event_r}' cannot be compared definitively",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "fFdDsSe",
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
            "update_cur": "pPmMoOdfse",
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
            "update_cur": "pPmMoOFSDe",
        }
    else:
        return None


def no_meeting(rel):
    if rel in ["p", "P"]:
        choice = [
            "There is no point in time when both events '{event_l}' and '{event_r}' are occurring",
            "Events '{event_l}' and '{event_r}' do not meet at any time",
            "At no time do events '{event_l}' and '{event_r}' coincide",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "oOdDsSfFe",
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
            "update_cur": "oOdDsSfFe",
        }
    else:
        return None


def overlaps(rel):
    if rel in ["o", "O", "F", "f", "D", "d", "s", "S", "e"]:
        choice = [
            "Events '{event_l}' and '{event_r}' overlap in time",
            "There is a temporal overlap between events '{event_l}' and '{event_r}'",
            "At one point, both '{event_l}' and '{event_r}' were active.",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "pPmM",
        }
    else:
        return None


def only_follow(rel):
    if rel in ["m", "M"]:
        choice = [
            "Although '{event_l}' and '{event_r}' are not overlapping, they are sequential.",
            "'{event_l}' and '{event_r}' are like day and night: connected but not overlapping.",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "pPoOdDsSfFe",
        }
    else:
        return None


def happen_before(rel):
    if rel in ["p", "m", "o", "F", "D"]:
        choice = [
            "'{event_l}' happens before '{event_r}'",
            "'{event_l}' takes place prior to '{event_r}'",
            "'{event_l}' occurs earlier than '{event_r}'",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "PMOdsSfe",
        }
    else:
        return None


def happen_after(rel):
    if rel in ["P", "M", "O", "f", "d"]:
        choice = [
            "'{event_l}' happens after '{event_r}'",
            "'{event_l}' takes place later than '{event_r}'",
            "'{event_l}' occurs subsequent to '{event_r}'",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "pmoDsSFe",
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
            "update_cur": "PMODSfFe",
        }
    else:
        return None


def ends_after(rel):
    if rel in ["P", "M", "O", "S", "D"]:
        choices = [
            "'{event_l}' ends after '{event_r}' ends.",
            "'{event_l}' concludes subsequent to the conclusion of '{event_r}'.",
            "'{event_l}' finishes later than '{event_r}'.",
        ]
        return {
            "hint": random.choice(choices),
            "update_cur": "pmodsfFe",
        }
    else:
        return None


def equals(rel):
    if rel == "e":
        choice = [
            "'{event_l}' does not start before or after '{event_r}', nor does it end before or after it.",
            "'{event_l}' and '{event_r}' have the same duration and occur simultaneously"
            "'{event_l}' and '{event_r}' have the same duration and end simultaneously",
        ]
        return {
            "hint": random.choice(choice),
            "update_cur": "pPmMoOdDsSfF",
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
            "update_cur": "pPmMoOdDfF",
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
            "update_cur": "pPmMoOdDsS",
        }
    else:
        return None
