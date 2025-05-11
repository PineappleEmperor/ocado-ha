"""Config flow for the Ocado integration."""

from __future__ import annotations
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

from .const import (
    DOMAIN,
    CONF_IMAP_DAYS,
    CONF_IMAP_FOLDER,
    CONF_IMAP_PORT,
    CONF_IMAP_SERVER,
    DEFAULT_IMAP_DAYS,
    DEFAULT_IMAP_FOLDER,
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_SERVER,
    DEFAULT_SCAN_INTERVAL,
    MIN_IMAP_DAYS,
    MIN_SCAN_INTERVAL,
)

from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector
import homeassistant.helpers.config_validation as cv

from .coordinator import OcadoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

OCADO_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_EMAIL,
            description={"suggested_value": ""}
            ): cv.string,
        vol.Required(CONF_PASSWORD, description={"suggested_value": "supersecretstring"}): cv.string,
        vol.Required(CONF_IMAP_SERVER, default=DEFAULT_IMAP_SERVER, description={"suggested_value": DEFAULT_IMAP_SERVER}): cv.string,
        vol.Required(CONF_IMAP_PORT, default=DEFAULT_IMAP_PORT, description={"suggested_value": DEFAULT_IMAP_PORT}): cv.positive_int,
        vol.Required(CONF_IMAP_FOLDER, default=DEFAULT_IMAP_FOLDER, description={"suggested_value": DEFAULT_IMAP_FOLDER}): cv.string,
    }
)

# ----------------------------------------------------------------------------
# Selectors described at
# https://www.home-assistant.io/docs/blueprint/selectors/
# ----------------------------------------------------------------------------
# could include a selector for the imap integration and use that as a way to update more frequently..
# STEP_SETTINGS_DATA_SCHEMA = vol.Schema(
#     {
#         vol.Required(CONF_SENSORS): selector(
#             {"entity": {"filter": {"integration": "imap"}}}
#         ),
#         # Take note of translation key and entry in strings.json and translation files.
#     }
# )


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> bool:
    """Validate the user input allows us to connect."""
    try:
        server = imap(host = data[CONF_IMAP_SERVER], port = data[CONF_IMAP_PORT], timeout = 30)
    except Exception as err:
        raise CannotConnect from err
    try:        
        await server.login(data[CONF_EMAIL], data[CONF_PASSWORD])
    except Exception as err:
        raise InvalidAuth from err
    try:
        server.select(data[CONF_IMAP_FOLDER], readonly=True)
        check = server.check()
        server.close()
        server.logout()
    except Exception:
        raise Exception
    if check != ('OK', [b'Success']):
        raise Exception
    return {"title": f"Ocado Integration - {data[CONF_EMAIL]}:{data[CONF_IMAP_SERVER]}"}


async def _validate_options(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate options."""
    if data[CONF_SCAN_INTERVAL] < 60:
        raise ValueError(f"Scan interval is too low, minimum is 60 {data[CONF_SCAN_INTERVAL]}")
    if data[CONF_IMAP_DAYS] < 7:
        raise ValueError(f"Number of days to fetch is too low, minimum is 7 {data[CONF_IMAP_DAYS]}")
    return {"title": f"Ocado Integration - {data[CONF_EMAIL]}:{data[CONF_IMAP_SERVER]}"}


# async def validate_settings(hass: HomeAssistant, data: dict[str, Any]) -> bool:
#     """Another validation method for our config steps."""
#     return True


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
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OcadoOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("User input received: %s", user_input)
            # The form has been filled in and submitted, so process the data provided.
            try:                
                info = await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            
            # The errors["base"] values match the values in your strings.json and translation files.
            if "base" not in errors:
                # Validation was successful, so proceed to the next step.
                # Set the unique ID
                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()

                # Set our title variable here for use later
                self._title = info.get("title")
                # save the input data for use later
                self._input_data = user_input

                # Call the next step
                return await self.async_step_settings()

        # Show initial form.
        return self.async_show_form(
            step_id="user",
            data_schema=OCADO_SETTINGS_SCHEMA,
            errors=errors,
            last_step=False,  # Adding last_step True/False decides whether form shows Next or Submit buttons
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step. Creates config entry."""

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            # if not await _validate_input(self.hass, user_input):
            #     errors["base"] = "invalid_settings"

            # if "base" not in errors:
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
        existing_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if existing_entry is None:
            _LOGGER.error("Reconfiguration failed: Config entry not found.")
            return self.async_abort(reason="Reconfigure Failed")

        if user_input is not None:
            _LOGGER.debug("Reconfigure user input: %s", user_input)
            try:
                info = await _validate_input(self.hass, user_input)
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


class OcadoOptionsFlowHandler(OptionsFlow):
    """Handles the options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Handle options flow."""

        return self.async_show_menu(
            step_id="init",
            menu_options=["intervals"],
        )

    async def async_step_intervals(self, user_input=None):
        """Handle menu intervals flow."""
        if user_input is not None:
            options = self.config_entry.options | user_input
            return self.async_create_entry(title="", data=options)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))),
                vol.Optional(
                    CONF_IMAP_DAYS,
                    default=self.options.get(CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS),
                ): (vol.All(vol.Coerce(int), vol.Clamp(min=MIN_IMAP_DAYS))),
            }
        )

        return self.async_show_form(step_id="intervals", data_schema=data_schema)

    # async def async_step_option2(self, user_input=None):
    #     """Handle menu option 2 flow.

    #     In this option, we show how to use dynamic data in a selector.
    #     """
    #     if user_input is not None:
    #         options = self.config_entry.options | user_input
    #         return self.async_create_entry(title="", data=options)

    #     coordinator: ExampleCoordinator = self.hass.data[DOMAIN][
    #         self.config_entry.entry_id
    #     ].coordinator
    #     devices = coordinator.data
    #     data_schema = vol.Schema(
    #         {
    #             vol.Optional(CONF_CHOOSE, default=devices[0]["device_name"]): selector(
    #                 {
    #                     "select": {
    #                         "options": [device["device_name"] for device in devices],
    #                         "mode": "dropdown",
    #                         "sort": True,
    #                     }
    #                 }
    #             ),
    #         }
    #     )

    #     return self.async_show_form(step_id="option2", data_schema=data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
