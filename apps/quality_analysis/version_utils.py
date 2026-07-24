import re
from datetime import date


def normalize_jira_version(value):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if not text:
        return ''

    normalized = text.split('发版', 1)[0].strip()
    return normalized or text


def parse_jira_version_timeline_date(value):
    text = normalize_jira_version(value)
    if not text:
        return None

    patterns = (
        r'(?<!\d)(?P<year>\d{4})[-./](?P<month>\d{1,2})[-./](?P<day>\d{1,2})(?!\d)',
        r'(?<!\d)(?P<year>\d{2})[-./](?P<month>\d{1,2})[.-](?P<day>\d{1,2})(?!\d)',
        r'(?<!\d)(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})(?!\d)',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        year = int(match.group('year'))
        if year < 100:
            year += 2000
        try:
            return date(year, int(match.group('month')), int(match.group('day')))
        except ValueError:
            return None

    return None


def jira_version_timeline_sort_key(value, latest_time=None, fallback_time=None):
    parsed_date = parse_jira_version_timeline_date(value)
    normalized = normalize_jira_version(value) or str(value or '')
    if parsed_date:
        return (0, parsed_date, normalized)

    resolved_time = latest_time if latest_time is not None else fallback_time
    return (1, resolved_time is None, resolved_time, normalized)
