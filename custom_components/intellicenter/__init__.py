"""Pentair IntelliCenter Integration.

This integration connects to a Pentair IntelliCenter pool control system
via local network (not cloud) using a custom TCP protocol on port 6681.
It supports Zeroconf discovery and local push updates for real-time responsiveness.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.water_heater import DOMAIN as WATER_HEATER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP, UnitOfTemperature
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, dispatcher
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

if TYPE_CHECKING:
    pass

from .const import DOMAIN
from .pyintellicenter import (
    ACT_ATTR,
    BODY_ATTR,
    BODY_TYPE,
    CHEM_TYPE,
    CIRCGRP_TYPE,
    CIRCUIT_ATTR,
    CIRCUIT_TYPE,
    FEATR_ATTR,
    GPM_ATTR,
    HEATER_ATTR,
    HEATER_TYPE,
    HTMODE_ATTR,
    LISTORD_ATTR,
    LOTMP_ATTR,
    LSTTMP_ATTR,
    MODE_ATTR,
    PUMP_TYPE,
    PWR_ATTR,
    RPM_ATTR,
    SCHED_TYPE,
    SENSE_TYPE,
    SNAME_ATTR,
    SOURCE_ATTR,
    STATUS_ATTR,
    SUBTYP_ATTR,
    SYSTEM_TYPE,
    USE_ATTR,
    VACFLO_ATTR,
    VOL_ATTR,
    BaseController,
    ConnectionHandler,
    ModelController,
    PoolModel,
    PoolObject,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

# here is the list of platforms we support
PLATFORMS = [
    LIGHT_DOMAIN,
    SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    BINARY_SENSOR_DOMAIN,
    WATER_HEATER_DOMAIN,
    NUMBER_DOMAIN,
    COVER_DOMAIN,
]

# -------------------------------------------------------------------------------------


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Pentair IntelliCenter Integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IntelliCenter integration from a config entry."""

    attributes_map: dict[str, set[str]] = {
        BODY_TYPE: {
            SNAME_ATTR,
            HEATER_ATTR,
            HTMODE_ATTR,
            LOTMP_ATTR,
            LSTTMP_ATTR,
            STATUS_ATTR,
            VOL_ATTR,
        },
        CIRCUIT_TYPE: {SNAME_ATTR, STATUS_ATTR, USE_ATTR, SUBTYP_ATTR, FEATR_ATTR},
        CIRCGRP_TYPE: {CIRCUIT_ATTR},
        CHEM_TYPE: set(),
        HEATER_TYPE: {SNAME_ATTR, BODY_ATTR, LISTORD_ATTR},
        PUMP_TYPE: {SNAME_ATTR, STATUS_ATTR, PWR_ATTR, RPM_ATTR, GPM_ATTR},
        SENSE_TYPE: {SNAME_ATTR, SOURCE_ATTR},
        SCHED_TYPE: {SNAME_ATTR, ACT_ATTR, VACFLO_ATTR},
        SYSTEM_TYPE: {MODE_ATTR, VACFLO_ATTR},
    }
    model = PoolModel(attributes_map)

    controller = ModelController(entry.data[CONF_HOST], model, loop=hass.loop)

    class Handler(ConnectionHandler):
        """Connection handler with Home Assistant integration."""

        UPDATE_SIGNAL = DOMAIN + "_UPDATE_" + entry.entry_id
        CONNECTION_SIGNAL = DOMAIN + "_CONNECTION_" + entry.entry_id

        def started(self, controller: BaseController) -> None:
            """Handle initial connection to the Pentair system."""
            system_info = controller.systemInfo
            prop_name = system_info.propName if system_info else "Unknown"
            _LOGGER.info(f"connected to system: '{prop_name}'")

            # Check for model attribute to access pool objects
            if hasattr(controller, "model"):
                for pool_obj in controller.model:
                    _LOGGER.debug(f"   loaded {pool_obj}")

        @callback  # type: ignore[misc]
        def reconnected(self, controller: BaseController) -> None:
            """Handle reconnection to the Pentair system."""
            system_info = controller.systemInfo
            prop_name = system_info.propName if system_info else "Unknown"
            _LOGGER.info(f"reconnected to system: '{prop_name}'")
            dispatcher.async_dispatcher_send(hass, self.CONNECTION_SIGNAL, True)

        @callback  # type: ignore[misc]
        def disconnected(
            self, controller: BaseController, exc: Exception | None
        ) -> None:
            """Handle disconnection from the Pentair system."""
            system_info = controller.systemInfo
            prop_name = system_info.propName if system_info else "Unknown"
            _LOGGER.info(f"disconnected from system: '{prop_name}'")
            dispatcher.async_dispatcher_send(hass, self.CONNECTION_SIGNAL, False)

        @callback  # type: ignore[misc]
        def updated(
            self, controller: ModelController, updates: dict[str, dict[str, Any]]
        ) -> None:
            """Handle updates from the Pentair system."""
            _LOGGER.debug(f"received update for {len(updates)} pool objects")
            dispatcher.async_dispatcher_send(hass, self.UPDATE_SIGNAL, updates)

    try:
        handler = Handler(controller)

        await handler.start()

        # Set up platforms BEFORE returning from setup_entry
        # This ensures entities are available immediately after setup completes
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        hass.data.setdefault(DOMAIN, {})

        # Store handler and event listener callback for cleanup
        async def on_hass_stop(event: Any) -> None:
            """Stop push updates when hass stops."""
            handler.stop()

        stop_listener = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, on_hass_stop
        )

        hass.data[DOMAIN][entry.entry_id] = {
            "handler": handler,
            "stop_listener": stop_listener,
        }

        return True
    except ConnectionRefusedError as err:
        raise ConfigEntryNotReady from err


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload IntelliCenter config entry."""
    # Use the proper Home Assistant method for unloading platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Cleanup handler and event listener
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.info(f"unloading integration {entry.entry_id}")
    if entry_data:
        # Cancel the stop listener to prevent memory leaks
        stop_listener = entry_data.get("stop_listener")
        if stop_listener:
            stop_listener()

        # Stop the connection handler
        handler = entry_data.get("handler")
        if handler:
            handler.stop()

    # If it was the last instance of this integration, clear up the DOMAIN entry
    if not hass.data[DOMAIN]:
        del hass.data[DOMAIN]

    return bool(unload_ok)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry data to current version.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to migrate.

    Returns:
        True if migration was successful.
    """
    _LOGGER.debug(f"Migrating from version {entry.version}.{entry.minor_version}")

    # Currently at version 1.1, no migration needed yet
    # Future migrations should follow this pattern:
    # if entry.version == 1:
    #     # Migrate from version 1 to version 2
    #     new_data = {**entry.data, "new_key": "default_value"}
    #     hass.config_entries.async_update_entry(entry, data=new_data, version=2)

    return True


# -------------------------------------------------------------------------------------


class PoolEntity(Entity):  # type: ignore[misc]
    """Base representation of a Pool entity linked to a pool object.

    This class provides common functionality for all pool-related entities
    including device info, state attributes, and update callbacks.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ModelController,
        poolObject: PoolObject,
        attribute_key: str = STATUS_ATTR,
        name: str | None = None,
        enabled_by_default: bool = True,
        extraStateAttributes: Iterable[str] | None = None,
        icon: str | None = None,
        unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize a Pool entity.

        Args:
            entry: The config entry for this integration
            controller: The ModelController managing the connection
            poolObject: The PoolObject this entity represents
            attribute_key: The primary attribute to monitor (default: STATUS_ATTR)
            name: Custom name or suffix (prefixed with '+') for the entity
            enabled_by_default: Whether the entity is enabled by default
            extraStateAttributes: Additional attributes to include in state
            icon: Custom icon for the entity
            unit_of_measurement: Unit of measurement for sensors
        """
        self._entry_id = entry.entry_id
        self._controller = controller
        self._poolObject = poolObject
        self._attr_available = True
        self._extra_state_attributes: set[str] = (
            set(extraStateAttributes) if extraStateAttributes else set()
        )
        self._custom_name = name
        self._attribute_key = attribute_key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_native_unit_of_measurement = unit_of_measurement
        if icon:
            self._attr_icon = icon

        _LOGGER.debug(f"mapping {poolObject}")

    async def async_added_to_hass(self) -> None:
        """Entity is added to Home Assistant."""
        self.async_on_remove(
            dispatcher.async_dispatcher_connect(
                self.hass, DOMAIN + "_UPDATE_" + self._entry_id, self._update_callback
            )
        )

        self.async_on_remove(
            dispatcher.async_dispatcher_connect(
                self.hass,
                DOMAIN + "_CONNECTION_" + self._entry_id,
                self._connection_callback,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Entity is removed from Home Assistant."""
        _LOGGER.debug(f"removing entity: {self.unique_id}")

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        if self._custom_name is None:
            # Default is to return the name of the underlying pool object
            return self._poolObject.sname
        elif self._custom_name.startswith("+"):
            # Name is a suffix
            base_name = self._poolObject.sname or ""
            return base_name + self._custom_name[1:]
        else:
            return self._custom_name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        my_id: str = self._entry_id + "_" + self._poolObject.objnam
        if self._attribute_key != STATUS_ATTR:
            my_id = my_id + self._attribute_key
        return my_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        system_info = self._controller.systemInfo

        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer="Pentair",
            model="IntelliCenter",
            name=system_info.propName if system_info else "IntelliCenter",
            sw_version=system_info.swVersion if system_info else None,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the entity."""
        pool_obj = self._poolObject

        obj_type = pool_obj.objtype
        if pool_obj.subtype:
            obj_type += f"/{pool_obj.subtype}"

        attributes: dict[str, Any] = {
            "OBJNAM": pool_obj.objnam,
            "OBJTYPE": obj_type,
        }

        if pool_obj.status:
            attributes["Status"] = pool_obj.status

        for attribute in self._extra_state_attributes:
            value = pool_obj[attribute]
            if value is not None:
                attributes[attribute] = value

        return attributes

    def requestChanges(self, changes: dict[str, Any]) -> None:
        """Request changes as key:value pairs to the associated Pool object.

        Args:
            changes: Dictionary of attribute changes to apply
        """
        # Since we don't care about waiting for the response, set waitForResponse to False
        # Whatever changes were requested will be reflected as an update if successful
        self._controller.requestChanges(
            self._poolObject.objnam, changes, waitForResponse=False
        )

    def _check_attributes_updated(
        self, updates: dict[str, dict[str, Any]], *attributes: str
    ) -> bool:
        """Check if any of the specified attributes were updated.

        Helper method to simplify isUpdated() implementations in subclasses.
        Instead of repeating the set intersection pattern, subclasses can call
        this method with the attributes they care about.

        Args:
            updates: Dictionary of object updates from IntelliCenter
            *attributes: Variable number of attribute names to check

        Returns:
            True if any of the specified attributes were updated for this object

        Example:
            def isUpdated(self, updates):
                return self._check_attributes_updated(
                    updates, STATUS_ATTR, HEATER_ATTR, HTMODE_ATTR
                )
        """
        my_updates = updates.get(self._poolObject.objnam, {})
        if not my_updates:
            return False
        return bool(set(attributes) & my_updates.keys())

    def isUpdated(self, updates: dict[str, dict[str, Any]]) -> bool:
        """Return true if the entity is updated by the updates from IntelliCenter.

        Args:
            updates: Dictionary of object updates

        Returns:
            True if this entity's primary attribute was updated

        Note:
            Subclasses that need to track multiple attributes should override
            this method and use _check_attributes_updated() helper.
        """
        return self._attribute_key in updates.get(self._poolObject.objnam, {})

    @callback  # type: ignore[misc]
    def _update_callback(self, updates: dict[str, dict[str, Any]]) -> None:
        """Update the entity if its underlying pool object has changed."""
        if self.isUpdated(updates):
            self._attr_available = True
            _LOGGER.debug(f"updating {self} from {updates}")
            self.async_write_ha_state()

    @callback  # type: ignore[misc]
    def _connection_callback(self, is_connected: bool) -> None:
        """Mark the entity as unavailable after being disconnected from the server."""
        if is_connected:
            updated_obj = self._controller.model[self._poolObject.objnam]
            if not updated_obj:
                # This is for the rare case where the object the entity is mapped to
                # had been removed from the Pentair system while we were disconnected
                return
            self._poolObject = updated_obj
        self._attr_available = is_connected
        self.async_write_ha_state()

    def pentairTemperatureSettings(self) -> str:
        """Return the temperature units from the Pentair system.

        Returns:
            UnitOfTemperature.CELSIUS or UnitOfTemperature.FAHRENHEIT
        """
        system_info = self._controller.systemInfo
        if system_info and system_info.usesMetric:
            return str(UnitOfTemperature.CELSIUS)
        return str(UnitOfTemperature.FAHRENHEIT)

    def _safe_float_conversion(self, value: Any) -> float | None:
        """Safely convert a value to float.

        Helper method to convert attribute values to float with proper
        error handling. Used for temperature and other numeric values.

        Args:
            value: The value to convert (can be None, string, or numeric).

        Returns:
            The value as float, or None if conversion fails.
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int_conversion(self, value: Any) -> int | None:
        """Safely convert a value to int.

        Helper method to convert attribute values to int with proper
        error handling. Used for RPM, power, and other integer values.

        Args:
            value: The value to convert (can be None, string, or numeric).

        Returns:
            The value as int, or None if conversion fails.
        """
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


# -------------------------------------------------------------------------------------
# Platform Setup Helper
# -------------------------------------------------------------------------------------


def get_controller(hass: HomeAssistant, entry: ConfigEntry) -> ModelController:
    """Get the ModelController for a config entry.

    This helper reduces boilerplate in platform async_setup_entry functions.

    Args:
        hass: The Home Assistant instance
        entry: The config entry

    Returns:
        The ModelController for this entry

    Example:
        async def async_setup_entry(hass, entry, async_add_entities):
            controller = get_controller(hass, entry)
            entities = []
            for obj in controller.model.objectList:
                if obj.isALight:
                    entities.append(PoolLight(entry, controller, obj))
            async_add_entities(entities)
    """
    handler = hass.data[DOMAIN][entry.entry_id]["handler"]
    controller: ModelController = handler.controller
    return controller


# -------------------------------------------------------------------------------------
# On/Off Control Mixin
# -------------------------------------------------------------------------------------


class OnOffControlMixin:
    """Mixin for entities with simple on/off control.

    This mixin provides common turn_on/turn_off functionality for entities
    that use STATUS_ATTR with standard on/off status values.

    Classes using this mixin must also inherit from PoolEntity (which provides
    requestChanges). The mixin should be listed AFTER PoolEntity in the class
    inheritance to ensure proper method resolution order.

    Example:
        class PoolCircuit(PoolEntity, OnOffControlMixin, SwitchEntity):
            # is_on, async_turn_on, async_turn_off provided by mixin
            pass
    """

    # Type hints for attributes provided by PoolEntity
    _poolObject: PoolObject
    _attribute_key: str

    # Note: requestChanges is provided by PoolEntity, not defined here
    # to avoid MRO issues. This is just a type hint for IDE support.
    if TYPE_CHECKING:

        def requestChanges(self, changes: dict[str, Any]) -> None:
            """Request changes - provided by PoolEntity."""
            ...

    @property
    def is_on(self) -> bool:
        """Return true if the entity is on."""
        return bool(
            self._poolObject[self._attribute_key] == self._poolObject.onStatus
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.requestChanges({self._attribute_key: self._poolObject.onStatus})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.requestChanges({self._attribute_key: self._poolObject.offStatus})
