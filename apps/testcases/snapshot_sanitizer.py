import re


PRIVATE_USE_CHAR_RE = re.compile('[\ue000-\uf8ff\U000F0000-\U000FFFFD\U00100000-\U0010FFFD]')
INLINE_SPACE_RE = re.compile(r'[ \t\f\v]+')
QUOTED_TEXT_RE = re.compile(r'"([^"\n]*)"')
COLON_SCALAR_LINE_RE = re.compile(r'^(\s*-\s+[A-Za-z0-9_-]+(?:\s+\[[^\]]+\])*\s*:\s*)(.*)$')
EMPTY_QUOTED_LINE_RE = re.compile(r'^(\s*-\s+[A-Za-z0-9_-]+)\s+""(\s*(?:\[[^\]]+\]\s*)*)$')
EMPTY_ICON_TEXT_LINE_RE = re.compile(r'^\s*-\s+(?:text|generic)(?:\s+""|\s+\[[^\]]+\])*\s*:?\s*$')

TEXT_LIKE_EVENT_KEYS = {
    'ariaLabel',
    'label',
    'linkText',
    'linktext',
    'name',
    'partialLinkText',
    'partiallinktext',
    'placeholder',
    'text',
    'title',
}


def remove_private_use_characters(value):
    if value is None:
        return ''
    return PRIVATE_USE_CHAR_RE.sub('', str(value))


def normalize_snapshot_inline_text(value):
    text = remove_private_use_characters(value)
    text = INLINE_SPACE_RE.sub(' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def sanitize_snapshot_line(line):
    cleaned = remove_private_use_characters(line)

    def clean_quoted(match):
        return f'"{normalize_snapshot_inline_text(match.group(1))}"'

    cleaned = QUOTED_TEXT_RE.sub(clean_quoted, cleaned)

    colon_match = COLON_SCALAR_LINE_RE.match(cleaned)
    if colon_match:
        scalar = colon_match.group(2)
        if scalar and not scalar.lstrip().startswith(('|', '>')):
            scalar = normalize_snapshot_inline_text(scalar)
            cleaned = f'{colon_match.group(1)}{scalar}' if scalar else colon_match.group(1).rstrip()

    empty_quote_match = EMPTY_QUOTED_LINE_RE.match(cleaned)
    if empty_quote_match:
        cleaned = f'{empty_quote_match.group(1)}{empty_quote_match.group(2)}'

    indent_width = len(cleaned) - len(cleaned.lstrip(' '))
    return cleaned[:indent_width] + INLINE_SPACE_RE.sub(' ', cleaned[indent_width:]).rstrip()


def line_indent(line):
    return len(line) - len(line.lstrip(' '))


def line_has_children(lines, index):
    current_indent = line_indent(lines[index])
    for next_line in lines[index + 1:]:
        if not next_line.strip():
            continue
        return line_indent(next_line) > current_indent
    return False


def sanitize_snapshot_content(content):
    if content is None:
        return ''

    raw_text = str(content).replace('\r\n', '\n').replace('\r', '\n')
    cleaned_lines = [sanitize_snapshot_line(line) for line in raw_text.split('\n')]
    result_lines = []

    for index, line in enumerate(cleaned_lines):
        if not line.strip():
            continue
        if EMPTY_ICON_TEXT_LINE_RE.match(line) and not line_has_children(cleaned_lines, index):
            continue
        result_lines.append(line)

    return '\n'.join(result_lines).rstrip() + '\n' if result_lines else ''


def sanitize_recording_payload(value, key=None, *, selector_object=False):
    if isinstance(value, dict):
        is_selector = {'type', 'value'}.issubset(set(value.keys()))
        return {
            item_key: sanitize_recording_payload(
                item_value,
                item_key,
                selector_object=is_selector,
            )
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize_recording_payload(item, key, selector_object=selector_object)
            for item in value
        ]

    if isinstance(value, str):
        if selector_object or key in TEXT_LIKE_EVENT_KEYS:
            return normalize_snapshot_inline_text(value)
        return remove_private_use_characters(value)

    return value
