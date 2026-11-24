# Changelog

## [0.2.3] - 2026-11-24

### Changed
- **Installation through the Home Assistant Marketplace.** Since Home Assistant 2026.11, HACS is built into Home Assistant as the Marketplace. The README now has a Marketplace badge and install steps. An existing HACS installation moves over by itself and keeps receiving updates.

## [0.2.2] - 2026-10-11

### Fixed
- **CI failed on Home Assistant 2026.10.** Home Assistant replaced voluptuous with probatio in 2026.9, and since 2026.10 `async_show_form` is typed to take a `probatio.Schema`. The config flow still imported `voluptuous`, so strict `mypy` rejected every form schema. It now imports `probatio` and falls back to `voluptuous` on Home Assistant 2026.4 to 2026.8, which do not ship probatio. Behaviour is unchanged: at runtime Home Assistant already redirects `voluptuous` imports to probatio.

## [0.2.1] - 2026-07-25

### Added
- CI now runs the test suite. The eight parser tests have existed since 0.1.0 and the workflow never executed them, because it validated HACS and hassfest metadata only. It also now runs `ruff check`, `ruff format --check` and strict `mypy`.
- A release gate that fails a tag push when the tag disagrees with the version in `manifest.json` or `pyproject.toml`.

### Fixed
- The test suite could not run under `uv run pytest` at all. `pytest-homeassistant-custom-component` registers itself as the `homeassistant` plugin and injects autouse async fixtures into every test, which made pytest-asyncio error out on these deliberately Home Assistant free sync tests, and on Windows its import of `homeassistant.runner` failed on the missing `fcntl` module. The plugin is now disabled for this suite.
- Two small typing corrections needed for strict `mypy`, in code the tests already cover: the per-day sensor factory uses named closures instead of lambdas carrying a default argument, and a stale `type: ignore` was removed from the test helper.

## [0.2.0] - 2026-05-28

### Added
- Live "UV index now" sensor for your Home Assistant location, using the free Open-Meteo air-quality API (no API key needed). It updates through the day and is recorded, so you get an actual UV history graph.
- The current sensor exposes an `hourly` attribute (today + tomorrow) for an intraday UV curve.

### Notes
- KNMI remains the source for the official national daily forecast; Open-Meteo provides the location-specific live/hourly value (CAMS model data, not a ground measurement — no measured UV is published as data for the Netherlands).

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
