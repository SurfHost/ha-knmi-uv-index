"""Parsing of KNMI UV index NetCDF files.

This module is intentionally free of Home Assistant imports so it can be
unit-tested standalone. It auto-detects the relevant variables (UV index,
latitude, longitude, time) from the NetCDF metadata, so it does not depend on
hard-coded variable names that may differ between dataset versions.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import netCDF4  # type: ignore[import-untyped]
import numpy as np

from .models import UvData, UvDayMax, UvForecastPoint

_LOGGER = logging.getLogger(__name__)

NIGHT_THRESHOLD = timedelta(minutes=45)

_LAT_NAMES = ("latitude", "lat", "y")
_LON_NAMES = ("longitude", "lon", "x")
_TIME_NAMES = ("time", "forecast_time", "datetime", "valid_time")
_LAT_UNITS = ("degrees_north", "degree_north", "degreesn")
_LON_UNITS = ("degrees_east", "degree_east", "degreese")
_UV_TOKENS = ("uv_index", "uvindex", "uvi", "erythem", "ery_uv", "uv")
_CLEAR_TOKENS = ("clear", "clr", "cloudfree", "cloud_free", "cloudless", "_cs", "cs_")


class UvParseError(Exception):
    """Raised when the NetCDF data cannot be interpreted."""


def _attr(var: object, name: str) -> str:
    """Return a string attribute of a NetCDF variable, or empty string."""
    value = getattr(var, name, "")
    return str(value).lower() if value else ""


def _find_coord(
    group: netCDF4.Dataset,
    fallback: netCDF4.Dataset,
    names: tuple[str, ...],
    units: tuple[str, ...] = (),
    standard_name: str = "",
    axis: str = "",
) -> tuple[str, netCDF4.Variable] | None:
    """Find a coordinate variable in `group`, falling back to `fallback`."""
    for source in (group, fallback):
        # First match on CF metadata.
        for var_name, var in source.variables.items():
            if standard_name and _attr(var, "standard_name") == standard_name:
                return var_name, var
            if units and _attr(var, "units") in units:
                return var_name, var
            if axis and _attr(var, "axis") == axis:
                return var_name, var
        # Then match on common names (case-insensitive).
        lower = {n.lower(): n for n in source.variables}
        for cand in names:
            if cand in lower:
                real = lower[cand]
                return real, source.variables[real]
    return None


def _to_pydatetime(value: object) -> datetime | None:
    """Convert a (cftime or python) datetime to a tz-aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime(
                value.year,  # type: ignore[attr-defined]
                value.month,  # type: ignore[attr-defined]
                value.day,  # type: ignore[attr-defined]
                getattr(value, "hour", 0),
                getattr(value, "minute", 0),
                int(getattr(value, "second", 0)),
            )
        except (AttributeError, ValueError, TypeError):
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _convert_times(time_var: netCDF4.Variable) -> list[datetime | None]:
    """Convert a NetCDF time variable to a list of UTC datetimes."""
    units = getattr(time_var, "units", None)
    if not units:
        raise UvParseError("Time variable has no 'units' attribute")
    calendar = getattr(time_var, "calendar", "standard")
    raw = np.ma.filled(time_var[:], np.nan).astype("float64")
    try:
        converted = netCDF4.num2date(raw, units=units, calendar=calendar)
    except (ValueError, TypeError) as err:
        raise UvParseError(f"Could not decode time axis: {err}") from err
    return [_to_pydatetime(v) for v in np.atleast_1d(converted)]


def _classify(name: str, var: netCDF4.Variable) -> tuple[bool, bool]:
    """Return (is_uv, is_clear_sky) for a candidate variable."""
    text = " ".join((name.lower(), _attr(var, "long_name"), _attr(var, "standard_name")))
    is_uv = any(tok in text for tok in _UV_TOKENS)
    is_clear = any(tok in text for tok in _CLEAR_TOKENS)
    return is_uv, is_clear


def _select_uv_vars(
    group: netCDF4.Dataset,
    skip: set[str],
    lat_dim: str,
    lon_dim: str,
    time_dim: str,
) -> tuple[netCDF4.Variable, netCDF4.Variable | None]:
    """Pick the primary (cloud/all-sky) and optional clear-sky UV variables."""
    primary_candidates: list[netCDF4.Variable] = []
    clear_candidates: list[netCDF4.Variable] = []
    fallback: list[netCDF4.Variable] = []

    for var_name, var in group.variables.items():
        if var_name in skip:
            continue
        dims = set(var.dimensions)
        if not ({lat_dim, lon_dim} <= dims) or time_dim not in dims:
            continue
        fallback.append(var)
        is_uv, is_clear = _classify(var_name, var)
        if is_uv and is_clear:
            clear_candidates.append(var)
        elif is_uv:
            primary_candidates.append(var)

    if primary_candidates:
        primary = primary_candidates[0]
    elif clear_candidates:
        primary = clear_candidates[0]
        clear_candidates = clear_candidates[1:]
    elif fallback:
        primary = fallback[0]
    else:
        raise UvParseError("No gridded UV variable found in this group")

    clear = clear_candidates[0] if clear_candidates else None
    return primary, clear


def _nearest_cell(
    lat_var: netCDF4.Variable,
    lon_var: netCDF4.Variable,
    latitude: float,
    longitude: float,
) -> tuple[dict[str, int], float, float]:
    """Return ({dim_name: index}, grid_lat, grid_lon) for the nearest grid cell."""
    lat_arr = np.ma.filled(lat_var[:], np.nan).astype("float64")
    lon_arr = np.ma.filled(lon_var[:], np.nan).astype("float64")

    if lat_arr.ndim == 1 and lon_arr.ndim == 1:
        lat_idx = int(np.nanargmin(np.abs(lat_arr - latitude)))
        lon_idx = int(np.nanargmin(np.abs(lon_arr - longitude)))
        index = {lat_var.dimensions[0]: lat_idx, lon_var.dimensions[0]: lon_idx}
        return index, float(lat_arr[lat_idx]), float(lon_arr[lon_idx])

    if lat_arr.ndim == 2 and lon_arr.ndim == 2 and lat_arr.shape == lon_arr.shape:
        cos = np.cos(np.radians(latitude))
        dist = (lat_arr - latitude) ** 2 + ((lon_arr - longitude) * cos) ** 2
        iy, ix = np.unravel_index(int(np.nanargmin(dist)), lat_arr.shape)
        ydim, xdim = lat_var.dimensions
        index = {ydim: int(iy), xdim: int(ix)}
        return index, float(lat_arr[iy, ix]), float(lon_arr[iy, ix])

    raise UvParseError("Unsupported latitude/longitude grid layout")


def _extract_series(
    var: netCDF4.Variable, time_dim: str, horiz_index: dict[str, int]
) -> np.ndarray:
    """Extract the 1-D time series for a single grid cell from a variable."""
    if time_dim not in var.dimensions:
        raise UvParseError(f"Variable {var.name} has no time dimension")
    selector: list[object] = []
    for dim in var.dimensions:
        if dim == time_dim:
            selector.append(slice(None))
        elif dim in horiz_index:
            selector.append(horiz_index[dim])
        else:
            selector.append(0)
    data = np.ma.filled(np.ma.asarray(var[tuple(selector)]), np.nan).astype("float64")
    return data.reshape(-1)


def _parse_group(
    group: netCDF4.Dataset,
    root: netCDF4.Dataset,
    latitude: float,
    longitude: float,
    now: datetime,
    max_days: int,
) -> UvData:
    """Try to parse UV data from a single NetCDF group."""
    lat = _find_coord(group, root, _LAT_NAMES, _LAT_UNITS, "latitude", "y")
    lon = _find_coord(group, root, _LON_NAMES, _LON_UNITS, "longitude", "x")
    time = _find_coord(group, root, _TIME_NAMES, standard_name="time")
    if lat is None or lon is None or time is None:
        raise UvParseError("Missing latitude, longitude or time coordinate")

    lat_name, lat_var = lat
    lon_name, lon_var = lon
    time_name, time_var = time
    time_dim = time_var.dimensions[0]
    lat_dim = lat_var.dimensions[0]
    lon_dim = lon_var.dimensions[-1]

    primary, clear = _select_uv_vars(
        group, {lat_name, lon_name, time_name}, lat_dim, lon_dim, time_dim
    )

    horiz_index, grid_lat, grid_lon = _nearest_cell(lat_var, lon_var, latitude, longitude)
    times = _convert_times(time_var)
    primary_series = _extract_series(primary, time_dim, horiz_index)
    clear_series = _extract_series(clear, time_dim, horiz_index) if clear is not None else None

    count = min(len(times), len(primary_series))
    points: list[UvForecastPoint] = []
    for i in range(count):
        ts = times[i]
        uv = primary_series[i]
        if ts is None or np.isnan(uv):
            continue
        clear_val: float | None = None
        if clear_series is not None and i < len(clear_series) and not np.isnan(clear_series[i]):
            clear_val = round(float(clear_series[i]), 3)
        points.append(UvForecastPoint(ts, round(float(uv), 3), clear_val))

    if not points:
        raise UvParseError("No valid UV data points for the requested location")

    has_clear = clear_series is not None
    nearest = min(points, key=lambda p: abs(p.timestamp - now))
    if abs(nearest.timestamp - now) <= NIGHT_THRESHOLD:
        current = nearest.uv
        current_time = nearest.timestamp
        current_clear = nearest.uv_clear
    else:
        current = 0.0
        current_time = now
        current_clear = 0.0 if has_clear else None

    by_day: dict[object, list[float]] = defaultdict(list)
    for point in points:
        by_day[point.timestamp.date()].append(point.uv)
    days = [UvDayMax(day, round(max(values), 3)) for day, values in sorted(by_day.items())]

    return UvData(
        current=current,
        current_time=current_time,
        current_clear=current_clear,
        days=days[:max_days],
        points=points,
        grid_latitude=round(grid_lat, 4),
        grid_longitude=round(grid_lon, 4),
    )


def _iter_groups(dataset: netCDF4.Dataset) -> list[netCDF4.Dataset]:
    """Return the dataset and all nested groups, breadth-first."""
    groups = [dataset]
    queue = list(dataset.groups.values())
    while queue:
        group = queue.pop(0)
        groups.append(group)
        queue.extend(group.groups.values())
    return groups


def _open_dataset(raw: bytes) -> tuple[netCDF4.Dataset, str | None]:
    """Open a NetCDF dataset from raw bytes, falling back to a temp file."""
    try:
        return netCDF4.Dataset("inmemory.nc", mode="r", memory=raw), None
    except OSError:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            tmp.write(raw)
            tmp.flush()
            tmp_name = tmp.name
        try:
            return netCDF4.Dataset(tmp_name, mode="r"), tmp_name
        except OSError as err:
            os.unlink(tmp_name)
            raise UvParseError(f"Could not open NetCDF data: {err}") from err


def parse_uv_netcdf(
    raw: bytes,
    latitude: float,
    longitude: float,
    now: datetime,
    max_days: int = 8,
) -> UvData:
    """Parse a KNMI UV index NetCDF file and return UV data for a location.

    `now` must be a timezone-aware datetime (UTC is recommended).
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    dataset, tmp_path = _open_dataset(raw)
    try:
        last_error: UvParseError | None = None
        for group in _iter_groups(dataset):
            try:
                return _parse_group(group, dataset, latitude, longitude, now, max_days)
            except UvParseError as err:
                last_error = err
                continue
        raise last_error or UvParseError("No UV index data found in file")
    except UvParseError:
        raise
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
        RuntimeError,
    ) as err:
        raise UvParseError(f"Failed to parse UV NetCDF data: {err}") from err
    finally:
        with contextlib.suppress(OSError, RuntimeError):
            dataset.close()
        if tmp_path:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
