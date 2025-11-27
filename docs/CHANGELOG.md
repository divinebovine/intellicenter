# Changelog

All notable changes to the Pentair IntelliCenter integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.5.0] - 2025-11-27

### Added
- **IntelliChem Controls** - pH and ORP setpoint control via Number entities
- **Chemistry Sensors** - pH level, ORP level, calcium hardness, cyanuric acid, total alkalinity
- **Pump Diagnostics** - Power (W), speed (RPM), flow (GPM) sensors with diagnostic entity category
- **Tank Level Sensors** - Acid and chlorine tank level monitoring (diagnostic category)
- **Internationalization** - 12 language translations:
  - English, Spanish, French, German, Italian, Portuguese
  - Chinese (Simplified & Traditional), Japanese, Korean
  - Russian, Dutch

### Changed
- **Home Assistant 2025.11+ Required** - Minimum version updated
- **pyintellicenter 0.1.1** - Updated to stable release of protocol library
- **Documentation Rewrite** - Complete overhaul following joyfulhouse organization standards
- Sensor entity categories reorganized for cleaner UI:
  - Chemistry and pump sensors marked as diagnostic
  - Tank levels moved to diagnostic category
- Translation system updated to use `translation_key` for SelectSelector options
- Improved config flow translations with proper abort messages

### Fixed
- Fixed `reconfigure_successful` translation key not displaying properly
- Fixed firmware version sensor incorrectly having `state_class` attribute

---

## [3.1.0] - 2025-11-25

### Added
- **Protocol Library Extraction** - Separated `pyintellicenter` into standalone PyPI package
  - Published to PyPI: [pyintellicenter](https://pypi.org/project/pyintellicenter/)
  - Enables reuse in other projects
  - Simplifies testing and maintenance
- **Device Classes** - Added appropriate device classes to entities:
  - `SensorDeviceClass.PH` for pH sensors
  - `CoverDeviceClass.SHUTTER` for pool covers
  - `SwitchDeviceClass.SWITCH` for circuits
- **Configuration Options Flow** - User-configurable connection settings:
  - Keepalive interval (30-300 seconds)
  - Reconnect delay (10-120 seconds)
- **PoolConnectionHandler** - Extracted connection management from coordinator
- **Connection Metrics** - Response time tracking and health monitoring

### Changed
- Integration now imports from `pyintellicenter` package instead of embedded modules
- Manifest requires `pyintellicenter>=0.0.5a12`
- Updated code structure for better separation of concerns

---

## [3.0.0] - 2025-11-24

### Added
- **Platinum Quality Scale Achievement** - Full compliance with Home Assistant's highest quality tier
- **Comprehensive Test Suite** - 175+ automated tests covering:
  - Protocol layer (message parsing, flow control, keepalive)
  - Controller layer (connection management, reconnection logic)
  - Model layer (PoolObject, PoolModel state management)
  - All platform entities (light, switch, sensor, binary_sensor, water_heater, cover, number)
  - Config flow and options flow
  - Diagnostics
- **Full Type Annotations** - mypy strict mode compliance
- **Code Documentation** - Comprehensive docstrings throughout
- **Circuit Breaker Pattern** - Prevents hammering dead servers (opens after 5 failures)
- **orjson Integration** - 2-3x faster JSON serialization

### Changed
- Quality scale upgraded from Gold to Platinum
- All code formatted with ruff (replaced black/isort)
- Enhanced error handling and logging

---

## [2.2.1] - 2025-11-20

### Fixed
- **CRITICAL: Keepalive Mechanism** - Replaced broken ping/pong with lightweight queries
  - IntelliCenter doesn't support ping/pong protocol
  - Now sends `{"command":"GetQuery","queryName":"GetHardwareDefinition"}` as keepalive
  - Configurable interval (default 90s) prevents idle disconnections

---

## [2.2.0] - 2025-11-18

### Added
- **Gold Quality Scale Achievement** - Comprehensive automated test suite
- Test coverage for critical integration components
- Enhanced test fixtures with realistic pool equipment data

### Changed
- **Improved Connection Stability**
  - 15-second debounce before marking device disconnected
  - Prevents rapid online/offline transitions
- **Protocol Health Monitoring**
  - Idle timeout: 120s with no data = dead connection
  - Flow control deadlock detection: 45s stuck = reset queue
  - Heartbeat interval: 30s (reduced from 10s)

### Fixed
- Excessive device unavailable notifications during brief network interruptions
- Entities going offline too frequently
- Rapid reconnection attempts

---

## [2.1.0] - 2025-11-15

### Added
- **Silver Quality Scale Achievement**
- Comprehensive troubleshooting documentation
- Diagnostic capabilities

### Changed
- Connection recovery with exponential backoff (30s base, 1.5x multiplier)
- Enhanced documentation

---

## [2.0.0] - 2025-11-10

### Added
- Home Assistant config flow UI setup
- Zeroconf auto-discovery
- Multiple platform support:
  - `light` - Pool/spa lights with color effects
  - `switch` - Circuits, bodies of water, vacation mode
  - `sensor` - Temperature, chemistry, pump metrics
  - `binary_sensor` - Pump status, schedules, freeze protection
  - `water_heater` - Pool/spa heater control
  - `number` - Setpoint controls
  - `cover` - Pool covers

### Changed
- Migrated from black/isort to ruff
- Fixed network connectivity issues
- Added automated test suite

---

## [1.x and Earlier]

This integration builds upon the foundational work of the original IntelliCenter integrations:

- **[@dwradcliffe/intellicenter](https://github.com/dwradcliffe/intellicenter)** - Original implementation that pioneered Home Assistant support for Pentair IntelliCenter
- **[@jlvaillant/intellicenter](https://github.com/jlvaillant/intellicenter)** - Enhanced fork with additional features

See [ACKNOWLEDGMENTS.md](./ACKNOWLEDGMENTS.md) for full credits.

---

## Version Comparison

| Version | Quality Scale | Tests | Key Feature |
|---------|---------------|-------|-------------|
| 3.5.0 | Platinum | 175+ | IntelliChem, i18n |
| 3.1.0 | Platinum | 175+ | pyintellicenter extraction |
| 3.0.0 | Platinum | 175+ | Full test coverage |
| 2.2.x | Gold | 59 | Connection stability |
| 2.1.0 | Silver | 16 | Documentation |
| 2.0.0 | Bronze | 14 | Config flow |

---

[3.5.0]: https://github.com/joyfulhouse/intellicenter/compare/v3.1.0...v3.5.0
[3.1.0]: https://github.com/joyfulhouse/intellicenter/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/joyfulhouse/intellicenter/compare/v2.2.1...v3.0.0
[2.2.1]: https://github.com/joyfulhouse/intellicenter/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/joyfulhouse/intellicenter/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/joyfulhouse/intellicenter/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/joyfulhouse/intellicenter/releases/tag/v2.0.0
