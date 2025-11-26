"""Pentair Intellicenter lights.

This module provides light entities for pool lights and light shows.
Supports color effects for IntelliBrite, MagicStream, and GloBrite lights.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from homeassistant.components.light import (
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PoolEntity, get_controller
from pyintellicenter import (
    ACT_ATTR,
    CIRCUIT_ATTR,
    STATUS_ATTR,
    USE_ATTR,
    ModelController,
    PoolObject,
)

_LOGGER = logging.getLogger(__name__)

# Mapping of IntelliCenter color codes to human-readable effect names
LIGHTS_EFFECTS: dict[str, str] = {
    "PARTY": "Party Mode",
    "CARIB": "Caribbean",
    "SSET": "Sunset",
    "ROMAN": "Romance",
    "AMERCA": "American",
    "ROYAL": "Royal",
    "WHITER": "White",
    "REDR": "Red",
    "BLUER": "Blue",
    "GREENR": "Green",
    "MAGNTAR": "Magenta",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load pool lights based on a config entry."""
    controller = get_controller(hass, entry)

    lights: list[PoolLight] = []

    obj: PoolObject
    for obj in controller.model.objectList:
        if obj.isALight:
            lights.append(
                PoolLight(
                    entry,
                    controller,
                    obj,
                    LIGHTS_EFFECTS if obj.supportColorEffects else None,
                )
            )
        elif obj.isALightShow:
            # Check if all child lights support color effects
            children = controller.model.getChildren(obj)
            supports_color = all(
                circuit_obj.supportColorEffects
                for child in children
                if (circuit_obj := controller.model[child[CIRCUIT_ATTR]]) is not None
            )
            lights.append(
                PoolLight(
                    entry,
                    controller,
                    obj,
                    LIGHTS_EFFECTS if supports_color else None,
                )
            )

    async_add_entities(lights)


class PoolLight(PoolEntity, LightEntity):  # type: ignore[misc]
    """Representation of a Pentair light.

    Supports basic on/off control and color effects for compatible lights
    (IntelliBrite, MagicStream, GloBrite).
    """

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature(0)

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        colorEffects: dict[str, str] | None = None,
    ) -> None:
        """Initialize a pool light.

        Args:
            entry: The config entry for this integration
            controller: The ModelController managing the connection
            poolObject: The PoolObject this light represents
            colorEffects: Optional mapping of IntelliCenter codes to effect names
        """
        super().__init__(entry, controller, poolObject)
        # USE appears to contain extra info like color...
        self._extra_state_attributes = {USE_ATTR}

        self._lightEffects = colorEffects
        self._reversedLightEffects: dict[str, str] | None = (
            {v: k for k, v in colorEffects.items()} if colorEffects else None
        )

        if self._lightEffects:
            self._attr_supported_features |= LightEntityFeature.EFFECT

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        if self._reversedLightEffects is None:
            return None
        return list(self._reversedLightEffects.keys())

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if self._lightEffects is None:
            return None
        use_value = self._poolObject[USE_ATTR]
        return self._lightEffects.get(use_value) if use_value else None

    @property
    def is_on(self) -> bool:
        """Return the state of the light."""
        return self._poolObject.status == self._poolObject.onStatus

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        self.requestChanges({STATUS_ATTR: "OFF"})

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        changes: dict[str, Any] = {STATUS_ATTR: self._poolObject.onStatus}

        if ATTR_EFFECT in kwargs and self._reversedLightEffects:
            effect = kwargs[ATTR_EFFECT]
            new_use = self._reversedLightEffects.get(effect)
            if new_use:
                changes[ACT_ATTR] = new_use

        self.requestChanges(changes)

    def isUpdated(self, updates: dict[str, dict[str, Any]]) -> bool:
        """Return true if the entity is updated by the updates from IntelliCenter."""
        my_updates = updates.get(self._poolObject.objnam, {})
        return bool(my_updates and ({STATUS_ATTR, USE_ATTR} & my_updates.keys()))
