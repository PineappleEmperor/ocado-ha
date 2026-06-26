"""Config flow for the Ocado integration."""

from __future__ import annotations

from collections.abc import Mapping
from imaplib import IMAP4_SSL as imap
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DELIVERY_TITLE,
    CONF_EDIT_TITLE,
    CONF_IMAP_DAYS,
    CONF_IMAP_FOLDER,
    CONF_IMAP_PORT,
    CONF_IMAP_SERVER,
    DEFAULT_DELIVERY_TITLE,
    DEFAULT_EDIT_TITLE,
    DEFAULT_IMAP_DAYS,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_SERVER,
    DEFAULT_SCAN_INTERVAL,
    DELIVERY_TITLE_TOKENS,
    DOMAIN,
    EDIT_TITLE_TOKENS,
    MIN_IMAP_DAYS,
    MIN_SCAN_INTERVAL,
)
from .utils import validate_title_template

_LOGGER = logging.getLogger(__name__)

OCADO_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_EMAIL,
            description={"suggested_value": ""}
            ): cv.string,
        vol.Required(
            CONF_PASSWORD,
            description={"suggested_value": "supersecretstring"}
            ): cv.string,
        vol.Required(
            CONF_IMAP_SERVER,
            default=DEFAULT_IMAP_SERVER,
            description={"suggested_value": DEFAULT_IMAP_SERVER}
            ): cv.string,
        vol.Required(
            CONF_IMAP_PORT,
            default=DEFAULT_IMAP_PORT,
            description={"suggested_value": DEFAULT_IMAP_PORT}
            ): cv.positive_int,
        vol.Required(
            CONF_IMAP_FOLDER,
            default=DEFAULT_IMAP_FOLDER,
            description={"suggested_value": DEFAULT_IMAP_FOLDER}
            ): cv.string,
    }
)


def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect (blocking; run via executor)."""
    try:
        _LOGGER.debug("Testing IMAP server with host: %s, port: %s", data[CONF_IMAP_SERVER], data[CONF_IMAP_PORT])
        server = imap(host = data[CONF_IMAP_SERVER], port = data[CONF_IMAP_PORT], timeout = 30)
    except Exception as err:
        raise CannotConnect from err
    try:
        _LOGGER.debug("Testing IMAP server login with email: %s", data[CONF_EMAIL])
        server.login(data[CONF_EMAIL], data[CONF_PASSWORD])
    except Exception as err:
        raise InvalidAuth from err
    try:
        _LOGGER.debug("Selecting IMAP folder: %s", data[CONF_IMAP_FOLDER])
        server.select(data[CONF_IMAP_FOLDER], readonly=True)
        _LOGGER.debug("Requesting IMAP server check")
        check = server.check()
        server.close()
        server.logout()
    except Exception as err:
        _LOGGER.exception("Failed to select imap folder or check")
        raise CannotConnect from err
    _LOGGER.debug("Checking the check: %s", check)
    if not check or check[0] != 'OK':
        _LOGGER.error("Check failed")
        raise CannotConnect("IMAP check failed")
    return {"title": "Ocado UK"}
    # return {"title": f"Ocado Integration - {data[CONF_EMAIL]}:{data[CONF_IMAP_SERVER]}"}


async def _validate_options(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate options."""
    if data[CONF_SCAN_INTERVAL] < 60:
        raise ValueError(f"Scan interval is too low, minimum is 60 {data[CONF_SCAN_INTERVAL]}")
    if data[CONF_IMAP_DAYS] < 7:
        raise ValueError(f"Number of days to fetch is too low, minimum is 7 {data[CONF_IMAP_DAYS]}")
    validate_title_template(data[CONF_DELIVERY_TITLE], DELIVERY_TITLE_TOKENS)
    validate_title_template(data[CONF_EDIT_TITLE], EDIT_TITLE_TOKENS)
    return {"title": "Ocado UK"}
    # return {"title": f"Ocado Integration - {data[CONF_EMAIL]}:{data[CONF_IMAP_SERVER]}"}


class OcadoConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ocado Integration."""

    VERSION = 1
    MINOR_VERSION = 0
    _input_data: dict[str, Any]
    _title: str

    def __init__(self) -> None:
        """Initialize the flow."""
        self._email         : str | None = None
        self._password      : str | None = None
        self._imap_server   : str | None = None
        self._imap_port     : int | None = None
        self._imap_folder   : str | None = None
        self._error         : str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OcadoOptionsFlowHandler:
        """Get the options flow for this handler."""
        return OcadoOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            _LOGGER.debug("User input received: %s", user_input)
            try:
                info = await self.hass.async_add_executor_job(_validate_input, self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Validation was successful, so proceed to the next step.
                # Set the unique ID
                title = info.get("title") or "Ocado UK"
                _LOGGER.debug("Setting unique ID")
                await self.async_set_unique_id(title)
                self._abort_if_unique_id_configured()

                # Set our title variable here for use later
                self._title = title
                # save the input data for use later
                self._input_data = user_input

                # Call the next step
                # return await self.async_step_settings()
                return self.async_create_entry(title=self._title, data=self._input_data)

        # Show initial form.
        return self.async_show_form(
            step_id="user",
            data_schema=OCADO_SETTINGS_SCHEMA,
            errors=errors,
            last_step=True,  # Adding last_step True/False decides whether form shows Next or Submit buttons
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step. Creates config entry."""

        errors: dict[str, str] = {}

        if self._input_data is not None:
            # if "base" not in errors:
            if user_input is not None:
                self._input_data.update(user_input)
            return self.async_create_entry(title=self._title, data=self._input_data)

        return self.async_show_form(
            step_id="user",# "settings"
            data_schema=OCADO_SETTINGS_SCHEMA,
            errors=errors,
            last_step=True,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        errors: dict[str, str] = {}
        entry_id = self.context.get("entry_id")
        if not entry_id:
            _LOGGER.error("Reconfiguration failed: entry ID not found.")
            return self.async_abort(reason="Reconfigure Failed")
        existing_entry = self.hass.config_entries.async_get_entry(entry_id)
        if existing_entry is None:
            _LOGGER.error("Reconfiguration failed: Config entry not found.")
            return self.async_abort(reason="Reconfigure Failed: entry missing")

        if user_input is not None:
            _LOGGER.debug("Reconfigure user input: %s", user_input)
            try:
                await self.hass.async_add_executor_job(_validate_input, self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                _LOGGER.info(
                    "Configuration updated for entry: %s", existing_entry.entry_id
                )
                return self.async_update_reload_and_abort(
                    existing_entry,
                    unique_id=existing_entry.unique_id,
                    data={**existing_entry.data, **user_input},
                    reason="reconfigure_successful",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=OCADO_SETTINGS_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when IMAP credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with an updated password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                await self.hass.async_add_executor_job(_validate_input, self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data=data,
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): cv.string}),
            description_placeholders={"email": reauth_entry.data.get(CONF_EMAIL, "")},
            errors=errors,
        )


class OcadoOptionsFlowHandler(OptionsFlow):
    """Handles the options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle options flow."""

        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("User options received: %s", user_input)
            try:
                await _validate_options(self.hass, user_input)
            except ValueError:
                errors["base"] = "value_error"
            if "base" not in errors:
                return self.async_create_entry(data=user_input)

        OCADO_OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))),
                vol.Optional(
                    CONF_IMAP_DAYS,
                    default=self.options.get(CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_IMAP_DAYS))),
                vol.Optional(
                    CONF_DELIVERY_TITLE,
                    default=self.options.get(CONF_DELIVERY_TITLE, DEFAULT_DELIVERY_TITLE),
                ): cv.string,
                vol.Optional(
                    CONF_EDIT_TITLE,
                    default=self.options.get(CONF_EDIT_TITLE, DEFAULT_EDIT_TITLE),
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OCADO_OPTIONS_SCHEMA,
                self.config_entry.options
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
