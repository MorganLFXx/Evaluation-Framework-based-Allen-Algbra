from typing import Dict, Optional
import json
import re


def parse_json_block(text: str) -> Optional[Dict]:
    """Try to parse a JSON object from raw model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
