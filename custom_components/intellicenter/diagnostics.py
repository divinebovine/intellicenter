"""Diagnostics support for Intellicenter.

This module provides diagnostic information for troubleshooting the integration.
Sensitive data like IP addresses are automatically redacted.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from pyintellicenter import ModelController

# Keys to redact from diagnostics output for privacy
TO_REDACT = {
    CONF_HOST,  # IP address
    "host",
    "ip",
    "IP",
    "HOST",
    "PROPNAME",  # Pool system name (could identify the owner)
    "propName",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to get diagnostics for.

    Returns:
        Dictionary containing redacted diagnostic information.
    """
    # Start with basic entry info that's always available
    diagnostics_data: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
        },
    }

    try:
        # Try to get handler and controller
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if entry_data is None:
            diagnostics_data["error"] = "Integration data not found"
            return dict(async_redact_data(diagnostics_data, TO_REDACT))

        handler = entry_data.get("handler")
        if handler is None:
            diagnostics_data["error"] = "Handler not found"
            return dict(async_redact_data(diagnostics_data, TO_REDACT))

        controller: ModelController = handler.controller

        # Collect pool object information
        objects = [
            {
                "objnam": obj.objnam,
                "objtype": obj.objtype,
                "subtype": obj.subtype,
                "properties": obj.properties,
            }
            for obj in controller.model.objectList
        ]

        # Include system info if available
        system_info: dict[str, Any] = {}
        if controller.systemInfo:
            system_info = {
                "sw_version": controller.systemInfo.swVersion,
                "uses_metric": controller.systemInfo.usesMetric,
            }

        # Include connection metrics for observability
        connection_metrics = controller.metrics.to_dict()

        # Count objects by type for summary
        object_types: dict[str, int] = {}
        for obj in controller.model.objectList:
            obj_type = obj.objtype
            object_types[obj_type] = object_types.get(obj_type, 0) + 1

        diagnostics_data["system_info"] = system_info
        diagnostics_data["connection_metrics"] = connection_metrics
        diagnostics_data["object_count"] = len(objects)
        diagnostics_data["object_types"] = object_types
        diagnostics_data["objects"] = objects

    except Exception as err:
        diagnostics_data["error"] = f"Error collecting diagnostics: {err}"

    # Redact sensitive information before returning
    result: dict[str, Any] = async_redact_data(diagnostics_data, TO_REDACT)
    return result
