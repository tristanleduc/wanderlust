"""Conservative OSM ``opening_hours`` evaluation — open / closed / unknown.

The OSM opening-hours grammar is large; this parses only the unambiguous,
overwhelmingly common patterns and returns ``None`` (unknown) for everything
else — the app must never demote a place on a misread rule. Handled:

  24/7 · "Mo-Fr 08:00-18:00" · day lists "Mo,We,Fr" · ranges across multiple
  rules "Tu-Su 09:00-18:00; Mo off" · several time spans "09:00-12:00,14:00-18:00"
  · plain daily times "10:00-19:00" · overnight spans "18:00-02:00" · "off"/"closed"

Abstained: PH/SH (holidays), sunrise/sunset, months/weeks, "+" open-ends, etc.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")

_DAYS = ["mo", "tu", "we", "th", "fr", "sa", "su"]
_DAY_RE = r"(?:mo|tu|we|th|fr|sa|su)"
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
# tokens that mean "too complex — abstain". PH/SH (public/school holidays) are
# NOT here: holiday rules are dropped per-rule instead, since the regular-day
# part of "Mo-Fr 08:00-18:00; PH off" is perfectly decidable.
_ABSTAIN = re.compile(
    r"sunrise|sunset|dawn|dusk|week|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|easter|\+|\|\|"
)


def _parse_days(spec: str) -> set[int] | None:
    """'mo-fr' / 'mo,we,fr' / 'tu-su,mo' -> weekday indices, or None if invalid.

    PH/SH tokens inside a list ("PH,Sa,Su 10:00-18:00") are ignored: they extend
    the rule to holidays, which doesn't change what regular weekdays it covers.
    """
    days: set[int] = set()
    saw_any = False
    for part in spec.split(","):
        part = part.strip()
        if part in ("ph", "sh"):
            continue
        m = re.fullmatch(rf"({_DAY_RE})\s*-\s*({_DAY_RE})", part)
        if m:
            a, b = _DAYS.index(m.group(1)), _DAYS.index(m.group(2))
            if a <= b:
                days.update(range(a, b + 1))
            else:  # wrapping range, e.g. fr-mo
                days.update(list(range(a, 7)) + list(range(0, b + 1)))
            saw_any = True
            continue
        if re.fullmatch(_DAY_RE, part):
            days.add(_DAYS.index(part))
            saw_any = True
            continue
        return None
    return days if saw_any else set()


def _parse_spans(spec: str) -> list[tuple[int, int]] | None:
    """'09:00-12:00,14:00-18:00' -> [(540,720),(840,1080)] minutes, or None."""
    spans: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", part)
        if not m:
            return None
        h1, m1 = map(int, m.group(1).split(":"))
        h2, m2 = map(int, m.group(2).split(":"))
        if not (0 <= h1 <= 24 and 0 <= h2 <= 24 and m1 < 60 and m2 < 60):
            return None
        spans.append((h1 * 60 + m1, h2 * 60 + m2))
    return spans


def is_open(opening_hours: str | None, when: datetime | None = None) -> bool | None:
    """True/False if confidently determinable for ``when`` (Paris time); else None."""
    if not opening_hours or not str(opening_hours).strip():
        return None
    text = " ".join(str(opening_hours).lower().split())
    if text in ("24/7", "24/7;"):
        return True
    if _ABSTAIN.search(text):
        return None

    when = when or datetime.now(PARIS_TZ)
    if when.tzinfo is None:
        when = when.replace(tzinfo=PARIS_TZ)
    weekday = when.weekday()
    minute = when.hour * 60 + when.minute
    # for overnight spans we also need "yesterday evening" rules
    yesterday = (weekday - 1) % 7

    decided: bool | None = None
    matched_any_rule = False
    day_head_re = re.compile(rf"^(?:(?:{_DAY_RE}|ph|sh)(?:\s*-\s*(?:{_DAY_RE}|ph|sh))?)"
                             rf"(?:,(?:{_DAY_RE}|ph|sh)(?:\s*-\s*(?:{_DAY_RE}|ph|sh))?)*$")
    for rule in text.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        head, _, tail = rule.partition(" ")
        if day_head_re.fullmatch(head):
            day_spec, rest = head, tail.strip()
        else:
            day_spec, rest = None, rule
        days = _parse_days(day_spec.replace(" ", "")) if day_spec else set(range(7))
        if days is None:
            return None  # unparseable day spec -> abstain entirely
        if not days:
            continue  # holiday-only rule (e.g. "PH off") -> no weekday effect

        if rest in ("off", "closed"):
            if weekday in days:
                decided = False
                matched_any_rule = True
            continue
        spans = _parse_spans(rest)
        if spans is None:
            return None  # unparseable times -> abstain entirely

        matched_any_rule = True
        for lo, hi in spans:
            if hi >= lo:  # same-day span
                if weekday in days and lo <= minute < hi:
                    decided = True
            else:  # overnight span, e.g. 18:00-02:00
                if weekday in days and minute >= lo:
                    decided = True
                if yesterday in days and minute < hi:
                    decided = True

    if decided is True:
        return True
    # only claim "closed" when at least one rule parsed and applies to this place
    return False if matched_any_rule else None


# Demotion factors when a place is closed at plan time: stopping at a closed
# café is pointless (heavy demotion); passing a closed monument still has
# exterior value (mild demotion). Unknown hours are left untouched — except for
# typically-daytime categories late at night, which get a mild realism demotion
# (a café with unlisted hours is a poor bet at midnight).
CLOSED_STOP_FACTOR = 0.2
CLOSED_PASS_FACTOR = 0.7
NIGHT_UNKNOWN_FACTOR = 0.5
_NIGHT_START_H, _NIGHT_END_H = 21, 6
_DAYTIME_CATEGORIES = {
    "cafe", "bakery_food_shop", "market", "museum_gallery", "library",
    "bookshop", "specialty_shop",
}


def apply_open_now(pois: list, posture: dict[str, str] | None,
                   when: datetime | None = None) -> list:
    """Annotate each POI with ``.open_state`` and demote closed ones in place."""
    posture = posture or {}
    when = when or datetime.now(PARIS_TZ)
    is_night = when.hour >= _NIGHT_START_H or when.hour < _NIGHT_END_H
    for p in pois:
        state = is_open(getattr(p, "opening_hours", None), when)
        p.open_state = state  # True / False / None(unknown)
        if state is False:
            factor = (CLOSED_STOP_FACTOR
                      if posture.get(p.category, "pass") == "stop"
                      else CLOSED_PASS_FACTOR)
            p.score *= factor
        elif state is None and is_night and p.category in _DAYTIME_CATEGORIES:
            p.score *= NIGHT_UNKNOWN_FACTOR
    return pois
