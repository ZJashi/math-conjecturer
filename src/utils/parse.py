import json
import re


def try_parse(raw: str) -> dict | None:
    # Try as-is first, then escape lone backslashes (common when model writes LaTeX)
    for transform in [
        lambda s: s,
        lambda s: re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s),
    ]:
        try:
            return json.loads(transform(raw))
        except json.JSONDecodeError:
            pass
    return None


def extract_json(text: str) -> dict | None:
    for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```", r"(\{[\s\S]*\})"]:
        m = re.search(pattern, text)
        if m:
            raw = m.group(1) if "```" in pattern else m.group(0)
            result = try_parse(raw)
            if result:
                return result
    return None