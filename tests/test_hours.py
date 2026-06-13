"""Open-now awareness: OSM opening_hours parsing + plan-time demotion."""
from __future__ import annotations

from datetime import datetime

from discoverroute.routing.hours import (PARIS_TZ, apply_open_now, is_open)

TUE_15H = datetime(2026, 6, 9, 15, 0, tzinfo=PARIS_TZ)   # Tuesday 15:00
TUE_23H = datetime(2026, 6, 9, 23, 30, tzinfo=PARIS_TZ)  # Tuesday 23:30
MON_15H = datetime(2026, 6, 8, 15, 0, tzinfo=PARIS_TZ)   # Monday 15:00
WED_01H = datetime(2026, 6, 10, 1, 0, tzinfo=PARIS_TZ)   # Wednesday 01:00


def test_always_open():
    assert is_open("24/7", TUE_15H) is True


def test_simple_weekday_range():
    assert is_open("Mo-Fr 08:00-18:00", TUE_15H) is True
    assert is_open("Mo-Fr 08:00-18:00", TUE_23H) is False


def test_multi_rule_with_off_day():
    spec = "Tu-Su 10:00-18:00; Mo off"
    assert is_open(spec, TUE_15H) is True
    assert is_open(spec, MON_15H) is False


def test_lunch_split_spans():
    spec = "Mo-Fr 09:00-12:00,14:00-18:00"
    assert is_open(spec, TUE_15H) is True
    assert is_open(spec, datetime(2026, 6, 9, 13, 0, tzinfo=PARIS_TZ)) is False


def test_daily_no_days():
    assert is_open("07:00-23:30", TUE_15H) is True


def test_overnight_span():
    spec = "Tu 18:00-02:00"
    assert is_open(spec, TUE_23H) is True
    assert is_open(spec, WED_01H) is True   # spills past midnight into Wednesday
    assert is_open(spec, TUE_15H) is False


def test_abstains_on_complex():
    assert is_open("sunrise-sunset", TUE_15H) is None
    assert is_open("Mar-Oct 08:00-20:00", TUE_15H) is None
    assert is_open(None, TUE_15H) is None
    assert is_open("", TUE_15H) is None


class P:
    def __init__(self, category, hours, score=1.0):
        self.category, self.opening_hours, self.score = category, hours, score


def test_demotion_by_posture():
    closed_cafe = P("cafe", "Mo-Fr 08:00-12:00")        # closed Tue 15:00
    closed_monument = P("monument_historic", "Mo-Fr 08:00-12:00")
    open_cafe = P("cafe", "Mo-Fr 08:00-18:00")
    unknown = P("cafe", None)
    posture = {"cafe": "stop", "monument_historic": "pass"}
    apply_open_now([closed_cafe, closed_monument, open_cafe, unknown],
                   posture, when=TUE_15H)
    assert closed_cafe.score == 0.2          # stop-at closed -> heavy demotion
    assert closed_monument.score == 0.7      # pass-by closed -> mild demotion
    assert open_cafe.score == 1.0 and open_cafe.open_state is True
    assert unknown.score == 1.0 and unknown.open_state is None


def test_holiday_rules_dont_block_weekday_decisions():
    # "PH off" must not force abstention on a decidable weekday
    assert is_open("Mo-Fr 08:00-18:00; PH off", TUE_15H) is True
    assert is_open("Mo-Fr 08:00-18:00; PH off", TUE_23H) is False
    # PH inside a day list extends to holidays; weekdays still decidable
    assert is_open("PH,Sa,Su 10:00-18:00; Mo-Fr 08:30-17:00", TUE_15H) is True


def test_night_demotes_unknown_daytime_categories():
    night = datetime(2026, 6, 9, 23, 30, tzinfo=PARIS_TZ)
    day = datetime(2026, 6, 9, 15, 0, tzinfo=PARIS_TZ)
    cafe_n, bar_n = P("cafe", None), P("bar_pub", None)
    apply_open_now([cafe_n, bar_n], {}, when=night)
    assert cafe_n.score == 0.5     # unknown café at 23:30 -> poor bet
    assert bar_n.score == 1.0      # unknown bar at night -> plausible
    cafe_d = P("cafe", None)
    apply_open_now([cafe_d], {}, when=day)
    assert cafe_d.score == 1.0     # daytime unknown untouched
