"""DataUpdateCoordinator for our integration."""

from datetime import timedelta, date
import logging
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from .const import (
    OCADO_ADDRESS,
    OCADO_CONFIRMATION_SUBJECT,
    CONF_IMAP_SERVER,
    CONF_IMAP_PORT,
    CONF_IMAP_FOLDER,
    CONF_IMAP_SSL,
    CONF_IMAP_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_IMAP_DAYS
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .utils import (
    email_triage,
    order_parse,
    get_window,
    sort_orders
)

_LOGGER = logging.getLogger(__name__)
type OcadoConfigEntry = ConfigEntry(OcadoUpdateCoordinator)


class OcadoUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage all the data from Ocado emails."""
    # data: list[dict[str, Any]]

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the data update coordinator."""
        # Set variables from values entered in config flow setup
        self._hass          = hass
        self.email_address  = config_entry.data[CONF_EMAIL]
        self.password       = config_entry.data[CONF_PASSWORD]
        self.imap_host      = config_entry.data[CONF_IMAP_SERVER]
        self.imap_port      = config_entry.data[CONF_IMAP_PORT]
        self.imap_folder    = config_entry.data[CONF_IMAP_FOLDER]
        # self.imap_ssl     = config_entry.data[CONF_IMAP_SSL]
        # self.imap_days    = config_entry.data[CONF_IMAP_DAYS]
                
        # Set variables from options
        self.scan_interval  = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.imap_days      = config_entry.options.get(CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS)

        super().__init__(
            hass,
            _LOGGER,
            name            = f"{DOMAIN}",
            config_entry    = config_entry,
            update_method   = self.async_update_data,
            update_interval = timedelta(seconds=self.scan_interval),
            always_update   = True,
        )

    async def async_update_data(self):
        """Fetch data from the IMAP server and filter the emails for Ocado ones."""        
        try:            
            # Add a way to determine if a BBD is needed -> delivery within 7days?
            # Retrieve all the Ocado order confirmations from the last imap_days
            triaged_emails = email_triage(self)
            orders         = []
            for order in triaged_emails.confirmations:
                order = order_parse(order)
                orders.append(vars(order))
            if len(orders) > 0:
                next, upcoming = sort_orders(orders)
            else:
                next            = None
                upcoming        = None
                orders          = None
            # If there has been a recent delivery, add it as recent.
            if triaged_emails.receipts:
                recent          = vars(triaged_emails.receipts)
            else:
                recent          = None
            payload_raw = {
                    "next"      : next,
                    "upcoming"  : upcoming,
                    "recent"    : recent,
                    "orders"    : orders,
                }
            return json.dumps(payload_raw)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
