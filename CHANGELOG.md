# Changelog

## [0.1.2] - 2026-05-28

### Changed
- Forecast day sensors now show a readable name: "Today", "Tomorrow", and the weekday + date (e.g. "Saturday 30 May") for the following days, updated automatically on each poll.
- Added `weekday` to the per-day sensors and to the `forecast` attribute, so a graph card can plot the multi-day forecast by absolute date/weekday (avoids mixing forecast days in a single sensor's history).
- Forecast day sensors use a stable entity id (`sensor.knmi_uv_index_day_N`).

## [0.1.1] - 2026-05-28

### Changed
- The KNMI `uv-index` dataset publishes an XML forecast (`zonkrachtverwachting`), not NetCDF. Rewrote the parser to read this XML using only the standard library.
- Removed the `netCDF4` dependency — the integration now works on all platforms, including 32-bit systems.
- The forecast is national (the Netherlands), so the location/zone selection was removed; setup now only asks for the API key and is a single instance.
- Each forecast day exposes the UV index for sunny weather (primary value) and for cloudy weather (`uv_cloudy` attribute).

## [0.1.0] - 2026-05-28

### Added
- Initial release
- KNMI Data Platform Open Data API integration with API key authentication
- UV index sensor for a chosen location (current value)
- Daily maximum UV index sensor for each available forecast day
- Location selection during setup based on Home Assistant zones (defaults to Home)
- Configurable update interval (300-21600 seconds, default 900)
- Options flow to change the update interval and location
- Config flow with API key validation against the KNMI Data Platform
- HACS compatible
