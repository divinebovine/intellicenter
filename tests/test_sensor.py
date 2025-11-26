"""Test the Pentair IntelliCenter sensor platform."""

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_HOST,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import pytest

from custom_components.intellicenter import DOMAIN
from custom_components.intellicenter.const import CONST_GPM, CONST_RPM
from pyintellicenter import (
    BODY_TYPE,
    CHEM_TYPE,
    GPM_ATTR,
    LOTMP_ATTR,
    LSTTMP_ATTR,
    ORPTNK_ATTR,
    ORPVAL_ATTR,
    PHTNK_ATTR,
    PHVAL_ATTR,
    PUMP_TYPE,
    PWR_ATTR,
    RPM_ATTR,
    SALT_ATTR,
    SENSE_TYPE,
    SOURCE_ATTR,
    PoolModel,
    PoolObject,
)
from custom_components.intellicenter.sensor import PoolSensor

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pool_object_temp_sensor() -> PoolObject:
    """Return a PoolObject representing a temperature sensor."""
    return PoolObject(
        "SENSE1",
        {
            "OBJTYP": SENSE_TYPE,
            "SUBTYP": "AIR",
            "SNAME": "Air Temp",
            "SOURCE": "68",
        },
    )


@pytest.fixture
def pool_object_pump() -> PoolObject:
    """Return a PoolObject representing a pump with sensors."""
    return PoolObject(
        "PUMP1",
        {
            "OBJTYP": PUMP_TYPE,
            "SUBTYP": "VS",
            "SNAME": "Pool Pump",
            "STATUS": "10",
            "PWR": "1200",
            "RPM": "2000",
            "GPM": "55",
        },
    )


@pytest.fixture
def pool_object_body() -> PoolObject:
    """Return a PoolObject representing a pool body."""
    return PoolObject(
        "POOL1",
        {
            "OBJTYP": BODY_TYPE,
            "SUBTYP": "POOL",
            "SNAME": "Pool",
            "LSTTMP": "78",
            "LOTMP": "72",
        },
    )


@pytest.fixture
def pool_object_intellichem() -> PoolObject:
    """Return a PoolObject representing IntelliChem."""
    return PoolObject(
        "CHEM1",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHEM",
            "SNAME": "IntelliChem",
            "PHVAL": "7.4",
            "ORPVAL": "650",
            "QUALTY": "85",
            "PHTNK": "5",
            "ORPTNK": "3",
        },
    )


@pytest.fixture
def pool_object_intellichlor() -> PoolObject:
    """Return a PoolObject representing IntelliChlor."""
    return PoolObject(
        "CHEM2",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHLOR",
            "SNAME": "IntelliChlor",
            "SALT": "3200",
        },
    )


async def test_sensor_setup_creates_entities(
    hass: HomeAssistant,
    pool_model: PoolModel,
) -> None:
    """Test sensor platform creates entities."""
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

    from custom_components.intellicenter.sensor import async_setup_entry

    await async_setup_entry(hass, entry, capture_entities)

    # Should create sensors for:
    # - SENSE1 (air temp)
    # - PUMP1 (power, RPM, GPM = 3)
    # - POOL1 and SPA01 (last temp, desired temp = 4)
    # - CHEM1 (pH, ORP, pH tank, ORP tank = 4)
    assert len(entities_added) >= 10


async def test_temperature_sensor_properties(
    hass: HomeAssistant,
    pool_object_temp_sensor: PoolObject,
) -> None:
    """Test temperature sensor properties."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.systemInfo = MagicMock()
    type(mock_controller.systemInfo).usesMetric = property(lambda self: False)

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_temp_sensor,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    assert sensor.name == "Air Temp"
    assert sensor.unique_id == "test_entry_SENSE1SOURCE"
    assert sensor.native_value == 68
    assert sensor.native_unit_of_measurement == str(UnitOfTemperature.FAHRENHEIT)
    assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT


async def test_temperature_sensor_metric(
    hass: HomeAssistant,
    pool_object_temp_sensor: PoolObject,
) -> None:
    """Test temperature sensor with metric units."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.systemInfo = MagicMock()
    type(mock_controller.systemInfo).usesMetric = property(lambda self: True)

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_temp_sensor,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    assert sensor.native_unit_of_measurement == str(UnitOfTemperature.CELSIUS)


async def test_pump_power_sensor(
    hass: HomeAssistant,
    pool_object_pump: PoolObject,
) -> None:
    """Test pump power sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        attribute_key=PWR_ATTR,
        name="+ power",
        rounding_factor=25,
    )

    assert sensor.native_value == 1200  # Already multiple of 25
    assert sensor.native_unit_of_measurement == UnitOfPower.WATT
    assert sensor._attr_device_class == SensorDeviceClass.POWER


async def test_pump_power_sensor_rounding(
    hass: HomeAssistant,
) -> None:
    """Test pump power sensor value rounding."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    pump = PoolObject(
        "PUMP1",
        {
            "OBJTYP": PUMP_TYPE,
            "SNAME": "Pool Pump",
            "PWR": "1237",  # Should round to 1225 or 1250
        },
    )

    sensor = PoolSensor(
        entry,
        mock_controller,
        pump,
        device_class=SensorDeviceClass.POWER,
        unit_of_measurement=UnitOfPower.WATT,
        attribute_key=PWR_ATTR,
        rounding_factor=25,
    )

    # 1237 / 25 = 49.48, rounds to 49, 49 * 25 = 1225
    assert sensor.native_value == 1225


async def test_pump_rpm_sensor(
    hass: HomeAssistant,
    pool_object_pump: PoolObject,
) -> None:
    """Test pump RPM sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=None,
        unit_of_measurement=CONST_RPM,
        attribute_key=RPM_ATTR,
        name="+ rpm",
    )

    assert sensor.native_value == 2000
    assert sensor.native_unit_of_measurement == CONST_RPM
    assert sensor._attr_device_class is None


async def test_pump_gpm_sensor(
    hass: HomeAssistant,
    pool_object_pump: PoolObject,
) -> None:
    """Test pump GPM sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=None,
        unit_of_measurement=CONST_GPM,
        attribute_key=GPM_ATTR,
        name="+ gpm",
    )

    assert sensor.native_value == 55
    assert sensor.native_unit_of_measurement == CONST_GPM


async def test_body_temperature_sensors(
    hass: HomeAssistant,
    pool_object_body: PoolObject,
) -> None:
    """Test body temperature sensors."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.systemInfo = MagicMock()
    type(mock_controller.systemInfo).usesMetric = property(lambda self: False)

    # Last temp sensor
    last_temp = PoolSensor(
        entry,
        mock_controller,
        pool_object_body,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=LSTTMP_ATTR,
        name="+ last temp",
    )

    assert last_temp.native_value == 78
    assert last_temp.native_unit_of_measurement == str(UnitOfTemperature.FAHRENHEIT)

    # Desired temp sensor
    desired_temp = PoolSensor(
        entry,
        mock_controller,
        pool_object_body,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=LOTMP_ATTR,
        name="+ desired temp",
    )

    assert desired_temp.native_value == 72


async def test_intellichem_ph_sensor(
    hass: HomeAssistant,
    pool_object_intellichem: PoolObject,
) -> None:
    """Test IntelliChem pH sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_intellichem,
        device_class=None,
        attribute_key=PHVAL_ATTR,
        name="+ (pH)",
    )

    # pH value is a float
    assert sensor.native_value == 7.4


async def test_intellichem_orp_sensor(
    hass: HomeAssistant,
    pool_object_intellichem: PoolObject,
) -> None:
    """Test IntelliChem ORP sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_intellichem,
        device_class=None,
        attribute_key=ORPVAL_ATTR,
        name="+ (ORP)",
    )

    assert sensor.native_value == 650


async def test_intellichem_tank_level_sensors(
    hass: HomeAssistant,
    pool_object_intellichem: PoolObject,
) -> None:
    """Test IntelliChem tank level sensors."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    ph_tank = PoolSensor(
        entry,
        mock_controller,
        pool_object_intellichem,
        device_class=None,
        attribute_key=PHTNK_ATTR,
        name="+ (Ph Tank Level)",
    )

    assert ph_tank.native_value == 5

    orp_tank = PoolSensor(
        entry,
        mock_controller,
        pool_object_intellichem,
        device_class=None,
        attribute_key=ORPTNK_ATTR,
        name="+ (ORP Tank Level)",
    )

    assert orp_tank.native_value == 3


async def test_intellichlor_salt_sensor(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test IntelliChlor salt sensor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_intellichlor,
        device_class=None,
        unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        attribute_key=SALT_ATTR,
        name="+ (Salt)",
    )

    assert sensor.native_value == 3200
    assert sensor.native_unit_of_measurement == CONCENTRATION_PARTS_PER_MILLION


async def test_sensor_native_value_none(
    hass: HomeAssistant,
) -> None:
    """Test sensor native_value when attribute is None."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    obj = PoolObject(
        "SENSE1",
        {
            "OBJTYP": SENSE_TYPE,
            "SNAME": "Air Temp",
            "SOURCE": None,  # No value
        },
    )

    sensor = PoolSensor(
        entry,
        mock_controller,
        obj,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    assert sensor.native_value is None


async def test_sensor_native_value_invalid_returns_string(
    hass: HomeAssistant,
) -> None:
    """Test sensor native_value returns string for non-numeric values."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    obj = PoolObject(
        "SENSE1",
        {
            "OBJTYP": SENSE_TYPE,
            "SNAME": "Air Temp",
            "SOURCE": "N/A",  # Non-numeric value
        },
    )

    sensor = PoolSensor(
        entry,
        mock_controller,
        obj,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    # Should return as string
    assert sensor.native_value == "N/A"


async def test_sensor_is_updated(
    hass: HomeAssistant,
    pool_object_temp_sensor: PoolObject,
) -> None:
    """Test sensor isUpdated method."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_temp_sensor,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    # Should update on SOURCE change
    assert sensor.isUpdated({"SENSE1": {SOURCE_ATTR: "72"}}) is True

    # Should not update on other attribute
    assert sensor.isUpdated({"SENSE1": {"OTHER": "value"}}) is False

    # Should not update on other object
    assert sensor.isUpdated({"SENSE2": {SOURCE_ATTR: "72"}}) is False


async def test_sensor_state_updates(
    hass: HomeAssistant,
    pool_object_temp_sensor: PoolObject,
) -> None:
    """Test sensor state updates from IntelliCenter."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.systemInfo = MagicMock()
    type(mock_controller.systemInfo).usesMetric = property(lambda self: False)

    sensor = PoolSensor(
        entry,
        mock_controller,
        pool_object_temp_sensor,
        device_class=SensorDeviceClass.TEMPERATURE,
        attribute_key=SOURCE_ATTR,
    )

    # Initial value
    assert sensor.native_value == 68

    # Simulate update from IntelliCenter
    updates = {"SENSE1": {SOURCE_ATTR: "72"}}
    assert sensor.isUpdated(updates) is True

    # Apply the update
    pool_object_temp_sensor.update(updates["SENSE1"])

    # Verify value changed
    assert sensor.native_value == 72


async def test_sensor_unique_id_with_attribute(
    hass: HomeAssistant,
    pool_object_pump: PoolObject,
) -> None:
    """Test sensor unique ID includes attribute key."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Power sensor
    power = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=SensorDeviceClass.POWER,
        attribute_key=PWR_ATTR,
    )
    assert power.unique_id == "test_entry_PUMP1PWR"

    # RPM sensor
    rpm = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=None,
        attribute_key=RPM_ATTR,
    )
    assert rpm.unique_id == "test_entry_PUMP1RPM"

    # GPM sensor
    gpm = PoolSensor(
        entry,
        mock_controller,
        pool_object_pump,
        device_class=None,
        attribute_key=GPM_ATTR,
    )
    assert gpm.unique_id == "test_entry_PUMP1GPM"


async def test_ph_sensor_device_class(hass: HomeAssistant) -> None:
    """Test that pH sensors have the correct device class."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Create a chemistry object with pH sensor
    chem_obj = PoolObject(
        "CHEM1",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHEM",
            "SNAME": "IntelliChem",
            PHVAL_ATTR: "7.2",
        },
    )

    sensor = PoolSensor(
        entry,
        mock_controller,
        chem_obj,
        device_class=SensorDeviceClass.PH,
        attribute_key=PHVAL_ATTR,
        name="+ (pH)",
    )

    assert sensor.device_class == SensorDeviceClass.PH
    assert sensor.native_value == 7.2
