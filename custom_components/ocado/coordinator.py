"""DataUpdateCoordinator for our integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import IntegrationNotLoaded, async_get_loaded_integration

from .const import (
    CONF_IMAP_DAYS,
    CONF_IMAP_FOLDER,
    CONF_IMAP_PORT,
    CONF_IMAP_SERVER,
    DEFAULT_IMAP_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAILURES_BEFORE_REPAIR,
    FAILURES_BEFORE_WARNING,
    OcadoAuthError,
)
from .utils import email_triage, order_parse, sort_orders, total_parse, voucher_parse

_LOGGER = logging.getLogger(__name__)

type OcadoConfigEntry = ConfigEntry[OcadoUpdateCoordinator]


class OcadoUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage all the data from Ocado emails."""

    def __init__(self, hass: HomeAssistant, config_entry: OcadoConfigEntry) -> None:
        """Initialize the data update coordinator."""
        # Set connection variables from the config entry data
        self.email_address  : str  = config_entry.data[CONF_EMAIL]
        self.password       : str  = config_entry.data[CONF_PASSWORD]
        self.imap_host      : str  = config_entry.data[CONF_IMAP_SERVER]
        self.imap_port      : int  = config_entry.data[CONF_IMAP_PORT]
        self.imap_folder    : str  = config_entry.data[CONF_IMAP_FOLDER]

        # Set variables from options
        self.scan_interval  : int  = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.imap_days      : int  = config_entry.options.get(CONF_IMAP_DAYS, DEFAULT_IMAP_DAYS)

        # Surface the integration version as the device firmware version.
        try:
            version = async_get_loaded_integration(hass, DOMAIN).version
            self.version: str = str(version) if version else "unknown"
        except IntegrationNotLoaded:
            self.version = "unknown"

        # Consecutive failures while holding cached data; drives log escalation
        # and the repair issue keyed on this entry.
        self._consecutive_failures = 0
        self._entry_id = config_entry.entry_id

        super().__init__(
            hass,
            _LOGGER,
            name            = DOMAIN,
            config_entry    = config_entry,
            update_method   = self.async_update_data,
            update_interval = timedelta(seconds=self.scan_interval),
            always_update   = False,
        )

    async def async_update_data(self) -> dict[str, Any]:
        """Fetch data from the IMAP server and filter the emails for Ocado ones."""
        _LOGGER.debug("Beginning coordinator update")

        try:
            # Retrieve all the Ocado order confirmations from the last imap_days, will return None if there are no new emails.
            # email_triage does blocking imaplib I/O, so run it in the executor to keep it off the event loop.
            message_ids, triaged_emails = await self.hass.async_add_executor_job(email_triage, self)
            if triaged_emails is None:
                _LOGGER.debug("No new emails found, returning cached data")
                self._mark_success()
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
            # If there has been a recent delivery, add the total.
            if triaged_emails.total is not None:
                try:
                    order           = total_parse(triaged_emails.total)
                    total           = order
                except Exception:  # noqa: BLE001
                    total = None
            else:
                _LOGGER.debug("No new total email found.")
                total               = None
            if triaged_emails.voucher is not None:
                try:
                    voucher         = voucher_parse(triaged_emails.voucher)
                except Exception:  # noqa: BLE001
                    voucher         = None
            else:
                _LOGGER.debug("No voucher email found.")
                voucher             = None
        except OcadoAuthError as err:
            # Bad credentials never resolve themselves; trigger reauth immediately.
            raise ConfigEntryAuthFailed("IMAP authentication failed") from err
        except Exception as err:
            # Cold start with nothing cached: fail setup so the entry retries.
            if self.data is None:
                raise UpdateFailed(f"Error fetching data: {err}") from err
            # An Ocado delivery stays relevant for days, so a transient fetch
            # error (network blip, mail host down) must not blank the sensors.
            # Hold the cached data and stay available; escalate the log so a
            # persistent failure is still visible.
            self._consecutive_failures += 1
            if self._consecutive_failures >= FAILURES_BEFORE_REPAIR:
                _LOGGER.warning(
                    "Ocado data has not refreshed for %s consecutive polls: %s",
                    self._consecutive_failures, err,
                )
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    self._issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="refresh_failing",
                    translation_placeholders={
                        "failures": str(self._consecutive_failures),
                        "error": str(err),
                    },
                )
            elif self._consecutive_failures >= FAILURES_BEFORE_WARNING:
                _LOGGER.warning(
                    "Ocado data has not refreshed for %s consecutive polls: %s",
                    self._consecutive_failures, err,
                )
            else:
                _LOGGER.debug("Keeping cached Ocado data after fetch error: %s", err)
            return self.data
        else:
            self._mark_success()
            return {
                "message_ids": message_ids,
                "next": next_order,
                "upcoming": upcoming_order,
                "total": total,
                "voucher": voucher,
                "orders": orders,
            }

    @property
    def _issue_id(self) -> str:
        """Stable repair-issue id for this config entry."""
        return f"refresh_failing_{self._entry_id}"

    def _mark_success(self) -> None:
        """Reset the failure counter and clear any open repair issue."""
        if self._consecutive_failures:
            self._consecutive_failures = 0
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
