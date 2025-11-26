"""Pentair Intellicenter water heaters.

This module provides water heater entities for pool and spa heating control.
Supports multiple heater types (gas, solar, heat pump) and remembers the
last used heater for convenient turn-on operations.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_IDLE, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import PoolEntity, get_controller
from .pyintellicenter import (
    BODY_ATTR,
    BODY_TYPE,
    HEATER_ATTR,
    HEATER_TYPE,
    HTMODE_ATTR,
    LISTORD_ATTR,
    LOTMP_ATTR,
    LSTTMP_ATTR,
    NULL_OBJNAM,
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
    """Load pool water heater entities based on a config entry."""
    controller = get_controller(hass, entry)

    # here we try to figure out which heater, if any, can be used for a given
    # body of water

    # first find all heaters
    # and sort them by their UI order (if they don't have one, use 100 and place them last)
    heaters = sorted(
        controller.model.getByType(HEATER_TYPE),
        key=lambda h: int(h[LISTORD_ATTR]) if h[LISTORD_ATTR] else 100,
    )

    bodies = controller.model.getByType(BODY_TYPE)

    water_heaters = []
    body: PoolObject
    for body in bodies:
        heater_list = []
        heater: PoolObject
        for heater in heaters:
            # if the heater supports this body, add it to the list
            if body.objnam in heater[BODY_ATTR].split(" "):
                heater_list.append(heater.objnam)
        if heater_list:
            water_heaters.append(PoolWaterHeater(entry, controller, body, heater_list))

    async_add_entities(water_heaters)


# -------------------------------------------------------------------------------------


class PoolWaterHeater(PoolEntity, WaterHeaterEntity, RestoreEntity):  # type: ignore[misc]
    """Representation of a Pentair water heater."""

    LAST_HEATER_ATTR = "LAST_HEATER"
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        heater_list: list[str],
    ) -> None:
        """Initialize."""
        super().__init__(
            entry,
            controller,
            poolObject,
            extraStateAttributes=[HEATER_ATTR, HTMODE_ATTR],
        )
        self._heater_list = heater_list
        self._lastHeater: str | None = self._poolObject[HEATER_ATTR]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the entity."""

        state_attributes = super().extra_state_attributes

        if self._lastHeater != NULL_OBJNAM:
            state_attributes[self.LAST_HEATER_ATTR] = self._lastHeater

        return state_attributes

    @property
    def state(self) -> str:
        """Return the current state."""
        status = self._poolObject[STATUS_ATTR]
        heater = self._poolObject[HEATER_ATTR]
        if status == "OFF" or heater == NULL_OBJNAM:
            return str(STATE_OFF)
        htmode = self._poolObject[HTMODE_ATTR]
        return str(STATE_ON) if htmode != "0" else str(STATE_IDLE)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return super().unique_id + LOTMP_ATTR

    @property
    def supported_features(self) -> WaterHeaterEntityFeature:
        """Return the list of supported features."""
        return (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
        )

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return self.pentairTemperatureSettings()

    @property
    def min_temp(self) -> float:
        """Return the minimum value."""
        system_info = self._controller.systemInfo
        return 5.0 if system_info and system_info.usesMetric else 4.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        system_info = self._controller.systemInfo
        return 40.0 if system_info and system_info.usesMetric else 104.0

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._safe_float_conversion(self._poolObject[LSTTMP_ATTR])

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._safe_float_conversion(self._poolObject[LOTMP_ATTR])

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperatures."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is not None:
            try:
                temp_value = int(target_temperature)
                self.requestChanges({LOTMP_ATTR: str(temp_value)})
            except (ValueError, TypeError) as err:
                _LOGGER.error(
                    f"Invalid temperature value '{target_temperature}': {err}"
                )

    @property
    def current_operation(self) -> str:
        """Return current operation."""
        heater = self._poolObject[HEATER_ATTR]
        if heater in self._heater_list:
            heater_obj = self._controller.model[heater]
            if heater_obj is not None and heater_obj.sname is not None:
                return heater_obj.sname
        return str(STATE_OFF)

    @property
    def operation_list(self) -> list[str]:
        """Return the list of available operation modes."""
        operations: list[str] = [str(STATE_OFF)]
        for heater in self._heater_list:
            heater_obj = self._controller.model[heater]
            if heater_obj is not None and heater_obj.sname is not None:
                operations.append(heater_obj.sname)
        return operations

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if operation_mode == STATE_OFF:
            self._turn_off()
        else:
            for heater in self._heater_list:
                heater_obj = self._controller.model[heater]
                if heater_obj is not None and operation_mode == heater_obj.sname:
                    self.requestChanges({HEATER_ATTR: heater})
                    break

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        heater = (
            self._lastHeater
            if self._lastHeater and self._lastHeater != NULL_OBJNAM
            else self._heater_list[0]
        )
        self.requestChanges({HEATER_ATTR: heater})

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        self._turn_off()

    def _turn_off(self) -> None:
        """Turn off the water heater."""
        self.requestChanges({HEATER_ATTR: NULL_OBJNAM})

    def isUpdated(self, updates: dict[str, dict[str, Any]]) -> bool:
        """Return true if the entity is updated by the updates from Intellicenter."""
        my_updates = updates.get(self._poolObject.objnam, {})

        updated = bool(
            my_updates
            and {STATUS_ATTR, HEATER_ATTR, HTMODE_ATTR, LOTMP_ATTR, LSTTMP_ATTR}
            & my_updates.keys()
        )

        if updated and self._poolObject[HEATER_ATTR] != NULL_OBJNAM:
            self._lastHeater = self._poolObject[HEATER_ATTR]

        return updated

    async def async_added_to_hass(self) -> None:
        """Entity is added to Home Assistant."""
        await super().async_added_to_hass()

        if self._lastHeater == NULL_OBJNAM:
            # Our current state is OFF so
            # let's see if we find a previous value stored in our state
            last_state = await self.async_get_last_state()

            if last_state:
                value = last_state.attributes.get(self.LAST_HEATER_ATTR)
                if value and value != NULL_OBJNAM:
                    self._lastHeater = value
