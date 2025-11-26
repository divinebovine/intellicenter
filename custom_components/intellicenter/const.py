"""Constants for the Pentair IntelliCenter integration."""

from __future__ import annotations

# Integration domain
DOMAIN = "intellicenter"

# Custom device classes
DEVICE_CLASS_ROTATION_SPEED = "rotational_speed"

# Units of measurement
CONST_RPM = "rpm"  # revolutions per minute
CONST_GPM = "gpm"  # gallons per minute

# Temperature rounding factors
# Used to round temperature values to user-friendly increments
TEMP_ROUNDING_FAHRENHEIT = 5  # Round to nearest 5°F
TEMP_ROUNDING_CELSIUS = 0.5  # Round to nearest 0.5°C

# Protocol defaults
DEFAULT_PORT = 6681  # Default TCP port for IntelliCenter communication

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
