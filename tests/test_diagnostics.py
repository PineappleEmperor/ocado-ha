"""Tests for the Ocado diagnostics."""

from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from homeassistant.core import HomeAssistant


async def test_diagnostics_redacts_credentials(
    hass: HomeAssistant, hass_client, init_integration
) -> None:
    """IMAP email and password are redacted; non-secret config is kept."""
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    )

    entry_data = diagnostics["entry"]["data"]
    assert entry_data["email"] == "**REDACTED**"
    assert entry_data["password"] == "**REDACTED**"
    assert entry_data["imap_host"] == "imap.test.com"
    assert "coordinator_data" in diagnostics
