from hint import *
import hint
from utils.relation import allen_relations


def get_negation(rel: str, l_no: int, r_no: int, events: list) -> list:
    hints = []
    event_l = events[l_no]
    event_r = events[r_no]

    hints.append(
        f"It is not true that '{event_l}' {allen_relations[rel]} '{event_r}' ."
    )
    return hints


def get_easy_hint(rel: str, l_no: int, r_no: int, events: list) -> list:
    """Generate hints based on relation and event numbers"""
    event_l = events[l_no]
    event_r = events[r_no]
    template = random.choice(HINT_TEMPLATES[rel])
    hint = template.format(event_l=event_l, l_no=l_no, event_r=event_r, r_no=r_no)
    return hint


def generate_neg_hints(path, events):
    """提供直接否定提示"""
    neg_hints = []
    for rel in path["excluded"]:
        l_no = path["base_event"][0]
        r_no = path["base_event"][1]
        neg_hints.extend(get_negation(rel, l_no, r_no, events))
    return neg_hints


def generate_indirect_neg_hints(path, events):
    """
    提供间接否定提示
    要求：尽可能快速地提供应被排除关系path["excluded"]不成立的特征
    return: list of hints
    """
    hints = []
    seen_attrs = set()
    target_rel = path["target"]
    l_no = path["base_event"][0]
    r_no = path["base_event"][1]

    for rel in path["excluded"]:
        attrs = hint.pick_discriminating_attributes(target_rel, rel)
        for attr in attrs:
            if attr in seen_attrs:
                continue
            hint_text = hint.build_attribute_hint(target_rel, attr, events, l_no, r_no)
            if hint_text:
                seen_attrs.add(attr)
                hints.append(hint_text)
    return hints


def generate_indirect_evidence(path, events):
    """
    提供间接肯定提示
    要求：尽可能快速地提供体现目标关系`path["target"]`成立的特征
    return: list of hints
    """
    hints = []
    target_rel = path["target"]
    l_no = path["base_event"][0]
    r_no = path["base_event"][1]

    def _select_attrs(target_rel, excluded_rels):
        core_attrs = hint.get_core_attributes(target_rel)
        if len(excluded_rels) == 0:
            return core_attrs

        target_def = hint.RELATION_DEFINITIONS[target_rel]
        remaining = set(excluded_rels)
        selected = []

        def differs(rel, attr):
            return hint.RELATION_DEFINITIONS[rel][attr] != target_def[attr]

        while remaining and len(selected) < len(core_attrs):
            best_attr = None
            best_removed = set()
            for attr in core_attrs:
                if attr in selected:
                    continue
                removed = {rel for rel in remaining if differs(rel, attr)}
                if len(removed) > len(best_removed):
                    best_removed = removed
                    best_attr = attr
            if not best_attr or not best_removed:
                break
            selected.append(best_attr)
            remaining -= best_removed

        if remaining:
            return core_attrs
        return selected

    attrs = _select_attrs(target_rel, path.get("excluded", []))
    for attr in attrs:
        hint_text = hint.build_attribute_hint(target_rel, attr, events, l_no, r_no)
        if hint_text:
            hints.append(hint_text)
    return hints


def generate_hint(path, events, hint_type):
    hints = []
    # composition
    if path["left"] == -1:
        hints.append(
            get_easy_hint(
                path["path"][0], path["base_event"][0], path["new_event"], events
            )
        )
    if path["right"] == -1:
        hints.append(
            get_easy_hint(
                path["path"][1], path["new_event"], path["base_event"][1], events
            )
        )

    # exclude
    if hint_type == "direct neg":
        hints.extend(generate_neg_hints(path, events))
    elif hint_type == "indirect neg":
        hints.extend(generate_indirect_neg_hints(path, events))
    elif hint_type == "indirect pos":
        hints.extend(generate_indirect_evidence(path, events))
    return hints


# "direct neg", "indirect neg", "indirect pos"
def generate_hints(paths, events, hint_type="direct neg"):
    hints = []
    for p in paths:
        p_hints = generate_hint(p, events, hint_type)
        hints.extend(p_hints)
    return hints


def main():
    path = {
        "target": "s",
        "path": ["s", "D"],
        "excluded": ["d", "D"],
        "parent": -1,
        "left": 2,
        "right": 1,
        "base_event": [0, 1],
        "new_event": 2,
    }

    hints = generate_hint(path, ["A", "B", "C", "D"], "indirect pos")
    print(hints)


if __name__ == "__main__":
    main()
