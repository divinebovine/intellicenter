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
