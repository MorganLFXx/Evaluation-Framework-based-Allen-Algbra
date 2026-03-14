from typing import Dict, Optional
import json
import re


def parse_json_block(text: str) -> Optional[Dict]:
    """Try to parse a JSON object from raw model output."""
    try:
        if not text.endswith("}"):
            #  Addressing the issue of overthinking and truncation in small models
            text += "\"}'"
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def main():
    test_input = """
    '{\n    "answer_single": "I can not determine",\n    "thinking": "hint1: \'J\' finishes at the same time as \'K\' and began earlier. This establishes that J finishes at the same time as K (J finishes K), and J starts before K starts. This implies J overlaps K,"""
    processed = parse_json_block(test_input)
    print(processed)
    print(processed.get("answer_single", ""))
    print(processed.get("thinking", ""))


if __name__ == "__main__":
    main()
