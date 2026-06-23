"""Tests for the Ocado update coordinator."""

import imaplib
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ocado.const import OcadoAuthError, OcadoEmails
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed


async def test_auth_error_raises_config_entry_auth_failed(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """An IMAP auth error is surfaced as ConfigEntryAuthFailed to trigger reauth."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    with (
        patch(
            "custom_components.ocado.coordinator.email_triage",
            side_effect=OcadoAuthError("bad login"),
        ),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator.async_update_data()


async def test_update_success_builds_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A successful triage returns the expected data keys."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    with patch(
        "custom_components.ocado.coordinator.email_triage",
        return_value=([b"1"], OcadoEmails()),
    ):
        data = await coordinator.async_update_data()

    assert set(data) == {
        "updated",
        "message_ids",
        "next",
        "upcoming",
        "total",
        "voucher",
        "orders",
    }
    assert data["voucher"] is None
    assert data["total"] is None


async def test_update_uses_credentials_from_entry(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Regression guard: the coordinator reads IMAP creds from entry.data."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    fake_imap = MagicMock()
    fake_imap.error = imaplib.IMAP4.error
    server = fake_imap.return_value
    server.select.return_value = ("OK", [b"1"])
    server.search.return_value = ("OK", [b""])

    with patch("custom_components.ocado.utils.imap", fake_imap):
        data = await coordinator.async_update_data()

    _, kwargs = fake_imap.call_args
    assert kwargs["host"] == mock_config_entry.data["imap_host"]
    assert kwargs["port"] == mock_config_entry.data["imap_port"]
    server.login.assert_called_once_with(
        mock_config_entry.data["email"], mock_config_entry.data["password"]
    )
    assert "voucher" in data


async def test_transient_error_keeps_cached_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A non-auth fetch failure after a success keeps the last-known data."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    cached = {"voucher": None, "orders": None}
    coordinator.data = cached
    with patch(
        "custom_components.ocado.coordinator.email_triage",
        side_effect=TimeoutError("read operation timed out"),
    ):
        data = await coordinator.async_update_data()

    assert data is cached
