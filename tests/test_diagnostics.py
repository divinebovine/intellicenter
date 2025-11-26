"""Test the Pentair IntelliCenter diagnostics."""

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
import pytest

from custom_components.intellicenter import DOMAIN
from custom_components.intellicenter.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.intellicenter.pyintellicenter import PoolModel
from custom_components.intellicenter.pyintellicenter.attributes import (
    BODY_TYPE,
    CIRCUIT_TYPE,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pool_model_for_diagnostics() -> PoolModel:
    """Return a PoolModel for diagnostics testing."""
    model = PoolModel()
    model.addObjects(
        [
            {
                "objnam": "POOL1",
                "params": {
                    "OBJTYP": BODY_TYPE,
                    "SUBTYP": "POOL",
                    "SNAME": "Pool",
                    "STATUS": "ON",
                    "PROPNAME": "My Pool System",
                },
            },
            {
                "objnam": "LIGHT1",
                "params": {
                    "OBJTYP": CIRCUIT_TYPE,
                    "SUBTYP": "INTELLI",
                    "SNAME": "Pool Light",
                    "STATUS": "OFF",
                },
            },
        ]
    )
    return model


async def test_diagnostics_returns_data(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics returns expected data structure."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = False
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert "entry" in result
    assert "system_info" in result
    assert "object_count" in result
    assert "objects" in result


async def test_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics redacts sensitive information."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = False
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    # Check that host is redacted
    assert result["entry"]["data"][CONF_HOST] == "**REDACTED**"

    # Check that PROPNAME in pool objects is redacted
    pool_obj = next(o for o in result["objects"] if o["objnam"] == "POOL1")
    assert pool_obj["properties"].get("PROPNAME") == "**REDACTED**"


async def test_diagnostics_object_count(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics returns correct object count."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = False
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["object_count"] == 2
    assert len(result["objects"]) == 2


async def test_diagnostics_system_info(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics returns system info."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = True
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["system_info"]["sw_version"] == "2.0.0"
    assert result["system_info"]["uses_metric"] is True


async def test_diagnostics_no_handler(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics when handler is not found."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    # Set up without handler
    hass.data[DOMAIN] = {entry.entry_id: {}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert "error" in result
    assert "Handler not found" in result["error"]


async def test_diagnostics_no_entry_data(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics when entry data is not found."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    # Set up without any data
    hass.data[DOMAIN] = {}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert "error" in result
    assert "not found" in result["error"]


async def test_diagnostics_no_system_info(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics when system info is None."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = None
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    # Should still work, just with empty system_info
    assert result["system_info"] == {}
    assert result["object_count"] == 2


async def test_diagnostics_object_details(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics includes correct object details."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.title = "IntelliCenter"
    entry.data = {CONF_HOST: "192.168.1.100"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = False
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    # Find the light object
    light_obj = next(o for o in result["objects"] if o["objnam"] == "LIGHT1")
    assert light_obj["objtype"] == CIRCUIT_TYPE
    assert light_obj["subtype"] == "INTELLI"


async def test_diagnostics_entry_info(
    hass: HomeAssistant,
    pool_model_for_diagnostics: PoolModel,
) -> None:
    """Test diagnostics includes entry info."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_123"
    entry.title = "My IntelliCenter"
    entry.data = {CONF_HOST: "10.0.0.50"}

    mock_handler = MagicMock()
    mock_controller = MagicMock()
    mock_controller.model = pool_model_for_diagnostics
    mock_controller.systemInfo = MagicMock()
    mock_controller.systemInfo.swVersion = "2.0.0"
    mock_controller.systemInfo.usesMetric = False
    mock_handler.controller = mock_controller

    hass.data[DOMAIN] = {entry.entry_id: {"handler": mock_handler}}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["entry_id"] == "test_entry_123"
    assert result["entry"]["title"] == "My IntelliCenter"
    # Host should be redacted
    assert result["entry"]["data"][CONF_HOST] == "**REDACTED**"
