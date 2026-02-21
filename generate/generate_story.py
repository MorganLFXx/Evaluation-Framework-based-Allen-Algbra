import argparse
import json
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from utils.chat import call_api
from utils.format import parse_json_block


SYSTEM_PROMPT = (
    "You are a professional workflow assistant for story generation. "
    "Generate a coherent narrative that allows readers to infer Allen interval relations. "
    "The story must follow constraints and embed all hints implicitly. "
    "Events within the same story should adhere to a unified narrative framework."
    "Return only JSON as instructed, no analysis."
)

VALIDATOR_PROMPT = (
    "You are an expert in Allen interval algebra. "
    "Given a story and event list, infer the temporal relation between specified pairs. "
    "Return ONLY JSON with the required fields."
)

HINT_VALIDATOR_PROMPT = (
    "You are a careful semantic validator. "
    "Given a story and a list of hints, decide which hints are semantically covered "
    "by the story (paraphrase allowed). Return ONLY JSON with required fields."
)

TEMPORAL_KEYWORDS = {
    "before",
    "after",
    "start",
    "started",
    "begin",
    "began",
    "end",
    "ended",
    "finish",
    "finished",
    "overlap",
    "during",
    "contain",
    "contains",
    "meet",
    "met",
    "same time",
}

MAX_PATH_ERRORS_IF_TARGET_OK = 2


def build_edges(sample: Dict) -> List[Tuple[int, int, str]]:
    edges: List[Tuple[int, int, str]] = []
    for path in sample.get("paths", []):
        if path.get("left", -1) == -1:
            l_no, r_no = path["base_event"][0], path["new_event"]
            edges.append((l_no, r_no, path["path"][0]))
        if path.get("right", -1) == -1:
            l_no, r_no = path["new_event"], path["base_event"][1]
            edges.append((l_no, r_no, path["path"][1]))
    return edges


def constraints_text(sample: Dict) -> str:
    events = sample.get("events", [])
    lines = []
    for l_no, r_no, rel in build_edges(sample):
        lines.append(
            f"- Relation: {events[l_no]}(index {l_no}) -> "
            f"{events[r_no]}(index {r_no}) is '{rel}'."
        )
    for path in sample.get("paths", []):
        excluded = path.get("excluded", [])
        if excluded:
            l_no, r_no = path["base_event"]
            lines.append(
                f"- Excluded between {events[l_no]}(index {l_no}) and "
                f"{events[r_no]}(index {r_no}): {', '.join(excluded)}."
            )
    return "\n".join(lines) if lines else "- No explicit constraints provided."


def event_list_text(event_source: Dict) -> str:
    if "events" in event_source:
        events = event_source.get("events", [])
        return "\n".join(f"- {i}: {name}" for i, name in enumerate(events))
    event_map = event_source
    size = len(event_map)
    events = [event_map.get(str(i), f"Event {i}") for i in range(size)]
    return "\n".join(f"- {i}: {name}" for i, name in enumerate(events))


def hints_text(sample: Dict) -> str:
    hints = sample.get("hints", [])
    if not hints:
        return "- (none)"
    return "\n".join(f"- {h}" for h in hints)


def build_user_prompt(sample: Dict) -> str:
    target = sample.get("target", {})
    target_desc = (
        f"Target relation between index {target.get('l')} and {target.get('r')} "
        f"is '{target.get('rel')}'."
    )
    return (
        "Please generate a complete story that implies the target relation and all constraints.\n"
        "Requirements:\n"
        "1. The story must respect all path constraints.\n"
        "2. The story must implicitly cover all hints (paraphrase allowed).\n"
        "3. The story must mention every event at least once, but you may rename events.\n"
        "4. Output ONLY JSON with fields: \n"
        "   {\n"
        '     "story": string,\n'
        '     "event_name_map": {"0": string, "1": string, ...},\n'
        '     "target_event_names": {"l": string, "r": string}\n'
        "   }\n\n"
        "Events (original names):\n"
        f"{event_list_text(sample)}\n\n"
        f"{target_desc}\n\n"
        "Constraints from paths:\n"
        f"{constraints_text(sample)}\n\n"
        "Hints to embed:\n"
        f"{hints_text(sample)}\n"
    )


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def covers_hints(text: str, hints: Sequence[str]) -> bool:
    if not hints:
        return True
    normalized = normalize_text(text)
    for hint_text in hints:
        hint_normalized = normalize_text(hint_text)
        tokens = [t for t in hint_normalized.split() if t not in {"'", '"'}]
        event_tokens = [t for t in tokens if t.isalpha()]
        if not any(token in normalized for token in event_tokens):
            return False
        if not any(keyword in normalized for keyword in TEMPORAL_KEYWORDS):
            return False
    return True


def validate_target(story: str, event_map: Dict, sample: Dict, model) -> List[str]:
    target = sample.get("target", {})
    target_desc = (
        f"{target.get('l')} -> {target.get('r')} should be '{target.get('rel')}'."
    )
    prompt = (
        "Story:\n"
        f"{story}\n\n"
        "Events (index: name):\n"
        f"{event_list_text(event_map)}\n\n"
        "Target relation requirement:\n"
        f"{target_desc}\n\n"
        "Return JSON with fields:\n"
        "{\n"
        '  "target": {"l": int, "r": int, "rel": '
        '"p|P|m|M|o|O|f|F|s|S|d|D|e"}\n'
        "}\n"
    )
    messages = [
        {"role": "system", "content": VALIDATOR_PROMPT},
        {"role": "user", "content": prompt},
    ]
    raw = call_api(messages, model)
    data = parse_json_block(raw)
    if not data:
        return ["Validator did not return valid JSON."]

    expected_target = target.get("rel")
    target_obj = data.get("target", {}) if isinstance(data, dict) else {}
    if target_obj.get("rel") != expected_target:
        return ["Target relation mismatch in generated story."]
    return []


def validate_story(story: str, event_map: Dict, sample: Dict, model) -> List[str]:
    errors = []
    errors.extend(validate_target(story, event_map, sample, model))
    target_check = True if errors == [] else False
    if not target_check:
        return errors
    # hints coverage check
    errors.extend(validate_hints(story, event_map, sample, model))
    # Strict relation examinations
    path_errors = validate_relations(story, event_map, sample, model)
    if len(path_errors) > MAX_PATH_ERRORS_IF_TARGET_OK:
        errors.extend(path_errors)
    return errors


def validate_relations(
    story: str, event_map: Dict, sample: Dict, model: str
) -> List[str]:
    """Validate path relations using LLM-based extraction."""
    edges = build_edges(sample)

    edge_desc = "\n".join(
        f"- {l_no} -> {r_no} expected '{rel}'." for l_no, r_no, rel in edges
    )

    prompt = (
        "Story:\n"
        f"{story}\n\n"
        "Events (index: name):\n"
        f"{event_list_text(event_map)}\n\n"
        "Path relations to verify:\n"
        f"{edge_desc}\n\n"
        "Return JSON with fields:\n"
        "{\n"
        '  "paths": [\n'
        '    {"l": int, "r": int, "rel": '
        '"p|P|m|M|o|O|f|F|s|S|d|D|e"}\n'
        "  ]\n"
        "}\n"
    )

    messages = [
        {"role": "system", "content": VALIDATOR_PROMPT},
        {"role": "user", "content": prompt},
    ]
    raw = call_api(messages, model)
    data = parse_json_block(raw)
    if not data:
        return ["Validator did not return valid JSON."]

    errors = []
    expected_edges = {(l, r): rel for l, r, rel in edges}
    for item in data.get("paths", []) if isinstance(data, dict) else []:
        key = (item.get("l"), item.get("r"))
        if key in expected_edges and item.get("rel") != expected_edges[key]:
            errors.append(f"Path relation mismatch for {key[0]}->{key[1]}.")

    missing = [
        key
        for key in expected_edges
        if key not in {(p.get("l"), p.get("r")) for p in data.get("paths", [])}
    ]
    for key in missing:
        errors.append(f"Path relation missing for {key[0]}->{key[1]}.")

    return errors


def validate_hints(story: str, event_map: Dict, sample: Dict, model: str) -> List[str]:
    hints = sample.get("hints", [])
    if not hints:
        return []

    prompt = (
        "Story:\n"
        f"{story}\n\n"
        "Events (index: name):\n"
        f"{event_list_text(event_map)}\n\n"
        "Hints to verify (paraphrase allowed):\n"
        + "\n".join(f"- ({i}) {h}" for i, h in enumerate(hints))
        + "\n\n"
        "Return JSON with fields:\n"
        "{\n"
        '  "covered": [bool, ...],\n'
        '  "missing": [int, ...]\n'
        "}\n"
    )

    messages = [
        {"role": "system", "content": HINT_VALIDATOR_PROMPT},
        {"role": "user", "content": prompt},
    ]
    raw = call_api(messages, model)
    data = parse_json_block(raw)
    if not data:
        return ["Hint validator did not return valid JSON."]

    missing = data.get("missing", []) if isinstance(data, dict) else []
    if not isinstance(missing, list):
        return ["Hint validator returned invalid format."]
    errors = [f"Hint not covered: {idx}." for idx in missing]
    return errors


def refine_prompt(base_prompt: str, errors: Sequence[str]) -> str:
    issues = "\n".join(f"- {err}" for err in errors)
    return (
        base_prompt
        + "\nThe previous story failed validation:\n"
        + issues
        + "\nPlease regenerate the story and fix these issues."
    )


def generate_story(
    sample: Dict,
    model: str,
    max_retries: int = 1,
) -> Dict:
    prompt = build_user_prompt(sample)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    raw = call_api(messages, model)
    data = parse_json_block(raw)
    if not data or "story" not in data:
        story = raw
        data = {"story": story, "event_name_map": {}}
    story = data.get("story", "")
    event_map = data.get("event_name_map", {})

    # after-llm check and retry
    errors = validate_story(story, event_map, sample, model)
    retry_count = 0
    # debug
    print(f"errors after generation: {errors}")
    while errors and retry_count < max_retries:
        retry_count += 1
        refined_prompt = refine_prompt(prompt, errors)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": refined_prompt},
        ]
        raw = call_api(messages, model)
        data = parse_json_block(raw)
        if not data or "story" not in data:
            story = raw
            data = {"story": story, "event_name_map": {}}
        story = data.get("story", "")
        event_map = data.get("event_name_map", {})
        errors = validate_story(story, event_map, sample, model)
        # debug
        print(f"Retry {retry_count}, errors: {errors}")

    return {"story": story, "event_name_map": event_map}


def generate_stories(
    samples: Sequence[Dict],
    model: str,
    max_retries: int = 1,
) -> List[Dict]:
    res = []
    for sample in samples:
        print(f"Generating story for sample {sample.get('id', 'unknown')}")
        res.append(generate_story(sample, model=model, max_retries=max_retries))
    return res


def main():
    parser = argparse.ArgumentParser(description="Generate stories for samples")
    parser.add_argument("--path", required=True, help="Input JSON file path")
    parser.add_argument(
        "--model", required=True, default="deepseek-v3.2", help="Model name for LLM"
    )
    parser.add_argument("--retries", type=int, default=2, help="Max retries per sample")
    args = parser.parse_args()

    with open(f"datasets/{args.path}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    results = generate_stories(data, model=args.model, max_retries=args.retries)
    for sample, result in zip(data, results):
        sample["story"] = result.get("story")
        event_name_map = result.get("event_name_map")
        for i in range(len(sample.get("events", []))):
            sample["events"][i] = event_name_map.get(str(i), sample["events"][i])

    with open(f"datasets/{args.path}_story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
