"""Test the Pentair IntelliCenter integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import pytest

from custom_components.intellicenter import (
    DOMAIN,
    PLATFORMS,
    PoolConnectionHandler,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)

pytestmark = pytest.mark.asyncio


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the async_setup function."""
    result = await async_setup(hass, {})
    assert result is True


async def test_async_setup_entry_success(
    hass: HomeAssistant, mock_model_controller: MagicMock
) -> None:
    """Test successful setup of a config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_HOST: "192.168.1.100"}
    entry.options = {}  # No custom options, will use defaults
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()

    # Mock the handler's start method
    with patch(
        "custom_components.intellicenter.ModelController"
    ) as mock_controller_class:
        mock_controller = MagicMock()
        mock_controller.systemInfo.propName = "Test Pool System"
        mock_controller.model = MagicMock()
        mock_controller.model.__iter__ = MagicMock(return_value=iter([]))
        mock_controller_class.return_value = mock_controller

        # Create a MockPoolConnectionHandler class with async methods
        class MockPoolConnectionHandler:
            """Mock PoolConnectionHandler for testing."""

            def __init__(self, hass, entry_id, controller, *args, **kwargs):
                self.controller = controller

            async def start(self):
                """Mock async start method that calls started callback."""
                # Call the started callback to trigger platform setup
                if hasattr(self, "started"):
                    self.started(self.controller)

            def stop(self):
                """Mock stop method."""
                pass

            def reconnected(self, controller):
                """Mock reconnected callback."""
                pass

            def updated(self, controller, updates):
                """Mock updated callback."""
                pass

        with patch(
            "custom_components.intellicenter.PoolConnectionHandler",
            MockPoolConnectionHandler,
        ):
            with patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ) as mock_forward:
                result = await async_setup_entry(hass, entry)

                assert result is True
                assert DOMAIN in hass.data
                assert entry.entry_id in hass.data[DOMAIN]

                # Wait a bit for the async task to complete
                await hass.async_block_till_done()

                # Verify platforms were set up
                mock_forward.assert_called_once_with(entry, PLATFORMS)


async def test_async_setup_entry_connection_failed(hass: HomeAssistant) -> None:
    """Test setup fails when connection is refused."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_HOST: "192.168.1.100"}
    entry.options = {}  # No custom options, will use defaults

    with patch(
        "custom_components.intellicenter.ModelController"
    ) as mock_controller_class:
        mock_controller = MagicMock()
        mock_controller_class.return_value = mock_controller

        # Create a MockPoolConnectionHandler class that raises ConnectionRefusedError
        class MockPoolConnectionHandler:
            """Mock PoolConnectionHandler that fails to connect."""

            def __init__(self, hass, entry_id, controller, *args, **kwargs):
                self.controller = controller

            async def start(self):
                """Mock async start that raises ConnectionRefusedError."""
                raise ConnectionRefusedError()

        with patch(
            "custom_components.intellicenter.PoolConnectionHandler",
            MockPoolConnectionHandler,
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, entry)


async def test_async_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading a config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Test Pool System"
    entry.data = {CONF_HOST: "192.168.1.100"}

    # Set up the handler in hass.data with new structure
    mock_handler = MagicMock()
    mock_handler.stop = MagicMock()
    mock_stop_listener = MagicMock()
    hass.data[DOMAIN] = {
        entry.entry_id: {"handler": mock_handler, "stop_listener": mock_stop_listener}
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=lambda: AsyncMock(return_value=True),
    ) as mock_unload:
        result = await async_unload_entry(hass, entry)

        # Verify async_unload_platforms was called with entry and platforms
        mock_unload.assert_called_once_with(entry, PLATFORMS)

        # Verify handler was stopped
        mock_handler.stop.assert_called_once()

        # Verify entry was removed from hass.data (domain should be deleted if empty)
        assert DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]

        assert result is True


async def test_async_unload_entry_platforms_fail(hass: HomeAssistant) -> None:
    """Test unload returns False when platforms fail to unload."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Test Pool System"
    entry.data = {CONF_HOST: "192.168.1.100"}

    # Set up the handler in hass.data with new structure
    mock_handler = MagicMock()
    mock_stop_listener = MagicMock()
    hass.data[DOMAIN] = {
        entry.entry_id: {"handler": mock_handler, "stop_listener": mock_stop_listener}
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=lambda: AsyncMock(
            return_value=False
        ),  # Simulate platform unload failure
    ):
        result = await async_unload_entry(hass, entry)

        # Handler should still be stopped even if platforms fail
        mock_handler.stop.assert_called_once()

        # Entry should still be removed (domain should be deleted if empty)
        assert DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]

        # Now returns False when platforms fail to unload
        assert result is False


# -------------------------------------------------------------------------------------
# PoolConnectionHandler Tests
# -------------------------------------------------------------------------------------


class TestPoolConnectionHandler:
    """Tests for the PoolConnectionHandler class."""

    async def test_signal_names(self, hass: HomeAssistant) -> None:
        """Test that signal names are correctly generated."""
        mock_controller = MagicMock()
        entry_id = "test_entry_123"

        handler = PoolConnectionHandler(
            hass, entry_id, mock_controller, timeBetweenReconnects=30
        )

        assert handler.update_signal == f"{DOMAIN}_UPDATE_{entry_id}"
        assert handler.connection_signal == f"{DOMAIN}_CONNECTION_{entry_id}"

    async def test_started_logs_system_info(
        self, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that started() logs the system name."""
        mock_controller = MagicMock()
        mock_controller.systemInfo.propName = "My Test Pool"
        mock_controller.model = MagicMock()
        mock_controller.model.__iter__ = MagicMock(return_value=iter([]))

        handler = PoolConnectionHandler(
            hass, "test_entry", mock_controller, timeBetweenReconnects=30
        )

        handler.started(mock_controller)

        assert "connected to system: 'My Test Pool'" in caplog.text

    async def test_started_handles_missing_system_info(
        self, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that started() handles missing system info gracefully."""
        mock_controller = MagicMock()
        mock_controller.systemInfo = None

        handler = PoolConnectionHandler(
            hass, "test_entry", mock_controller, timeBetweenReconnects=30
        )

        # Should not raise an exception
        handler.started(mock_controller)

        assert "connected to system: 'Unknown'" in caplog.text

    async def test_reconnected_sends_signal(self, hass: HomeAssistant) -> None:
        """Test that reconnected() sends the connection signal."""
        mock_controller = MagicMock()
        mock_controller.systemInfo.propName = "My Test Pool"
        entry_id = "test_entry"

        handler = PoolConnectionHandler(
            hass, entry_id, mock_controller, timeBetweenReconnects=30
        )

        signal_received = []

        async def signal_handler(is_connected: bool) -> None:
            signal_received.append(is_connected)

        hass.helpers.dispatcher.async_dispatcher_connect(
            handler.connection_signal, signal_handler
        )

        handler.reconnected(mock_controller)
        await hass.async_block_till_done()

        assert signal_received == [True]

    async def test_disconnected_sends_signal(self, hass: HomeAssistant) -> None:
        """Test that disconnected() sends the connection signal."""
        mock_controller = MagicMock()
        mock_controller.systemInfo.propName = "My Test Pool"
        entry_id = "test_entry"

        handler = PoolConnectionHandler(
            hass, entry_id, mock_controller, timeBetweenReconnects=30
        )

        signal_received = []

        async def signal_handler(is_connected: bool) -> None:
            signal_received.append(is_connected)

        hass.helpers.dispatcher.async_dispatcher_connect(
            handler.connection_signal, signal_handler
        )

        handler.disconnected(mock_controller, None)
        await hass.async_block_till_done()

        assert signal_received == [False]

    async def test_updated_sends_signal(self, hass: HomeAssistant) -> None:
        """Test that updated() sends the update signal with updates."""
        mock_controller = MagicMock()
        entry_id = "test_entry"

        handler = PoolConnectionHandler(
            hass, entry_id, mock_controller, timeBetweenReconnects=30
        )

        signal_received = []
        test_updates = {"obj1": {"attr1": "val1"}}

        async def signal_handler(updates: dict) -> None:
            signal_received.append(updates)

        hass.helpers.dispatcher.async_dispatcher_connect(
            handler.update_signal, signal_handler
        )

        handler.updated(mock_controller, test_updates)
        await hass.async_block_till_done()

        assert signal_received == [test_updates]

    async def test_custom_reconnect_delay(self, hass: HomeAssistant) -> None:
        """Test that custom reconnect delay is used."""
        mock_controller = MagicMock()

        handler = PoolConnectionHandler(
            hass, "test_entry", mock_controller, timeBetweenReconnects=60
        )

        # Check that the delay was passed to the parent class
        assert handler._timeBetweenReconnects == 60
