"""Tests for the delivery-day missing/substituted item parsing and sensors.

The parser runs on the plaintext body Home Assistant extracts from the
"Your upcoming Ocado delivery" email; these cases mirror the real layouts
(entirely missing, single and multiple substitutions, and the all-present
"no substitutions" email).
"""

from datetime import date

from custom_components.ocado.const import OcadoDeliveryUpdate, OcadoEmail
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from custom_components.ocado.sensor import OcadoMissing, OcadoSubstitutions
from custom_components.ocado.utils import (
    delivery_update_parse,
    parse_missing_items,
    parse_substitutions,
)
from homeassistant.core import HomeAssistant

MISSING_BODY = """Missing items
We're sorry, but you're missing:
• 1 x M&S Lamb's Lettuce 80g
Sorry, unfortunately there wasn't a suitable alternative for the above."""

CLEAN_BODY = """Hello Dan,
Your order doesn't have any substitutions, everything's present and correct.
See you later,"""

SINGLE_SUB_BODY = """Substituted items
Sorry, but the following had to be substituted:
• 1 x Warburtons Wholemeal Sliced Medium 400g
with
• 1 x Hovis Tasty Wholemeal Medium Loaf 400g

See you later,"""

MULTI_SUB_BODY = """Substituted items
Sorry, but the following had to be substituted:
• 1 x Eat Natural Dark Chocolate Cranberries & Macadamias Bars 3 x 40g
with
• 1 x Eat Natural Apple Ginger & Dark Chocolate Bars 3 x 40g

• 1 x Ocado Mixed Peppers 4 per pack
with
• 1 x Ocado Mixed Peppers 3 per pack

See you later,"""


def test_parse_missing_items() -> None:
    """A missing item is captured with its quantity and name."""
    assert parse_missing_items(MISSING_BODY) == [
        {"qty": 1, "item": "M&S Lamb's Lettuce 80g"}
    ]


def test_missing_body_has_no_substitutions() -> None:
    """A missing-only email yields no substitution pairs."""
    assert parse_substitutions(MISSING_BODY) == []


def test_clean_body_is_empty() -> None:
    """The all-present email yields no missing items and no substitutions."""
    assert parse_missing_items(CLEAN_BODY) == []
    assert parse_substitutions(CLEAN_BODY) == []


def test_parse_single_substitution() -> None:
    """A substitution pair maps ordered to sent."""
    assert parse_substitutions(SINGLE_SUB_BODY) == [
        {
            "ordered": "Warburtons Wholemeal Sliced Medium 400g",
            "sent": "Hovis Tasty Wholemeal Medium Loaf 400g",
        }
    ]


def test_substitution_body_has_no_missing_items() -> None:
    """A substitution's two bullets are not mistaken for missing items."""
    assert parse_missing_items(SINGLE_SUB_BODY) == []


def test_parse_multiple_substitutions_with_x_in_name() -> None:
    """Multiple pairs parse, and item names containing 'x' survive."""
    assert parse_substitutions(MULTI_SUB_BODY) == [
        {
            "ordered": "Eat Natural Dark Chocolate Cranberries & Macadamias Bars 3 x 40g",
            "sent": "Eat Natural Apple Ginger & Dark Chocolate Bars 3 x 40g",
        },
        {
            "ordered": "Ocado Mixed Peppers 4 per pack",
            "sent": "Ocado Mixed Peppers 3 per pack",
        },
    ]


def test_delivery_update_parse_carries_order_and_date() -> None:
    """delivery_update_parse copies the order number and email date across."""
    email = OcadoEmail(
        message_id          = b"1",
        email_type          = "delivery_update",
        email_date          = date(2026, 7, 12),
        from_address        = "noreply@email.ocado.com",
        subject             = "Your upcoming Ocado delivery",
        body                = MISSING_BODY,
        order_number        = "1927827262897",
    )
    update = delivery_update_parse(email)
    assert update.order_number == "1927827262897"
    assert update.updated == date(2026, 7, 12)
    assert update.missing == [{"qty": 1, "item": "M&S Lamb's Lettuce 80g"}]
    assert update.substitutions == []


async def test_missing_and_substitution_sensors(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Both sensors report their count as state and the details as attributes."""
    update = OcadoDeliveryUpdate(
        updated             = date(2026, 7, 12),
        order_number        = "1927827262897",
        missing             = [{"qty": 1, "item": "M&S Lamb's Lettuce 80g"}],
        substitutions       = [{"ordered": "Warburtons", "sent": "Hovis"}],
    )
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    coordinator.data = {"delivery_update": update}

    missing = OcadoMissing(coordinator)
    assert missing.native_value == 1
    assert missing.extra_state_attributes["missing"] == update.missing
    assert missing.extra_state_attributes["order_number"] == "1927827262897"

    subs = OcadoSubstitutions(coordinator)
    assert subs.native_value == 1
    assert subs.extra_state_attributes["substitutions"] == update.substitutions


async def test_sensors_default_to_zero_without_update(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """With no delivery-update email the sensors read zero with empty lists."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    coordinator.data = {"delivery_update": None}

    missing = OcadoMissing(coordinator)
    assert missing.native_value == 0
    assert missing.extra_state_attributes["missing"] == []

    subs = OcadoSubstitutions(coordinator)
    assert subs.native_value == 0
    assert subs.extra_state_attributes["substitutions"] == []
