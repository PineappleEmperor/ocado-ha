"""Diagnostics support for the Ocado integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import OcadoConfigEntry

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OcadoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with IMAP credentials redacted."""
    coordinator = entry.runtime_data
    data = dict(coordinator.data) if coordinator.data else {}
    # Raw IMAP message ids are opaque bytes and not useful in diagnostics.
    data.pop("message_ids", None)
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator_data": async_redact_data(data, TO_REDACT),
    }
