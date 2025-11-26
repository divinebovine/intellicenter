"""Pentair Intellicenter switches.

This module provides switch entities for pool circuits, bodies of water,
superchlorinate mode, and vacation mode.
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OnOffControlMixin, PoolEntity, get_controller
from .pyintellicenter import (
    BODY_TYPE,
    CHEM_TYPE,
    CIRCUIT_TYPE,
    HEATER_ATTR,
    HTMODE_ATTR,
    SUPER_ATTR,
    SYSTEM_TYPE,
    VACFLO_ATTR,
    VOL_ATTR,
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
    """Load Pentair switch entities based on a config entry."""
    controller = get_controller(hass, entry)

    switches: list[PoolCircuit] = []

    pool_obj: PoolObject
    for pool_obj in controller.model.objectList:
        if pool_obj.objtype == BODY_TYPE:
            switches.append(PoolBody(entry, controller, pool_obj))
        elif (
            pool_obj.objtype == CHEM_TYPE
            and pool_obj.subtype == "ICHLOR"
            and SUPER_ATTR in pool_obj.attributes
        ):
            switches.append(
                PoolCircuit(
                    entry,
                    controller,
                    pool_obj,
                    attribute_key=SUPER_ATTR,
                    name="+ Superchlorinate",
                    icon="mdi:alpha-s-box-outline",
                )
            )
        elif (
            pool_obj.objtype == CIRCUIT_TYPE
            and not (pool_obj.isALight or pool_obj.isALightShow)
            and pool_obj.isFeatured
        ):
            switches.append(
                PoolCircuit(entry, controller, pool_obj, icon="mdi:alpha-f-box-outline")
            )
        elif pool_obj.objtype == CIRCUIT_TYPE and pool_obj.subtype == "CIRCGRP":
            switches.append(
                PoolCircuit(entry, controller, pool_obj, icon="mdi:alpha-g-box-outline")
            )
        elif pool_obj.objtype == SYSTEM_TYPE:
            switches.append(
                PoolCircuit(
                    entry,
                    controller,
                    pool_obj,
                    VACFLO_ATTR,
                    name="Vacation mode",
                    icon="mdi:palm-tree",
                    enabled_by_default=False,
                )
            )

    async_add_entities(switches)


# -------------------------------------------------------------------------------------


class PoolCircuit(PoolEntity, OnOffControlMixin, SwitchEntity):  # type: ignore[misc]
    """Representation of a standard pool circuit.

    Uses OnOffControlMixin for is_on, async_turn_on, async_turn_off.
    PoolEntity must come first to provide requestChanges for the mixin.
    """

    _attr_device_class = SwitchDeviceClass.SWITCH


# -------------------------------------------------------------------------------------


class PoolBody(PoolCircuit):
    """Representation of a body of water."""

    _attr_icon = "mdi:pool"

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
    ) -> None:
        """Initialize a Pool body from the underlying circuit."""
        super().__init__(entry, controller, poolObject)
        self._extra_state_attributes = {VOL_ATTR, HEATER_ATTR, HTMODE_ATTR}
