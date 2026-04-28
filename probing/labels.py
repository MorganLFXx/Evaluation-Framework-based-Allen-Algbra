from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


RelationTriple = Tuple[str, str, str]


@dataclass
class LabelBuildResult:
    positives: List[RelationTriple]
    negatives: List[RelationTriple]
    candidates: List[RelationTriple]
    label_map: Dict[RelationTriple, int]


def normalize_triples(triples: Sequence[RelationTriple]) -> List[RelationTriple]:
    """Deduplicate triples while preserving input order."""
    out: List[RelationTriple] = []
    seen = set()
    for tri in triples:
        if len(tri) != 3:
            continue
        key = (str(tri[0]), str(tri[1]), str(tri[2]))
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def build_key_relation_labels(
    whole_rels: Sequence[RelationTriple],
    key_rels: Sequence[RelationTriple],
) -> LabelBuildResult:
    """
    Build binary labels for probing:
    - key_rels -> positive (1)
    - whole_rels minus key_rels -> negative (0)
    """
    whole = normalize_triples(whole_rels)
    key = normalize_triples(key_rels)
    key_set = set(key)

    positives = [tri for tri in whole if tri in key_set]
    # Keep key rels that are not present in whole_rels as extra positives.
    for tri in key:
        if tri not in key_set:
            continue
        if tri not in positives:
            positives.append(tri)

    negatives = [tri for tri in whole if tri not in key_set]
    candidates = positives + negatives

    label_map: Dict[RelationTriple, int] = {}
    for tri in negatives:
        label_map[tri] = 0
    for tri in positives:
        label_map[tri] = 1

    return LabelBuildResult(
        positives=positives,
        negatives=negatives,
        candidates=candidates,
        label_map=label_map,
    )


def label_for_triple(
    triple: RelationTriple, label_map: Dict[RelationTriple, int]
) -> int:
    """Return binary label for a relation triple, defaulting to negative."""
    return int(label_map.get(triple, 0))
