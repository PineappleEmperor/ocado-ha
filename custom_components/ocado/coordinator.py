"""DataUpdateCoordinator for our integration."""

from datetime import timedelta, date
import logging
from typing import Any
from imaplib import IMAP4_SSL as imap

from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import (
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_IMAP_SERVER,
    CONF_IMAP_PORT,
    CONF_IMAP_FOLDER,
    CONF_IMAP_SSL,
    CONF_IMAP_DAYS,
    CONF_EMAIL,
    CONF_PASSWORD,
    DATA_NETWORK_INFO,
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


_LOGGER = logging.getLogger(__name__)

@callback
@bind_hass
def get_network_info(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return Host Network information.

    Async friendly.
    """
    return hass.data.get(DATA_NETWORK_INFO)

class OcadoUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage all the data from Ocado emails."""
    data: list[dict[str, Any]]

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        # Set variables from values entered in config flow setup
        self._hass = hass
        self.session = async_get_clientsession(self._hass)
        self.email_address = config_entry.data[CONF_EMAIL]
        self.password = config_entry.data[CONF_PASSWORD]
        self.imap_host = config_entry.data[CONF_IMAP_HOST]
        self.imap_port = config_entry.data[CONF_IMAP_PORT]
        self.imap_folder = config_entry.data[CONF_IMAP_FOLDER]
        self.imap_ssl = config_entry.data[CONF_IMAP_SSL]
        self.imap_days = config_entry.data[CONF_IMAP_DAYS]
        self.confirmation_flag = [u'SINCE', date.today() - timedelta(days=self.imap_days), u'FROM', 'customerservices@ocado.com', u'SUBJECT','Confirmation of your order']
                
        # set variables from options. You need a default here in case options have not been set
        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, 300
        )

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}",# ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
            always_update = True,
        )

    async def async_update_data(self):
        """Fetch data from the IMAP server and filter the emails for Ocado ones."""        
        server = imap(self.imap_host)
        server.login(self.email_address,self.password)

        # Add a way to determine if a BBD is needed -> delivery within 7days?
        # Retrieve all the Ocado order confirmations from the last imap_days
        try:
            result, message_ids = server.search(None,,readonly=True)
        except:
        
        try:
            data = await self.hass.async_add_executor_job(self.api.get_data)
        except APIConnectionError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        except Exception as err:
            # This will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # What is returned here is stored in self.data by the DataUpdateCoordinator
        return data
    # ----------------------------------------------------------------------------
    # Here we add some custom functions on our data coordinator to be called
    # from entity platforms to get access to the specific data they want.
    #
    # These will be specific to your api or yo may not need them at all
    # ----------------------------------------------------------------------------
    # def get_device(self, device_id: int) -> dict[str, Any]:
    #     """Get a device entity from our api data."""
    #     try:
    #         return [
    #             devices for devices in self.data if devices["device_id"] == device_id
    #         ][0]
    #     except (TypeError, IndexError):
    #         # In this case if the device id does not exist you will get an IndexError.
    #         # If api did not return any data, you will get TypeError.
    #         return None

    # def get_device_parameter(self, device_id: int, parameter: str) -> Any:
    #     """Get the parameter value of one of our devices from our api data."""
    #     if device := self.get_device(device_id):
    #         return device.get(parameter)
