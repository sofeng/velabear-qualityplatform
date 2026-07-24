import re


REQUIREMENT_KEY_PATTERN = re.compile(r'(?P<requirement_key>[A-Z]+-\d+)', re.IGNORECASE)
REQUIREMENT_BOUNDARY_CHARS = '[]()（）【】 \t\r\n-_:：'


def split_requirement_identifier_and_title(raw_title: str) -> tuple[str, str]:
    """Split a requirement title into its identifier and display title.

    Supports both "需求编号 + 需求标题" and "需求标题 + 需求编号".
    """
    normalized = str(raw_title or '').strip()
    if not normalized:
        return '', ''

    match = REQUIREMENT_KEY_PATTERN.search(normalized)
    if not match:
        return '', normalized

    requirement_key = match.group('requirement_key').strip().upper()
    prefix = normalized[:match.start()].rstrip(REQUIREMENT_BOUNDARY_CHARS).strip()
    suffix = normalized[match.end():].lstrip(REQUIREMENT_BOUNDARY_CHARS).strip()

    if prefix and suffix:
        requirement_title = f'{prefix} {suffix}'
    else:
        requirement_title = prefix or suffix

    return requirement_key, requirement_title
