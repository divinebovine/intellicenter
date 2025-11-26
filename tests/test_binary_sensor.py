"""Test the Pentair IntelliCenter binary sensor platform."""

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
import pytest

from custom_components.intellicenter import DOMAIN
from custom_components.intellicenter.binary_sensor import (
    HeaterBinarySensor,
    PoolBinarySensor,
)
from custom_components.intellicenter.pyintellicenter import (
    BODY_TYPE,
    CIRCUIT_TYPE,
    HEATER_ATTR,
    HEATER_TYPE,
    HTMODE_ATTR,
    PUMP_TYPE,
    STATUS_ATTR,
    PoolModel,
    PoolObject,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pool_object_freeze() -> PoolObject:
    """Return a PoolObject representing a freeze protection circuit."""
    return PoolObject(
        "FRZ01",
        {
            "OBJTYP": CIRCUIT_TYPE,
            "SUBTYP": "FRZ",
            "SNAME": "Freeze Protection",
            "STATUS": "OFF",
        },
    )


@pytest.fixture
def pool_object_heater_sensor() -> PoolObject:
    """Return a PoolObject representing a heater."""
    return PoolObject(
        "HTR01",
        {
            "OBJTYP": HEATER_TYPE,
            "SUBTYP": "GAS",
            "SNAME": "Gas Heater",
            "BODY": "POOL1 SPA01",
        },
    )


@pytest.fixture
def pool_object_pump_sensor() -> PoolObject:
    """Return a PoolObject representing a pump."""
    return PoolObject(
        "PUMP1",
        {
            "OBJTYP": PUMP_TYPE,
            "SUBTYP": "VS",
            "SNAME": "Pool Pump",
            "STATUS": "10",
        },
    )


@pytest.fixture
def pool_object_schedule() -> PoolObject:
    """Return a PoolObject representing a schedule."""
    return PoolObject(
        "SCHED1",
        {
            "OBJTYP": "SCHED",
            "SNAME": "Morning Filter",
            "ACT": "ON",
            "VACFLO": "OFF",
        },
    )


async def test_binary_sensor_setup_creates_entities(
    hass: HomeAssistant,
    pool_model: PoolModel,
) -> None:
    """Test binary sensor platform creates entities."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    entities_added = []

    def capture_entities(entities):
        entities_added.extend(entities)

    from custom_components.intellicenter.binary_sensor import async_setup_entry

    await async_setup_entry(hass, entry, capture_entities)

    # Should create binary sensors for:
    # - Heater (HTR01)
    # - Pump (PUMP1)
    # - Schedule (SCHED1)
    assert len(entities_added) >= 3


async def test_freeze_protection_sensor_off(
    hass: HomeAssistant,
    pool_object_freeze: PoolObject,
) -> None:
    """Test freeze protection sensor when off."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_freeze,
        icon="mdi:snowflake",
        device_class=BinarySensorDeviceClass.COLD,
    )

    assert sensor.is_on is False
    assert sensor.name == "Freeze Protection"
    assert sensor._attr_device_class == BinarySensorDeviceClass.COLD


async def test_freeze_protection_sensor_on(
    hass: HomeAssistant,
    pool_object_freeze: PoolObject,
) -> None:
    """Test freeze protection sensor when on."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Set status to ON
    pool_object_freeze.update({STATUS_ATTR: "ON"})

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_freeze,
        device_class=BinarySensorDeviceClass.COLD,
    )

    assert sensor.is_on is True


async def test_pump_sensor_running(
    hass: HomeAssistant,
    pool_object_pump_sensor: PoolObject,
) -> None:
    """Test pump sensor when running."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_pump_sensor,
        valueForON="10",  # Pump running value
        device_class=BinarySensorDeviceClass.RUNNING,
    )

    assert sensor.is_on is True
    assert sensor._attr_device_class == BinarySensorDeviceClass.RUNNING


async def test_pump_sensor_stopped(
    hass: HomeAssistant,
    pool_object_pump_sensor: PoolObject,
) -> None:
    """Test pump sensor when stopped."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Set pump to stopped
    pool_object_pump_sensor.update({STATUS_ATTR: "4"})

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_pump_sensor,
        valueForON="10",
        device_class=BinarySensorDeviceClass.RUNNING,
    )

    assert sensor.is_on is False


async def test_schedule_sensor_active(
    hass: HomeAssistant,
    pool_object_schedule: PoolObject,
) -> None:
    """Test schedule sensor when active."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_schedule,
        attribute_key="ACT",
        name="+ (schedule)",
        enabled_by_default=False,
    )

    assert sensor.is_on is True
    assert sensor._attr_entity_registry_enabled_default is False


async def test_schedule_sensor_inactive(
    hass: HomeAssistant,
    pool_object_schedule: PoolObject,
) -> None:
    """Test schedule sensor when inactive."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Set schedule to inactive
    pool_object_schedule.update({"ACT": "OFF"})

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_schedule,
        attribute_key="ACT",
    )

    assert sensor.is_on is False


async def test_heater_sensor_heating(
    hass: HomeAssistant,
    pool_object_heater_sensor: PoolObject,
) -> None:
    """Test heater sensor when actively heating."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    # Create mock pool body that is using this heater
    pool_body = PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Pool",
            "STATUS": "ON",
            "HEATER": "HTR01",
            "HTMODE": "1",  # Heating
        },
    )

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(return_value=pool_body)

    sensor = HeaterBinarySensor(
        entry,
        mock_controller,
        pool_object_heater_sensor,
    )

    assert sensor.is_on is True
    assert sensor._attr_device_class == BinarySensorDeviceClass.HEAT


async def test_heater_sensor_not_heating(
    hass: HomeAssistant,
    pool_object_heater_sensor: PoolObject,
) -> None:
    """Test heater sensor when not heating."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    # Create mock pool body that is not using this heater
    pool_body = PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Pool",
            "STATUS": "ON",
            "HEATER": "HTR01",
            "HTMODE": "0",  # Not heating (at temperature)
        },
    )

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(return_value=pool_body)

    sensor = HeaterBinarySensor(
        entry,
        mock_controller,
        pool_object_heater_sensor,
    )

    assert sensor.is_on is False


async def test_heater_sensor_body_off(
    hass: HomeAssistant,
    pool_object_heater_sensor: PoolObject,
) -> None:
    """Test heater sensor when body is off."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    # Create mock pool body that is off
    pool_body = PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Pool",
            "STATUS": "OFF",
            "HEATER": "HTR01",
            "HTMODE": "1",
        },
    )

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(return_value=pool_body)

    sensor = HeaterBinarySensor(
        entry,
        mock_controller,
        pool_object_heater_sensor,
    )

    assert sensor.is_on is False


async def test_heater_sensor_different_heater(
    hass: HomeAssistant,
    pool_object_heater_sensor: PoolObject,
) -> None:
    """Test heater sensor when a different heater is being used."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    # Create mock pool body using a different heater
    pool_body = PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Pool",
            "STATUS": "ON",
            "HEATER": "HTR02",  # Different heater
            "HTMODE": "1",
        },
    )

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(return_value=pool_body)

    sensor = HeaterBinarySensor(
        entry,
        mock_controller,
        pool_object_heater_sensor,
    )

    assert sensor.is_on is False


async def test_heater_sensor_is_updated_body_changes(
    hass: HomeAssistant,
    pool_object_heater_sensor: PoolObject,
) -> None:
    """Test heater sensor isUpdated when body attributes change."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(return_value=None)

    sensor = HeaterBinarySensor(
        entry,
        mock_controller,
        pool_object_heater_sensor,
    )

    # Should update on body status change
    assert sensor.isUpdated({"POOL1": {STATUS_ATTR: "ON"}}) is True

    # Should update on body heater change
    assert sensor.isUpdated({"POOL1": {HEATER_ATTR: "HTR01"}}) is True

    # Should update on body htmode change
    assert sensor.isUpdated({"POOL1": {HTMODE_ATTR: "1"}}) is True

    # Should update on heater object change
    assert sensor.isUpdated({"HTR01": {"STATUS": "ON"}}) is True

    # Should not update on unrelated object
    assert sensor.isUpdated({"OTHER": {STATUS_ATTR: "ON"}}) is False


async def test_heater_sensor_multiple_bodies(
    hass: HomeAssistant,
) -> None:
    """Test heater sensor with multiple bodies."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    heater = PoolObject(
        "HTR01",
        {
            "OBJTYP": HEATER_TYPE,
            "SNAME": "Gas Heater",
            "BODY": "POOL1 SPA01",  # Supports both bodies
        },
    )

    # Pool is heating
    pool_body = PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Pool",
            "STATUS": "ON",
            "HEATER": "HTR01",
            "HTMODE": "1",
        },
    )

    # Spa is not
    spa_body = PoolObject(
        "SPA01",
        {
            "OBJTYP": BODY_TYPE,
            "SNAME": "Spa",
            "STATUS": "OFF",
            "HEATER": "HTR01",
            "HTMODE": "0",
        },
    )

    mock_controller = MagicMock()
    mock_controller.model = MagicMock()
    mock_controller.model.__getitem__ = MagicMock(
        side_effect=lambda x: pool_body if x == "POOL1" else spa_body
    )

    sensor = HeaterBinarySensor(entry, mock_controller, heater)

    # Should be on because pool is heating
    assert sensor.is_on is True

    # Should update on either body's changes
    assert sensor.isUpdated({"POOL1": {HTMODE_ATTR: "0"}}) is True
    assert sensor.isUpdated({"SPA01": {STATUS_ATTR: "ON"}}) is True


async def test_binary_sensor_unique_id(
    hass: HomeAssistant,
    pool_object_freeze: PoolObject,
) -> None:
    """Test binary sensor unique ID generation."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_freeze,
    )

    assert sensor.unique_id == "test_entry_FRZ01"


async def test_binary_sensor_state_updates(
    hass: HomeAssistant,
    pool_object_freeze: PoolObject,
) -> None:
    """Test binary sensor state updates from IntelliCenter."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolBinarySensor(
        entry,
        mock_controller,
        pool_object_freeze,
    )

    # Initial state is OFF
    assert sensor.is_on is False

    # Simulate update from IntelliCenter
    updates = {"FRZ01": {STATUS_ATTR: "ON"}}
    assert sensor.isUpdated(updates) is True

    # Apply the update
    pool_object_freeze.update(updates["FRZ01"])

    # Verify state changed
    assert sensor.is_on is True
