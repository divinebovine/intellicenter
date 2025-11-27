"""Pentair Intellicenter numbers.

This module provides number entities for:
- IntelliChlor output percentage control
- IntelliChem pH and ORP setpoint control
- Body max temperature setpoint (HITMP)
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyintellicenter import (
    BODY_ATTR,
    BODY_TYPE,
    CHEM_TYPE,
    HITMP_ATTR,
    ORPSET_ATTR,
    PHSET_ATTR,
    PRIM_ATTR,
    SEC_ATTR,
    PoolObject,
)

from . import IntelliCenterConfigEntry, PoolEntity
from .coordinator import IntelliCenterCoordinator

_LOGGER = logging.getLogger(__name__)

# Coordinator handles updates via push, so no parallel update limit needed
PARALLEL_UPDATES = 0

# IntelliChem setpoint ranges (per Pentair documentation)
PH_SETPOINT_MIN = 7.0
PH_SETPOINT_MAX = 7.6
PH_SETPOINT_STEP = 0.1

ORP_SETPOINT_MIN = 400
ORP_SETPOINT_MAX = 800
ORP_SETPOINT_STEP = 10

# Temperature setpoint ranges (Fahrenheit)
TEMP_SETPOINT_MIN = 40
TEMP_SETPOINT_MAX = 104
TEMP_SETPOINT_STEP = 1

# -------------------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntelliCenterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load pool number entities based on a config entry."""
    coordinator = entry.runtime_data

    numbers: list[PoolNumber] = []

    pool_obj: PoolObject
    for pool_obj in coordinator.model:
        if pool_obj.objtype == CHEM_TYPE:
            if pool_obj.subtype == "ICHLOR" and PRIM_ATTR in pool_obj.attribute_keys:
                # IntelliChlor output percentage controls
                body_attr = pool_obj[BODY_ATTR]
                if body_attr is None:
                    continue
                intellichlor_bodies = body_attr.split(" ")

                # Only create number entities for bodies that are actually configured
                for index, body_id in enumerate(intellichlor_bodies):
                    body = coordinator.model[body_id]
                    if body is not None:
                        attribute_key = PRIM_ATTR if index == 0 else SEC_ATTR
                        numbers.append(
                            PoolNumber(
                                coordinator,
                                pool_obj,
                                unit_of_measurement=PERCENTAGE,
                                attribute_key=attribute_key,
                                name=f"+ Output % ({body.sname})",
                            )
                        )

            elif pool_obj.subtype == "ICHEM":
                # IntelliChem pH setpoint control
                if PHSET_ATTR in pool_obj.attribute_keys:
                    numbers.append(
                        PoolNumber(
                            coordinator,
                            pool_obj,
                            min_value=PH_SETPOINT_MIN,
                            max_value=PH_SETPOINT_MAX,
                            step=PH_SETPOINT_STEP,
                            attribute_key=PHSET_ATTR,
                            name="+ pH Setpoint",
                            icon="mdi:ph",
                            device_class=NumberDeviceClass.PH,
                            mode=NumberMode.SLIDER,
                        )
                    )

                # IntelliChem ORP setpoint control
                if ORPSET_ATTR in pool_obj.attribute_keys:
                    numbers.append(
                        PoolNumber(
                            coordinator,
                            pool_obj,
                            min_value=ORP_SETPOINT_MIN,
                            max_value=ORP_SETPOINT_MAX,
                            step=ORP_SETPOINT_STEP,
                            attribute_key=ORPSET_ATTR,
                            name="+ ORP Setpoint",
                            icon="mdi:test-tube",
                            unit_of_measurement="mV",
                            mode=NumberMode.SLIDER,
                        )
                    )

    # Add body max temperature setpoints (HITMP)
    for pool_obj in coordinator.model:
        if pool_obj.objtype == BODY_TYPE and HITMP_ATTR in pool_obj.attribute_keys:
            numbers.append(
                PoolNumber(
                    coordinator,
                    pool_obj,
                    min_value=TEMP_SETPOINT_MIN,
                    max_value=TEMP_SETPOINT_MAX,
                    step=TEMP_SETPOINT_STEP,
                    attribute_key=HITMP_ATTR,
                    name="+ Max Temperature",
                    icon="mdi:thermometer-high",
                    device_class=NumberDeviceClass.TEMPERATURE,
                    mode=NumberMode.SLIDER,
                )
            )

    async_add_entities(numbers)


# -------------------------------------------------------------------------------------


class PoolNumber(PoolEntity, NumberEntity):
    """Representation of a pool number entity."""

    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        coordinator: IntelliCenterCoordinator,
        pool_object: PoolObject,
        min_value: float = DEFAULT_MIN_VALUE,
        max_value: float = DEFAULT_MAX_VALUE,
        step: float = DEFAULT_STEP,
        device_class: NumberDeviceClass | None = None,
        mode: NumberMode = NumberMode.AUTO,
        **kwargs: Any,
    ) -> None:
        """Initialize a pool number entity.

        Args:
            coordinator: The coordinator for this integration
            pool_object: The PoolObject this entity represents
            min_value: Minimum value for the number
            max_value: Maximum value for the number
            step: Step size for value changes
            device_class: The device class for this number entity
            mode: The input mode (slider, box, auto)
            **kwargs: Additional arguments passed to PoolEntity
        """
        super().__init__(coordinator, pool_object, **kwargs)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        if device_class:
            self._attr_device_class = device_class
        self._attr_mode = mode

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._safe_float_conversion(self._pool_object[self._attribute_key])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value.

        For pH setpoints, sends the value with one decimal place.
        For integer values (ORP, percentage), sends as integer.
        """
        # pH setpoint needs to preserve decimal (e.g., "7.2")
        if self._attribute_key == PHSET_ATTR:
            changes = {self._attribute_key: f"{value:.1f}"}
        else:
            changes = {self._attribute_key: str(int(value))}
        self.request_changes(changes)
