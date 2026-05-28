"""Unit tests for the KNMI UV (zonkracht) XML parser.

The parser and models modules are deliberately free of Home Assistant imports,
so they are loaded in isolation here (without executing the package __init__,
which imports Home Assistant). The tests only need the standard library.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from datetime import date

import pytest

_BASE = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "knmi_uv_index"
_FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "zonkrachtverwachting.xml"


def _load(modname: str, filename: str) -> types.ModuleType:
    full = f"knmi_uv_pkg.{modname}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _BASE / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


if "knmi_uv_pkg" not in sys.modules:
    _pkg = types.ModuleType("knmi_uv_pkg")
    _pkg.__path__ = [str(_BASE)]  # type: ignore[attr-defined]
    sys.modules["knmi_uv_pkg"] = _pkg

_load("models", "models.py")
_parser = _load("parser", "parser.py")

parse_uv_xml = _parser.parse_uv_xml
select_today = _parser.select_today
UvParseError = _parser.UvParseError

_RAW = _FIXTURE.read_bytes()


def test_parse_real_fixture_days() -> None:
    data = parse_uv_xml(_RAW)

    # The KNMI forecast covers today + 8 days.
    assert len(data.days) == 9
    assert data.issued is not None

    first = data.days[0]
    assert first.day == date(2026, 5, 28)
    assert first.valid_id == "dag00"
    assert first.uv_sunny == 6.0
    assert first.uv_cloudy == 3.0

    last = data.days[-1]
    assert last.day == date(2026, 6, 5)
    assert last.uv_sunny == 5.3
    assert last.uv_cloudy == 2.6


def test_days_are_sorted_by_date() -> None:
    data = parse_uv_xml(_RAW)
    dates = [day.day for day in data.days]
    assert dates == sorted(dates)


def test_select_today_matches_date() -> None:
    data = parse_uv_xml(_RAW)
    tomorrow = select_today(data, date(2026, 5, 29))
    assert tomorrow is not None
    assert tomorrow.valid_id == "dag01"
    assert tomorrow.uv_sunny == 6.4


def test_select_today_falls_back_to_first_day() -> None:
    data = parse_uv_xml(_RAW)
    fallback = select_today(data, date(2030, 1, 1))
    assert fallback is not None
    assert fallback.day == date(2026, 5, 28)


def test_missing_cloudy_value_is_none() -> None:
    xml = b"""<?xml version="1.0"?>
    <report>
      <metadata>
        <report_info><report_dtg_issued>2026-05-28T06:00:00</report_dtg_issued></report_info>
        <report_valid_periods>
          <report_valid_period>
            <valid_id>dag00</valid_id>
            <valid_start>2026-05-28T00:00:00</valid_start>
            <valid_descr>vandaag</valid_descr>
          </report_valid_period>
        </report_valid_periods>
      </metadata>
      <data>
        <location>
          <location_id>NL</location_id>
          <block>
            <field_id>zonkracht_zonnig</field_id>
            <valid_id>dag00</valid_id>
            <field_content>7.0</field_content>
          </block>
        </location>
      </data>
    </report>"""
    data = parse_uv_xml(xml)
    assert len(data.days) == 1
    assert data.days[0].uv_sunny == 7.0
    assert data.days[0].uv_cloudy is None


def test_invalid_xml_raises() -> None:
    with pytest.raises(UvParseError):
        parse_uv_xml(b"<report><not-closed>")
