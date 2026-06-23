"""Tests for the Ocado config flow."""

from unittest.mock import patch

from custom_components.ocado.config_flow import CannotConnect, InvalidAuth
from custom_components.ocado.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

USER_INPUT = {
    "email": "test@example.com",
    "password": "password123",
    "imap_host": "imap.test.com",
    "imap_port": 993,
    "imap_folder": "INBOX",
}


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A valid user flow creates the config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.ocado.config_flow._validate_input",
        return_value={"title": "Ocado UK"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ocado UK"
    assert result["data"] == USER_INPUT


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """A connection failure shows the cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.ocado.config_flow._validate_input",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """An auth failure shows the invalid_auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.ocado.config_flow._validate_input",
        side_effect=InvalidAuth,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """A reauth flow updates the stored password."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.ocado.config_flow._validate_input",
        return_value={"title": "Ocado UK"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "newpassword"}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data["password"] == "newpassword"
    await hass.async_block_till_done()


async def test_reconfigure_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """A reconfigure flow updates the connection settings."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_input = {**USER_INPUT, "imap_host": "imap.changed.com"}
    with patch(
        "custom_components.ocado.config_flow._validate_input",
        return_value={"title": "Ocado UK"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], new_input
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["imap_host"] == "imap.changed.com"
    await hass.async_block_till_done()
