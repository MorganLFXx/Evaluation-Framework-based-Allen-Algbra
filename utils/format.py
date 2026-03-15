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
    {\n    "answer_single": "finishes",\n    "thinking": "hint1: \'P\' starts at the same time as  the same time as \'G\'. Letntains\'. If it asks for B to P, it is \'during\'. The question asks for the relationship between \'P0\' and \'B1\'. Usually, this implies the relation of the first argument to the second. So P0 contains B1. The abbreviation is \'contains\'.\\n\\nLet\'s verify the \'finishes\' definition again. \'A finishes B\' means A and B end at the same time but A starts after B. Here P starts before B. So P does not finish B. B finishes P? B starts after P starts, B ends at same time as P. So B finishes P. The relation of B to P is \'finishes\'. The relation of P to B is \'finished_by\'.\\n\\nWait, I need to be careful with the direction. The question asks for the relationship between \'P0\' and \'B1\'. This usually means "\t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t  \t\t\t\t\t\t\t\t\t """
    processed = parse_json_block(test_input)
    print(processed)
    print("Answer:" + processed.get("answer_single", ""))
    print("Thinking:" + processed.get("thinking", ""))


if __name__ == "__main__":
    main()
