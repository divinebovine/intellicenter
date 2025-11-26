"""Config flow for Pentair Intellicenter integration.

This module handles the configuration flow for setting up the IntelliCenter
integration, including manual user setup and Zeroconf discovery.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    CONF_KEEPALIVE_INTERVAL,
    CONF_RECONNECT_DELAY,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_RECONNECT_DELAY,
    DOMAIN,
    MAX_KEEPALIVE_INTERVAL,
    MAX_RECONNECT_DELAY,
    MIN_KEEPALIVE_INTERVAL,
    MIN_RECONNECT_DELAY,
)
from pyintellicenter import BaseController, SystemInfo

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):  # type: ignore[misc]
    """Error to indicate we cannot connect."""


class InvalidHost(HomeAssistantError):  # type: ignore[misc]
    """Error to indicate the host is invalid."""


def _validate_host(host: str) -> str:
    """Validate and return the host address.

    Args:
        host: IP address or hostname to validate.

    Returns:
        The validated host string (stripped of whitespace).

    Raises:
        InvalidHost: If the host is empty or invalid.
    """
    host = host.strip()
    if not host:
        raise InvalidHost("Host cannot be empty")

    # Try to parse as IP address for validation
    try:
        ipaddress.ip_address(host)
    except ValueError as err:
        # Not a valid IP, but could be a hostname
        # Basic hostname validation: must contain at least one character
        # and no spaces
        if " " in host or not host:
            raise InvalidHost(f"Invalid host: {host}") from err

    return host


class ConfigFlow(HAConfigFlow, domain=DOMAIN):  # type: ignore[call-arg, misc]
    """Pentair Intellicenter config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize a new Intellicenter ConfigFlow."""
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    @staticmethod
    @callback  # type: ignore[misc]
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: ConfigType | None = None) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return self._show_setup_form()

        errors: dict[str, str] = {}

        try:
            host = _validate_host(user_input[CONF_HOST])
            system_info = await self._get_system_info(host)

            # Check if already configured
            await self.async_set_unique_id(system_info.uniqueID)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=system_info.propName, data={CONF_HOST: host}
            )
        except AbortFlow:
            raise  # Re-raise abort flow to properly abort
        except InvalidHost:
            errors["base"] = "invalid_host"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self._show_setup_form(errors)

    async def async_step_zeroconf(self, discovery_info: ConfigType) -> FlowResult:
        """Handle device found via zeroconf."""
        _LOGGER.debug(f"zeroconf discovery {discovery_info}")

        host = str(discovery_info.host)

        if self._host_already_configured(host):
            return self.async_abort(reason="already_configured")

        try:
            system_info = await self._get_system_info(host)

            await self.async_set_unique_id(system_info.uniqueID)

            # If there is already a flow for this system, update the host IP address
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

            self._discovered_host = host
            self._discovered_name = system_info.propName

            self.context.update(
                {
                    CONF_HOST: host,
                    CONF_NAME: system_info.propName,
                    "title_placeholders": {"name": system_info.propName},
                }
            )

            return self._show_confirm_dialog()

        except AbortFlow:
            raise  # Re-raise abort flow to properly abort
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

    async def async_step_zeroconf_confirm(
        self, user_input: ConfigType | None = None
    ) -> FlowResult:
        """Handle a flow initiated by zeroconf."""
        if user_input is None:
            return self._show_confirm_dialog()

        host = self._discovered_host or self.context.get(CONF_HOST)
        if host is None:
            return self.async_abort(reason="unknown")

        try:
            system_info = await self._get_system_info(host)

            # Check if already configured
            await self.async_set_unique_id(system_info.uniqueID)
            self._abort_if_unique_id_configured()

        except AbortFlow:
            raise  # Re-raise abort flow to properly abort
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        return self.async_create_entry(
            title=system_info.propName, data={CONF_HOST: host}
        )

    def _show_setup_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors or {},
        )

    def _show_confirm_dialog(self) -> FlowResult:
        """Show the confirm dialog to the user."""
        host = self._discovered_host or self.context.get(CONF_HOST)
        name = self._discovered_name or self.context.get(CONF_NAME)

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": host, "name": name},
        )

    async def _get_system_info(self, host: str) -> SystemInfo:
        """Attempt to connect to the host and retrieve basic system information.

        Args:
            host: The IP address or hostname of the IntelliCenter system.

        Returns:
            SystemInfo object with pool system information.

        Raises:
            CannotConnect: If unable to connect to the IntelliCenter.
        """
        controller = BaseController(host, loop=self.hass.loop)

        try:
            await controller.start()
            if controller.systemInfo is None:
                raise CannotConnect("System info not available")
            return controller.systemInfo
        except (ConnectionRefusedError, OSError, TimeoutError) as err:
            raise CannotConnect from err
        finally:
            controller.stop()

    def _host_already_configured(self, host: str) -> bool:
        """Check if we already have a system with the same host address."""
        existing_hosts = {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries()
            if CONF_HOST in entry.data
        }
        return host in existing_hosts


class OptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
    """Handle options flow for Pentair IntelliCenter integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options for IntelliCenter integration.

        Allows configuration of:
        - Keepalive interval: How often to send keepalive queries
        - Reconnect delay: Initial delay before reconnection attempts
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values or defaults
        current_keepalive = self.config_entry.options.get(
            CONF_KEEPALIVE_INTERVAL, DEFAULT_KEEPALIVE_INTERVAL
        )
        current_reconnect = self.config_entry.options.get(
            CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_KEEPALIVE_INTERVAL,
                        default=current_keepalive,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_KEEPALIVE_INTERVAL,
                            max=MAX_KEEPALIVE_INTERVAL,
                        ),
                    ),
                    vol.Optional(
                        CONF_RECONNECT_DELAY,
                        default=current_reconnect,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_RECONNECT_DELAY,
                            max=MAX_RECONNECT_DELAY,
                        ),
                    ),
                }
            ),
            description_placeholders={
                "host": self.config_entry.data.get(CONF_HOST, "Unknown")
            },
        )
