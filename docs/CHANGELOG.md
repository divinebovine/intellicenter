# Changelog

All notable changes to the Pentair IntelliCenter integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-01-15

### Added
- **Gold Quality Scale Achievement** - Comprehensive automated test suite with 59 tests
  - Model layer tests (24 tests): PoolObject and PoolModel functionality
  - Light platform tests (14 tests): Entity creation, turn on/off, color effects, state updates
  - Switch platform tests (10 tests): Circuit/body switches, vacation mode, featured circuits
  - Config flow tests (8 tests): User setup, Zeroconf discovery, error handling
  - Integration tests (5 tests): Setup, unload, connection failures
- TESTING.md documentation with comprehensive testing guide
- Enhanced test fixtures with realistic pool equipment data
- Test coverage for critical integration components

### Changed
- **CRITICAL: Fixed Broken Ping/Pong Mechanism** - Complete protocol health monitoring overhaul
  - **Removed non-functional ping/pong**: IntelliCenter does NOT support ping/pong protocol
  - **New idle detection**: Monitor time since last data received (120s timeout)
  - **Flow control monitoring**: Detect and recover from stuck requests (45s timeout)
  - **Push update reliance**: Leverage IntelliCenter's NotifyList messages for liveness
  - Increased heartbeat check interval from 10s to 30s (less overhead)
- **Improved Connection Stability** - Reduced frequency of device offline/online notifications
  - Added 15-second debounce period before marking device as disconnected
  - Prevents rapid online/offline transitions during temporary network issues
  - Connection state tracking prevents duplicate notifications
  - Improved logging to reduce verbosity during normal operation
- Updated quality scale from Silver to Gold in manifest.json
- Updated README.md badge to reflect Gold quality achievement

### Fixed
- **CRITICAL**: Removed broken ping/pong implementation that was closing connections every 60s
  - Testing revealed IntelliCenter rejects bare "ping" as invalid JSON
  - Previous implementation was treating timeout as connection failure
  - Now properly monitors actual data flow instead of non-existent pong responses
- Excessive device unavailable notifications during brief network interruptions
- Entities going offline too frequently causing unwanted automation triggers
- Rapid reconnection attempts not waiting for stable connection

### Technical Details

**Protocol Health Monitoring Changes:**
- **Removed**: Ping/pong mechanism (IntelliCenter doesn't support it)
- **Added**: Idle timeout monitoring (120s with no data = dead connection)
- **Added**: Flow control deadlock detection (45s stuck = reset queue)
- **Improved**: Heartbeat interval 10s → 30s (reduced overhead)

**Connection Debouncing:**
- New 15-second grace period before marking as disconnected
- Connection state tracking prevents duplicate notifications
- Reconnection attempts start immediately but notification waits for stability

**Behavior Impact:**
- **Before**: Device marked offline after 60s of "missed pongs" (that never arrived)
- **After**: Device marked offline only after 120s of complete data silence
- Entities remain "available" during brief disconnections if reconnection succeeds within 15s grace period
- Properly detects actual IntelliCenter NotifyList push updates as connection health indicator

## [2.1.0] - Previous Release

### Added
- Initial Silver quality scale implementation
- Comprehensive troubleshooting documentation
- Diagnostic capabilities

### Changed
- Improved connection recovery with exponential backoff
- Enhanced documentation

## [2.0.0] - Previous Major Release

### Added
- Home Assistant config flow UI setup
- Zeroconf auto-discovery
- Multiple platform support (light, switch, sensor, binary_sensor, water_heater, number, cover)

[2.2.0]: https://github.com/joyfulhouse/intellicenter/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/joyfulhouse/intellicenter/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/joyfulhouse/intellicenter/releases/tag/v2.0.0
