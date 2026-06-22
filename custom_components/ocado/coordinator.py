"""DataUpdateCoordinator for our integration."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .utils import email_triage, order_parse, sort_orders, total_parse, voucher_parse

_LOGGER = logging.getLogger(__name__)


class OcadoUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage all the data from Ocado emails."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the data update coordinator."""
        # assert self._config_entry is not None

        # Set variables from options
        self.scan_interval  : int  = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.imap_days      : int  = config_entry.options.get(CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS)

        super().__init__(
            hass,
            _LOGGER,
            name            = DOMAIN,
            config_entry    = config_entry,
            update_method   = self.async_update_data,
            update_interval = timedelta(seconds=self.scan_interval),
            always_update   = True,
        )

        # Set variables from services
        # self.last_uploaded_file: OcadoReceipt | None = None

    async def async_update_data(self) -> dict[str, Any]:
        """Fetch data from the IMAP server and filter the emails for Ocado ones."""
        _LOGGER.debug("Beginning coordinator update")

        try:
            # Retrieve all the Ocado order confirmations from the last imap_days, will return None if there are no new emails
            message_ids, triaged_emails = email_triage(self)
            if triaged_emails is None:
                _LOGGER.debug("No new emails found, returning cached data")
                return self.data
            orders                  = []
            for order in triaged_emails.confirmations:
                order = order_parse(order)
                orders.append(order)
            if len(orders) > 0:
                next_order, upcoming_order = sort_orders(orders)
            else:
                next_order          = None
                upcoming_order      = None
                orders              = None
            # Need to add a way to return old version by default
            # if self.last_uploaded_file:
            #     # Example: parse/process the uploaded file
            #     receipt_bbds = self.last_uploaded_file
            # else:
            #     receipt_bbds = None
            # If there has been a recent delivery, add it as recent.
            # if triaged_emails.receipt is not None:
            #     try:
            #         # order           = receipt_parse(triaged_emails.receipt)
            #         receipt         = triaged_emails.receipt
            #         if receipt_bbds:
            #             receipt.update_from(receipt_bbds)
            #     except Exception:
            #         receipt         = None
            # else:
            #     _LOGGER.info("No receipt email found.")
            #     receipt             = None
            # If there has been a recent delivery, add the total.
            if triaged_emails.total is not None:
                try:
                    order           = total_parse(triaged_emails.total)
                    total           = order
                except Exception:  # noqa: BLE001
                    total = None
            else:
                _LOGGER.info("No receipt email found.")
                total               = None
            if triaged_emails.voucher is not None:
                try:
                    voucher         = voucher_parse(triaged_emails.voucher)
                except Exception:  # noqa: BLE001
                    voucher         = None
            else:
                _LOGGER.info("No voucher email found.")
                voucher             = None
            return {
                    "updated"       : datetime.now(timezone.utc),
                    "message_ids"   : message_ids,
                    "next"          : next_order,
                    "upcoming"      : upcoming_order,
                    "total"         : total,
                    # "receipt"       : receipt,
                    "voucher"       : voucher,
                    "orders"        : orders,
                }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
