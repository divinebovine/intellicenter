"""Pentair Intellicenter binary sensors.

This module provides binary sensor entities for:
- Freeze protection circuits
- Heater status
- Schedule status
- Pump status
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PoolEntity, get_controller
from .pyintellicenter import (
    BODY_ATTR,
    CIRCUIT_TYPE,
    HEATER_ATTR,
    HEATER_TYPE,
    HTMODE_ATTR,
    STATUS_ATTR,
    ModelController,
    PoolObject,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load pool binary sensors based on a config entry."""
    controller = get_controller(hass, entry)

    sensors: list[PoolBinarySensor | HeaterBinarySensor] = []

    obj: PoolObject
    for obj in controller.model.objectList:
        if obj.objtype == CIRCUIT_TYPE and obj.subtype == "FRZ":
            sensors.append(
                PoolBinarySensor(
                    entry,
                    controller,
                    obj,
                    icon="mdi:snowflake",
                    device_class=BinarySensorDeviceClass.COLD,
                )
            )
        elif obj.objtype == HEATER_TYPE:
            sensors.append(
                HeaterBinarySensor(
                    entry,
                    controller,
                    obj,
                )
            )
        elif obj.objtype == "SCHED":
            sensors.append(
                PoolBinarySensor(
                    entry,
                    controller,
                    obj,
                    attribute_key="ACT",
                    name="+ (schedule)",
                    enabled_by_default=False,
                    extraStateAttributes={"VACFLO"},
                )
            )
        elif obj.objtype == "PUMP":
            sensors.append(
                PoolBinarySensor(
                    entry,
                    controller,
                    obj,
                    valueForON="10",
                    device_class=BinarySensorDeviceClass.RUNNING,
                )
            )
    async_add_entities(sensors)


# -------------------------------------------------------------------------------------


class PoolBinarySensor(PoolEntity, BinarySensorEntity):  # type: ignore[misc]
    """Representation of a Pentair Binary Sensor.

    Used for freeze protection, schedule status, and pump running status.
    """

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        valueForON: str = "ON",
        device_class: BinarySensorDeviceClass | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a pool binary sensor.

        Args:
            entry: The config entry for this integration
            controller: The ModelController managing the connection
            poolObject: The PoolObject this sensor represents
            valueForON: The attribute value that indicates "on" state
            device_class: The device class for this sensor
            **kwargs: Additional arguments passed to PoolEntity
        """
        super().__init__(entry, controller, poolObject, **kwargs)
        self._valueForON = valueForON
        if device_class:
            self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        """Return true if sensor is on."""
        return bool(self._poolObject[self._attribute_key] == self._valueForON)


# -------------------------------------------------------------------------------------


class HeaterBinarySensor(PoolEntity, BinarySensorEntity):  # type: ignore[misc]
    """Representation of a Heater binary sensor.

    Tracks whether a heater is actively heating any body of water.
    """

    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_icon = "mdi:fire-circle"

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        **kwargs: Any,
    ) -> None:
        """Initialize a heater binary sensor.

        Args:
            entry: The config entry for this integration
            controller: The ModelController managing the connection
            poolObject: The PoolObject (heater) this sensor represents
            **kwargs: Additional arguments passed to PoolEntity
        """
        super().__init__(entry, controller, poolObject, **kwargs)
        body_attr = poolObject[BODY_ATTR]
        self._bodies: set[str] = set(body_attr.split(" ")) if body_attr else set()

    @property
    def is_on(self) -> bool:
        """Return true if the heater is actively heating."""
        for body_objnam in self._bodies:
            body = self._controller.model[body_objnam]
            if body is None:
                continue
            if (
                body[STATUS_ATTR] == "ON"
                and body[HEATER_ATTR] == self._poolObject.objnam
                and body[HTMODE_ATTR] != "0"
            ):
                return True
        return False

    def isUpdated(self, updates: dict[str, dict[str, Any]]) -> bool:
        """Return true if the entity is updated by the updates from IntelliCenter.

        Checks both:
        1. If any monitored body's heating-related attributes changed
        2. If the heater object itself was updated (e.g., availability change)

        Args:
            updates: Dictionary of object updates

        Returns:
            True if this heater sensor's state may have changed
        """
        # Check if any monitored body had heating-related updates
        for objnam in self._bodies & updates.keys():
            if {STATUS_ATTR, HEATER_ATTR, HTMODE_ATTR} & updates[objnam].keys():
                return True

        # Also check if the heater object itself was updated
        if self._poolObject.objnam in updates:
            return True

        return False
