"""End-to-end test that a real Ocado email populates the sensors.

A confirmation email is fed through the mocked IMAP transport so the whole
chain runs for real — triage, parsing, coordinator, entities — and the sensor
states are asserted. The fixture's dates are shifted into the future at runtime
so the delivery survives ``sort_orders`` without freezing the clock.
"""

from datetime import date, timedelta
import imaplib
from pathlib import Path
from unittest.mock import MagicMock, patch

from custom_components.ocado.const import EMPTY_ORDER
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from custom_components.ocado.sensor import OcadoOrderList
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

CONFIRMATION_TEMPLATE = (Path(__file__).parent / "fixtures" / "basic.eml").read_text()


def _ordinal(day: int) -> str:
    """Return the day with its English ordinal suffix, e.g. 21 -> 21st."""
    if 11 <= day % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _future_confirmation_eml() -> bytes:
    """Shift the captured confirmation email to a delivery five days from now."""
    today = date.today()
    delivery = today + timedelta(days=5)
    edit = delivery - timedelta(days=1)
    text = (
        CONFIRMATION_TEMPLATE.replace(
            "Sunday 22 June", f"{delivery:%A} {delivery.day} {delivery:%B}"
        )
        .replace(
            "21st June 2025", f"{_ordinal(edit.day)} {edit:%B} {edit.year}"
        )
        .replace(
            "Mon, 27 May 2025 15:00:00 +0000", f"{today:%a, %d %b %Y} 15:00:00 +0000"
        )
    )
    return text.encode()


def _imap_returning(eml: bytes) -> MagicMock:
    """Build an IMAP class mock whose inbox holds a single message."""
    imap = MagicMock()
    imap.error = imaplib.IMAP4.error
    server = imap.return_value
    server.select.return_value = ("OK", [b"1"])
    server.search.return_value = ("OK", [b"1"])
    server.fetch.return_value = ("OK", [(b"1 (RFC822)", eml)])
    return imap


async def test_confirmation_email_populates_delivery_sensor(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A confirmation email drives the next-delivery sensor state and attributes."""
    delivery = date.today() + timedelta(days=5)
    with patch(
        "custom_components.ocado.utils.imap", _imap_returning(_future_confirmation_eml())
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    coordinator_next = mock_config_entry.runtime_data.data["next"]
    assert coordinator_next.order_number == "1234567891"
    assert coordinator_next.delivery_datetime.date() == delivery

    state = hass.states.get("sensor.ocado_uk_deliveries_next_delivery")
    assert state is not None
    assert state.state == delivery.isoformat()
    assert state.attributes["order_number"] == "1234567891"
    assert state.attributes["estimated_total"] == "63.50"
    assert state.attributes["delivery_window"] == "10:00 - 11:00"

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_orders_sensor_state_is_count(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The orders sensor reports the number of orders as its state."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    coordinator.data = {"orders": [EMPTY_ORDER, EMPTY_ORDER]}
    entity = OcadoOrderList(coordinator)

    entity._handle_coordinator_update()

    assert entity.native_value == 2
