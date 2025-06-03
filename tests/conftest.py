"""Fixtures for testing."""

import pytest
import logging
# from email import message_from_bytes
# from pathlib import Path
# from homeassistant.setup import async_setup_component
# from homeassistant.helpers import entity_component
from custom_components.ocado.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry
# from unittest.mock import AsyncMock, MagicMock, patch

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def mock_config_entry(hass):
    """Return a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ocado",
        data={
            "email": "test@example.com",
            "password": "password123",
            "imap_host": "imap.test.com",
            "imap_port": 993,
            "imap_folder": "INBOX",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def init_integration(hass, mock_config_entry):
    """Set up the Ocado integration for testing."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state == ConfigEntryState.LOADED
    return mock_config_entry


# @pytest.fixture
# def example_ocado_email():
#     email_path = Path(__file__).parent / "fixtures" / "basic.eml"
#     raw_bytes = email_path.read_bytes()
#     return raw_bytes


# @pytest.fixture(autouse=True)
# def mock_imaplib(example_ocado_email):
#     """Auto-mock imaplib.IMAP4_SSL used inside utils.py."""
#     with patch("custom_components.ocado.utils.imap") as mock_imap:
#         imap_instance = MagicMock()
#         imap_instance.login.return_value = ("OK", [b"Logged in"])
#         imap_instance.select.return_value = ("OK", [b"1"])
#         imap_instance.search.return_value = ("OK", [b"1"])
#         imap_instance.fetch.return_value = ("OK", [(b"1 (RFC822)", example_ocado_email)])
#         mock_imap.return_value = imap_instance
#         yield mock_imap


# @patch("custom_components.your_integration.api.OcadoApi.async_get_data", new_callable=AsyncMock)
# async def test_coordinator_fetch(mock_get_data, hass, mock_config_entry):
#     mock_get_data.return_value = {"orders": []}

#     await hass.config_entries.async_setup(mock_config_entry.entry_id)
#     await hass.async_block_till_done()

#     coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]

#     await coordinator.async_request_refresh()
#     assert coordinator.data == {"orders": []}
