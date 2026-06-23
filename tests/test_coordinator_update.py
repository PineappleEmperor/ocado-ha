"""Tests for the Ocado update coordinator."""

from unittest.mock import patch

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
