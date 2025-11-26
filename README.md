# 🏊 Pentair IntelliCenter for Home Assistant

[![HACS Custom][hacsbadge]][hacs]
[![GitHub Release][releases-shield]][releases]
[![Tests](https://github.com/joyfulhouse/intellicenter/actions/workflows/quality-validation.yml/badge.svg)](https://github.com/joyfulhouse/intellicenter/actions/workflows/quality-validation.yml)
[![Quality Scale](https://img.shields.io/badge/quality_scale-platinum-e5e4e2)](https://www.home-assistant.io/docs/quality_scale/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A Home Assistant custom integration for **Pentair IntelliCenter** pool control systems. Monitor and control your pool, spa, lights, pumps, and heaters directly from Home Assistant with real-time local push updates.

<p align="center">
  <img src="device_info.png" width="400" alt="Device Info"/>
  <img src="entities.png" width="400" alt="Entities"/>
</p>

## ✨ Highlights

- 🏠 **100% Local** — Direct TCP connection to your IntelliCenter. No cloud, no internet required.
- ⚡ **Real-time Updates** — Push-based notifications for instant state changes.
- 🔍 **Zero Configuration** — Automatic discovery via Zeroconf/mDNS.
- 🔄 **Reliable** — Automatic reconnection with exponential backoff if connection drops.
- 🎛️ **Comprehensive** — Supports pools, spas, lights, pumps, heaters, chemistry, schedules, and more.

## 📋 Requirements

| Requirement | Details |
|-------------|---------|
| 🏠 Home Assistant | 2023.1 or newer |
| 🎛️ IntelliCenter | i5P, i7P, i9P, or i10P |
| 🌐 Network | Local network access (TCP port 6681) |

## 🚀 Quick Start

### Installation via HACS (Recommended)

1. Open **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. Add `https://github.com/joyfulhouse/intellicenter` (Category: Integration)
3. Search for "Pentair IntelliCenter" and click **Download**
4. Restart Home Assistant
5. Your IntelliCenter should be auto-discovered under **Settings** → **Devices & Services**

### Manual Installation

1. Download the [latest release](https://github.com/joyfulhouse/intellicenter/releases)
2. Copy `custom_components/intellicenter` to your `config/custom_components/` directory
3. Restart Home Assistant

## ⚙️ Configuration

### 🔍 Automatic Discovery

Your IntelliCenter is automatically discovered via Zeroconf:

1. Go to **Settings** → **Devices & Services**
2. Look for "Pentair IntelliCenter" under **Discovered**
3. Click **Configure** and confirm

### 🔧 Manual Setup

If discovery doesn't work:

1. **Settings** → **Devices & Services** → **+ Add Integration**
2. Search for "Pentair IntelliCenter"
3. Enter your IntelliCenter's IP address

**Finding your IP address:**
- 📡 Router's DHCP client list (look for "Pentair")
- 📱 Pentair mobile app: **Settings** → **System Information**
- 🖥️ IntelliCenter display panel

> 💡 **Tip:** Assign a static IP or DHCP reservation to prevent address changes.

### 🎚️ Advanced Options

After setup, configure connection settings:

1. **Settings** → **Devices & Services** → **IntelliCenter** → **Configure**
2. Adjust:
   - ⏱️ **Keepalive Interval** (30-300s, default 90) — Connection health check frequency
   - 🔄 **Reconnect Delay** (10-120s, default 30) — Initial retry delay after disconnect

## 🎛️ Supported Equipment

| Category | Entity Type | Features |
|----------|-------------|----------|
| 🏊 **Pool/Spa** | Switch, Sensors, Water Heater | On/off, temperature, heater control |
| 💡 **Lights** | Light | On/off, color effects (IntelliBrite, MagicStream) |
| 🌈 **Light Shows** | Light | Coordinated multi-light effects |
| ⚡ **Circuits** | Switch | All "Featured" circuits (cleaner, blower, etc.) |
| 🔄 **Pumps** | Binary Sensor, Sensors | Running status, power (W), speed (RPM), flow (GPM) |
| 🧪 **Chemistry** | Sensors | pH, ORP, tank levels (IntelliChem) |
| 🔥 **Heaters** | Binary Sensor | Running status |
| 📅 **Schedules** | Binary Sensor | Active status (disabled by default) |
| 🖥️ **System** | Switch, Binary Sensor, Sensors | Vacation mode, freeze protection, temperatures |

## 🤖 Automation Examples

### 🌅 Spa Ready at Sunset

```yaml
automation:
  - alias: "Evening Spa"
    trigger:
      - platform: sun
        event: sunset
        offset: "-00:30:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.spa
      - service: water_heater.set_temperature
        target:
          entity_id: water_heater.spa
        data:
          temperature: 102
```

### 🎉 Pool Party Lights

```yaml
automation:
  - alias: "Pool Party Mode"
    trigger:
      - platform: state
        entity_id: input_boolean.party_mode
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.pool_light
        data:
          effect: "Party"
```

### 🥶 Freeze Protection Alert

```yaml
automation:
  - alias: "Freeze Protection Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.freeze_protection
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "🏊 Pool Alert"
          message: "❄️ Freeze protection activated!"
```

## 🔧 Troubleshooting

<details>
<summary><strong>🔍 Integration Not Discovered</strong></summary>

1. Ensure Home Assistant and IntelliCenter are on the same network/VLAN
2. Check that mDNS/multicast traffic isn't blocked
3. Try manual setup with the IP address
</details>

<details>
<summary><strong>❌ Connection Failed</strong></summary>

1. Verify the IP address is correct
2. Ensure TCP port 6681 is accessible: `telnet <ip> 6681`
3. Check IntelliCenter is powered on and network cable connected
4. Try power cycling the IntelliCenter
</details>

<details>
<summary><strong>⚠️ Entities Unavailable</strong></summary>

1. Check connection status in **Settings** → **Devices & Services**
2. Review logs: **Settings** → **System** → **Logs**
3. Try reloading: **IntelliCenter** → **⋮** → **Reload**
4. The integration auto-reconnects with exponential backoff (30s, 45s, 67s...)
</details>

<details>
<summary><strong>🐛 Enable Debug Logging</strong></summary>

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.intellicenter: debug
```
</details>

## 🏗️ Architecture

This integration is built on two packages:

| Package | Description |
|---------|-------------|
| 📦 [pyintellicenter](https://github.com/joyfulhouse/pyintellicenter) | Standalone Python library for IntelliCenter protocol |
| 🏠 intellicenter | Home Assistant integration using pyintellicenter |

The separation allows the protocol library to be used in other projects and simplifies testing.

## 👨‍💻 Development

```bash
# Clone and setup
git clone https://github.com/joyfulhouse/intellicenter.git
cd intellicenter
uv sync

# For simultaneous pyintellicenter development
git clone https://github.com/joyfulhouse/pyintellicenter.git ../pyintellicenter
uv pip install -e ../pyintellicenter

# Testing
uv run pytest                    # 🧪 Run tests
uv run pytest --cov              # 📊 With coverage
uv run ruff check --fix          # 🔍 Lint
uv run ruff format               # ✨ Format
```

See [VALIDATION.md](VALIDATION.md) for full development guidelines.

## ⚠️ Known Limitations

- 🔧 **Equipment Coverage** — Tested primarily with standard configurations. Some equipment (covers, cascades, multiple heaters) may have limited testing.
- 🌡️ **Unit Changes** — Reload integration after changing metric/imperial on IntelliCenter.
- ⚙️ **Configuration Changes** — Reload integration after significant pool configuration changes.

## 🙏 Acknowledgments

This project builds upon the excellent work of:

- 🌟 **[@dwradcliffe](https://github.com/dwradcliffe)** — [Original intellicenter integration](https://github.com/dwradcliffe/intellicenter) that pioneered Home Assistant support for Pentair IntelliCenter systems
- 🌟 **[@jlvaillant](https://github.com/jlvaillant)** — [Enhanced fork](https://github.com/jlvaillant/intellicenter) with additional features and improvements

Thank you for your foundational work that made this integration possible! 💙

## 🤝 Contributing

Contributions welcome! Please:

1. 🍴 Fork the repository
2. 🌿 Create a feature branch
3. ✅ Ensure all tests pass (`uv run pytest`)
4. 📬 Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.

## 💬 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/joyfulhouse/intellicenter/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/joyfulhouse/intellicenter/discussions)

---

Made with ❤️ for the Home Assistant community

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange
[releases-shield]: https://img.shields.io/github/v/release/joyfulhouse/intellicenter
[releases]: https://github.com/joyfulhouse/intellicenter/releases
