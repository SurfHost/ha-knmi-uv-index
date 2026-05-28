"""Unit tests for the KNMI UV NetCDF parser.

The parser and models modules are deliberately free of Home Assistant imports,
so they are loaded in isolation here (without executing the package __init__,
which imports Home Assistant). This lets the tests run with only netCDF4 +
numpy installed.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import types
from datetime import UTC, date, datetime

import netCDF4
import numpy as np

_BASE = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "knmi_uv_index"


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

_models = _load("models", "models.py")
_parser = _load("parser", "parser.py")

parse_uv_netcdf = _parser.parse_uv_netcdf

# Six forecast steps spanning two days (hours since midnight 2026-05-28 UTC).
_TIME_HOURS = [10, 12, 14, 34, 36, 38]
# UV values at the target grid cell (lat idx 1, lon idx 1) per time step.
_UV_AT_CELL = [1.0, 5.0, 3.0, 2.0, 6.0, 4.0]


def _build_netcdf(*, in_group: bool = False) -> bytes:
    """Build a small synthetic KNMI-like UV NetCDF file and return its bytes."""
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
        tmp_name = tmp.name
    ds = netCDF4.Dataset(tmp_name, "w", format="NETCDF4")
    ds.createDimension("time", len(_TIME_HOURS))
    ds.createDimension("lat", 3)
    ds.createDimension("lon", 3)

    time_var = ds.createVariable("time", "f8", ("time",))
    time_var.units = "hours since 2026-05-28 00:00:00"
    time_var.calendar = "standard"
    time_var.standard_name = "time"
    time_var[:] = _TIME_HOURS

    lat_var = ds.createVariable("lat", "f4", ("lat",))
    lat_var.units = "degrees_north"
    lat_var.standard_name = "latitude"
    lat_var[:] = [52.0, 52.5, 53.0]

    lon_var = ds.createVariable("lon", "f4", ("lon",))
    lon_var.units = "degrees_east"
    lon_var.standard_name = "longitude"
    lon_var[:] = [4.0, 4.5, 5.0]

    container = ds.createGroup("PRODUCT") if in_group else ds

    uv = container.createVariable("uv_index", "f4", ("time", "lat", "lon"))
    uv.long_name = "UV index"
    data = np.zeros((len(_TIME_HOURS), 3, 3), dtype="f4")
    for t, value in enumerate(_UV_AT_CELL):
        data[t, 1, 1] = value
    uv[:] = data

    uv_clear = container.createVariable("uv_index_clear_sky", "f4", ("time", "lat", "lon"))
    uv_clear.long_name = "Clear sky UV index"
    uv_clear[:] = data + 0.5

    ds.close()
    raw = pathlib.Path(tmp_name).read_bytes()
    pathlib.Path(tmp_name).unlink()
    return raw


def test_parse_daytime_current_and_daily_max() -> None:
    raw = _build_netcdf()
    now = datetime(2026, 5, 28, 12, 5, tzinfo=UTC)

    result = parse_uv_netcdf(raw, latitude=52.4, longitude=4.6, now=now)

    # Nearest grid cell is (52.5, 4.5).
    assert result.grid_latitude == 52.5
    assert result.grid_longitude == 4.5
    # Current = value at the 12:00 step (nearest to 12:05).
    assert result.current == 5.0
    assert result.current_clear == 5.5
    assert result.current_time == datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    # Two forecast days with their respective maxima.
    assert len(result.days) == 2
    assert result.days[0].day == date(2026, 5, 28)
    assert result.days[0].uv_max == 5.0
    assert result.days[1].day == date(2026, 5, 29)
    assert result.days[1].uv_max == 6.0


def test_parse_night_returns_zero() -> None:
    raw = _build_netcdf()
    now = datetime(2026, 5, 28, 2, 0, tzinfo=UTC)

    result = parse_uv_netcdf(raw, latitude=52.4, longitude=4.6, now=now)

    # 02:00 is more than 45 minutes from the first data point (10:00) -> night.
    assert result.current == 0.0
    assert result.current_clear == 0.0
    # Daily maxima are still available.
    assert result.days[0].uv_max == 5.0


def test_parse_data_inside_group() -> None:
    raw = _build_netcdf(in_group=True)
    now = datetime(2026, 5, 28, 14, 2, tzinfo=UTC)

    result = parse_uv_netcdf(raw, latitude=52.4, longitude=4.6, now=now)

    # Variable lives in the PRODUCT group while coordinates are at the root.
    assert result.current == 3.0
    assert result.grid_latitude == 52.5
    assert len(result.days) == 2


def test_max_days_cap() -> None:
    raw = _build_netcdf()
    now = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)

    result = parse_uv_netcdf(raw, latitude=52.4, longitude=4.6, now=now, max_days=1)

    assert len(result.days) == 1
    assert result.days[0].day == date(2026, 5, 28)
