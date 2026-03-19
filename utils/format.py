from typing import Dict, Optional
import json
import re


def parse_json_block(text: str) -> Optional[Dict]:
    """Try to parse a JSON object from raw model output."""
    # 消除文本中重复多次(4+)出现的无意义空白符
    text = re.sub(r"\s{4,}", "", text)
    try:
        if not text.endswith("}"):
            #  Addressing the issue of overthinking and truncation in small models
            if text.endswith("\\"):
                text += "\\"
            if not text.endswith('"'):
                text += '"'
            text += "}'"
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
    {\n    "thinking": "hint1: \'M0\' starts eets Q1.",\n    "answer_single": "m"\n}"""
    processed = parse_json_block(test_input)
    print(processed)
    print("Answer:" + processed.get("answer_single", ""))
    print("Thinking:" + processed.get("thinking", ""))


if __name__ == "__main__":
    main()
