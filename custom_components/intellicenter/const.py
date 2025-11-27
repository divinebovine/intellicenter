"""Constants for the Pentair IntelliCenter integration."""

from __future__ import annotations

# Integration domain
DOMAIN = "intellicenter"

# Units of measurement (not available in Home Assistant constants)
CONST_RPM = "rpm"  # revolutions per minute
CONST_GPM = "gpm"  # gallons per minute

# Configuration option keys
CONF_KEEPALIVE_INTERVAL = "keepalive_interval"
CONF_RECONNECT_DELAY = "reconnect_delay"

# Default values for configuration options
DEFAULT_KEEPALIVE_INTERVAL = 90  # seconds
DEFAULT_RECONNECT_DELAY = 30  # seconds

# Minimum/maximum values for configuration options
MIN_KEEPALIVE_INTERVAL = 30
MAX_KEEPALIVE_INTERVAL = 300
MIN_RECONNECT_DELAY = 10
MAX_RECONNECT_DELAY = 120
