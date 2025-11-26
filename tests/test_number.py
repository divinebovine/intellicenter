"""Test the Pentair IntelliCenter number platform."""

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, PERCENTAGE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.intellicenter import DOMAIN
from custom_components.intellicenter.number import PoolNumber
from pyintellicenter import (
    BODY_TYPE,
    CHEM_TYPE,
    PRIM_ATTR,
    SEC_ATTR,
    PoolModel,
    PoolObject,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pool_model_with_intellichlor() -> PoolModel:
    """Return a PoolModel with IntelliChlor."""
    model = PoolModel()
    model.addObjects(
        [
            {
                "objnam": "POOL1",
                "params": {
                    "OBJTYP": BODY_TYPE,
                    "SUBTYP": "POOL",
                    "SNAME": "Pool",
                },
            },
            {
                "objnam": "SPA01",
                "params": {
                    "OBJTYP": BODY_TYPE,
                    "SUBTYP": "SPA",
                    "SNAME": "Spa",
                },
            },
            {
                "objnam": "ICHLOR1",
                "params": {
                    "OBJTYP": CHEM_TYPE,
                    "SUBTYP": "ICHLOR",
                    "SNAME": "IntelliChlor",
                    "BODY": "POOL1 SPA01",
                    "PRIM": "50",
                    "SEC": "30",
                },
            },
        ]
    )
    return model


@pytest.fixture
def pool_object_intellichlor() -> PoolObject:
    """Return a PoolObject representing an IntelliChlor."""
    return PoolObject(
        "ICHLOR1",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHLOR",
            "SNAME": "IntelliChlor",
            "BODY": "POOL1 SPA01",
            "PRIM": "50",
            "SEC": "30",
        },
    )


async def test_number_setup_creates_entities(
    hass: HomeAssistant,
    pool_model_with_intellichlor: PoolModel,
) -> None:
    """Test number platform creates entities for IntelliChlor."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_with_intellichlor
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    entities_added = []

    def capture_entities(entities):
        entities_added.extend(entities)

    from custom_components.intellicenter.number import async_setup_entry

    await async_setup_entry(hass, entry, capture_entities)

    # Should create 2 number entities (one for each body)
    assert len(entities_added) == 2


async def test_number_entity_properties_primary(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test PoolNumber entity properties for primary output."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        unit_of_measurement=PERCENTAGE,
        attribute_key=PRIM_ATTR,
        name="+ Output % (Pool)",
    )

    assert number.native_value == 50.0
    assert number._attr_native_unit_of_measurement == PERCENTAGE
    assert number._attr_icon == "mdi:gauge"


async def test_number_entity_properties_secondary(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test PoolNumber entity properties for secondary output."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        unit_of_measurement=PERCENTAGE,
        attribute_key=SEC_ATTR,
        name="+ Output % (Spa)",
    )

    assert number.native_value == 30.0


async def test_number_min_max_step(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test number min/max/step values."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    # Use default values
    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    # Check default values
    assert number._attr_native_min_value == 0
    assert number._attr_native_max_value == 100
    assert number._attr_native_step == 1


async def test_number_custom_min_max_step(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test number with custom min/max/step values."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        min_value=10,
        max_value=90,
        step=5,
        attribute_key=PRIM_ATTR,
    )

    assert number._attr_native_min_value == 10
    assert number._attr_native_max_value == 90
    assert number._attr_native_step == 5


async def test_number_set_value(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test setting number value."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.requestChanges = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    await number.async_set_native_value(75)

    mock_controller.requestChanges.assert_called_once()
    args = mock_controller.requestChanges.call_args[0]
    assert args[0] == "ICHLOR1"
    assert PRIM_ATTR in args[1]
    assert args[1][PRIM_ATTR] == "75"


async def test_number_set_value_secondary(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test setting secondary number value."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.requestChanges = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=SEC_ATTR,
    )

    await number.async_set_native_value(40)

    mock_controller.requestChanges.assert_called_once()
    args = mock_controller.requestChanges.call_args[0]
    assert args[0] == "ICHLOR1"
    assert SEC_ATTR in args[1]
    assert args[1][SEC_ATTR] == "40"


async def test_number_set_value_converts_to_int(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test setting number value converts float to int."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()
    mock_controller.requestChanges = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    await number.async_set_native_value(75.5)

    mock_controller.requestChanges.assert_called_once()
    args = mock_controller.requestChanges.call_args[0]
    # Should convert 75.5 to "75"
    assert args[1][PRIM_ATTR] == "75"


async def test_number_unique_id(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test number unique ID generation."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    # Unique ID should include attribute key since it's not STATUS_ATTR
    assert number.unique_id == "test_entry_ICHLOR1PRIM"


async def test_number_native_value_none(
    hass: HomeAssistant,
) -> None:
    """Test number native_value when attribute is None."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    obj = PoolObject(
        "ICHLOR1",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHLOR",
            "SNAME": "IntelliChlor",
            "PRIM": None,  # No value
        },
    )

    number = PoolNumber(
        entry,
        mock_controller,
        obj,
        attribute_key=PRIM_ATTR,
    )

    assert number.native_value is None


async def test_number_native_value_invalid(
    hass: HomeAssistant,
) -> None:
    """Test number native_value when attribute is invalid."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    obj = PoolObject(
        "ICHLOR1",
        {
            "OBJTYP": CHEM_TYPE,
            "SUBTYP": "ICHLOR",
            "SNAME": "IntelliChlor",
            "PRIM": "invalid",  # Invalid value
        },
    )

    number = PoolNumber(
        entry,
        mock_controller,
        obj,
        attribute_key=PRIM_ATTR,
    )

    assert number.native_value is None


async def test_number_is_updated(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test number isUpdated method."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    # Should update on PRIM change
    assert number.isUpdated({"ICHLOR1": {PRIM_ATTR: "60"}}) is True

    # Should not update on SEC change
    assert number.isUpdated({"ICHLOR1": {SEC_ATTR: "40"}}) is False

    # Should not update on other object
    assert number.isUpdated({"OTHER": {PRIM_ATTR: "60"}}) is False


async def test_number_state_updates(
    hass: HomeAssistant,
    pool_object_intellichlor: PoolObject,
) -> None:
    """Test number state updates from IntelliCenter."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"

    mock_controller = MagicMock()

    number = PoolNumber(
        entry,
        mock_controller,
        pool_object_intellichlor,
        attribute_key=PRIM_ATTR,
    )

    # Initial value
    assert number.native_value == 50.0

    # Simulate update from IntelliCenter
    updates = {"ICHLOR1": {PRIM_ATTR: "75"}}
    assert number.isUpdated(updates) is True

    # Apply the update
    pool_object_intellichlor.update(updates["ICHLOR1"])

    # Verify value changed
    assert number.native_value == 75.0


async def test_number_no_bodies_configured(
    hass: HomeAssistant,
) -> None:
    """Test number setup when no bodies are configured."""
    model = PoolModel()
    model.addObjects(
        [
            {
                "objnam": "ICHLOR1",
                "params": {
                    "OBJTYP": CHEM_TYPE,
                    "SUBTYP": "ICHLOR",
                    "SNAME": "IntelliChlor",
                    "BODY": None,  # No bodies configured
                    "PRIM": "50",
                },
            },
        ]
    )

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = model
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    entities_added = []

    def capture_entities(entities):
        entities_added.extend(entities)

    from custom_components.intellicenter.number import async_setup_entry

    await async_setup_entry(hass, entry, capture_entities)

    # Should create no entities when no bodies configured
    assert len(entities_added) == 0
