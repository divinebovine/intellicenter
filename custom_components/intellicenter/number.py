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
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyintellicenter import (
    BODY_ATTR,
    CHEM_TYPE,
    PRIM_ATTR,
    SEC_ATTR,
    PoolObject,
)

from . import IntelliCenterConfigEntry, PoolEntity
from .coordinator import IntelliCenterCoordinator

_LOGGER = logging.getLogger(__name__)

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
        if (
            pool_obj.objtype == CHEM_TYPE
            and pool_obj.subtype == "ICHLOR"
            and PRIM_ATTR in pool_obj.attribute_keys
        ):
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
        **kwargs: Any,
    ) -> None:
        """Initialize a pool number entity.

        Args:
            coordinator: The coordinator for this integration
            pool_object: The PoolObject this entity represents
            min_value: Minimum value for the number
            max_value: Maximum value for the number
            step: Step size for value changes
            **kwargs: Additional arguments passed to PoolEntity
        """
        super().__init__(coordinator, pool_object, **kwargs)
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._safe_float_conversion(self._pool_object[self._attribute_key])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        changes = {self._attribute_key: str(int(value))}
        self.request_changes(changes)
