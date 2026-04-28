from typing import Dict, Optional
import json
import re


def parse_json_block(text: str) -> Optional[Dict]:
    """Try to parse a JSON object from raw model output."""
    # 消除文本中重复多次(4+)出现的无意义空白符
    text = re.sub(r"\s{4,}", "", text)
    # text = text.strip()
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
    test_input = "{\n    \"thinking\": \"1. Hint Interpretation Phase: \\n- Hint 1 states 'O0' starts when 'C1' starts (Start(O0) = Start(C1)).\\n- Hint 2 states 'O0' finishes earlier than 'C1' (End(O0) < End(C1)). Combined, this implies O0 is during C1 (O0 d C1).\\n- Hint 154 states 'O0' starts at the same time as 'C1' (Start(O0) = Start(C1)) but ends later (End(O0) > End(C1)). This implies C0 finishes C1 (O0 f C1).\\n- Other hints establish a complex timeline (e.g., H5 ends before V17 starts in Hint 27; I9 starts after H5 in Hint 28; I9 and H5 have no overlap in Hint 29/30), but the direct contradiction is found between hints describing the exact same pair of events (O0 and C1) with mutually exclusive end-time relationships.\\n\\n2. Reasoning Phase:\\n- Compare Hint 2 and Hint 154 directly.\\n- Hint 2: 'O0' finishes earlier than 'C1'. This means End(O0) < End(C1).\\n- Hint 154: 'O0' ... ends later [than C1]. This means End(O0) > End(C1).\\n- It is logically impossible for 'O0' to end both earlier than and later than 'C1' if they start at the same time (which both hints 1 and 154 agree on).\\n- Therefore, Hint 154 directly contradicts the combination of Hint 1 and Hint 2 (specifically Hint 2 regarding the end time). Since the prompt asks for the hint where the conflict is confirmed, and Hint 154 provides the statement that clashes with the previously established fact in Hint 2, Hint 154 is the source of the conflict.\",\n    \"answer_single\": 154\n}"
    processed = parse_json_block(test_input)
    print(processed)
    print("Answer:", processed.get("answer_single", ""))
    print("Thinking:", processed.get("thinking", ""))


if __name__ == "__main__":
    main()
