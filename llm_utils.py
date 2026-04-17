import re
import json
from typing import List, Dict, Any

def parse_xml_tool_calls(text: str) -> List[Dict[str, Any]]:
    tool_calls = []
    pattern = r"<tool_call>(.*?)</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        try:
            call = json.loads(match.strip())
            tool_calls.append(call)
        except json.JSONDecodeError:
            continue
    return tool_calls
