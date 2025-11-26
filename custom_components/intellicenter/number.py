"""Pentair Intellicenter numbers.

This module provides number entities for IntelliChlor output percentage control.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
    NumberEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PoolEntity, get_controller
from .pyintellicenter import (
    BODY_ATTR,
    CHEM_TYPE,
    PRIM_ATTR,
    SEC_ATTR,
    ModelController,
    PoolObject,
)

_LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load pool number entities based on a config entry."""
    controller = get_controller(hass, entry)

    numbers: list[PoolNumber] = []

    pool_obj: PoolObject
    for pool_obj in controller.model.objectList:
        if (
            pool_obj.objtype == CHEM_TYPE
            and pool_obj.subtype == "ICHLOR"
            and PRIM_ATTR in pool_obj.attributes
        ):
            body_attr = pool_obj[BODY_ATTR]
            if body_attr is None:
                continue
            intellichlor_bodies = body_attr.split(" ")

            # Only create number entities for bodies that are actually configured
            for index, body_id in enumerate(intellichlor_bodies):
                body = controller.model[body_id]
                if body is not None:
                    attribute_key = PRIM_ATTR if index == 0 else SEC_ATTR
                    numbers.append(
                        PoolNumber(
                            entry,
                            controller,
                            pool_obj,
                            unit_of_measurement=PERCENTAGE,
                            attribute_key=attribute_key,
                            name=f"+ Output % ({body.sname})",
                        )
                    )

    async_add_entities(numbers)


# -------------------------------------------------------------------------------------


class PoolNumber(PoolEntity, NumberEntity):  # type: ignore[misc]
    """Representation of a pool number entity."""

    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        min_value: float = DEFAULT_MIN_VALUE,
        max_value: float = DEFAULT_MAX_VALUE,
        step: float = DEFAULT_STEP,
        **kwargs: Any,
    ) -> None:
        """Initialize a pool number entity.

        Args:
            entry: The config entry for this integration
            controller: The ModelController managing the connection
            poolObject: The PoolObject this entity represents
            min_value: Minimum value for the number
            max_value: Maximum value for the number
            step: Step size for value changes
            **kwargs: Additional arguments passed to PoolEntity
        """
        super().__init__(entry, controller, poolObject, **kwargs)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._safe_float_conversion(self._poolObject[self._attribute_key])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        changes = {self._attribute_key: str(int(value))}
        self.requestChanges(changes)
