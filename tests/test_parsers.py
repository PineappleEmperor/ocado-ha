"""Unit tests for the pure parsing helpers in utils.py.

These take a string or object and return a value with no Home Assistant and no
mocks, so they are the cheapest and highest-value regression cover for the
email-scraping logic.
"""

from datetime import datetime

import pytest

from custom_components.ocado.const import OcadoEmail
from custom_components.ocado.utils import (
    _ocado_email_typer,
    _unfold_ics,
    capitalise,
    get_email_from_address,
    get_email_from_datetime,
    get_estimated_total,
    get_order_number,
    get_window,
    iconify,
    parse_ics,
    total_parse,
    voucher_parse,
)


def _email(*, subject: str | None = None, body: str | None = None) -> OcadoEmail:
    """Build a minimal OcadoEmail for body/subject parsers."""
    return OcadoEmail(
        message_id=b"1",
        email_type="voucher",
        email_date=datetime(2025, 5, 1),
        from_address="marketing@marketing.ocado.com",
        subject=subject,
        body=body,
        order_number=None,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ocado <orders@ocado.com>", "orders@ocado.com"),
        ("ORDERS@ocado.com", "orders@ocado.com"),
    ],
)
def test_get_email_from_address(raw: str, expected: str) -> None:
    """A From header yields the lower-cased bare address."""
    assert get_email_from_address(raw) == expected


def test_get_email_from_address_malformed_raises() -> None:
    """A header with multiple angle brackets is rejected."""
    with pytest.raises(ValueError):
        get_email_from_address("a <b <c")


def test_get_email_from_datetime() -> None:
    """An RFC date header parses day-first to the right calendar date."""
    parsed = get_email_from_datetime("Tue, 27 May 2025 15:00:00 +0000")
    assert (parsed.year, parsed.month, parsed.day) == (2025, 5, 27)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Order reference: 1234567890123", "1234567890123"),
        ("Your order is 1234567890", "1234567890"),
        ("Order ref. 9876543210", "9876543210"),
    ],
)
def test_get_order_number_found(message: str, expected: str) -> None:
    """A 10-14 digit order reference is extracted."""
    assert get_order_number(message) == expected


def test_get_order_number_absent_returns_none() -> None:
    """No order reference returns None rather than raising."""
    assert get_order_number("nothing to see here") is None


@pytest.mark.parametrize(
    "message",
    [
        "Total (estimated): £45.67",
        "Total (estimated):    45.67 GBP",
    ],
)
def test_get_estimated_total(message: str) -> None:
    """Both the £ and GBP layouts yield the amount."""
    assert get_estimated_total(message) == "45.67"


def test_get_estimated_total_missing_raises() -> None:
    """A message without a total raises."""
    with pytest.raises(ValueError):
        get_estimated_total("no total in here")


@pytest.mark.parametrize(
    "body",
    [
        "New order total = £52.30",
        "New order total:    52.30 GBP",
    ],
)
def test_total_parse(body: str) -> None:
    """A new-total email yields the order total."""
    order = total_parse(_email(body=body))
    assert order.estimated_total == "52.30"


def test_voucher_parse_slash_date() -> None:
    """A voucher email yields amount, code and a slash-format validity date."""
    voucher = voucher_parse(
        _email(
            subject="Your £5.00 Price Promise voucher",
            body="Here is your £5.00 voucher, code vouopp123456, "
            "valid until 31/12/2025.",
        )
    )
    assert voucher.amount == "5.00"
    assert voucher.voucher == "vouopp123456"
    assert voucher.voucher_validity == datetime(2025, 12, 31)


def test_voucher_parse_month_name_date() -> None:
    """A voucher with a written-out validity date parses too."""
    voucher = voucher_parse(
        _email(
            subject="",
            body="£3.50 voucher vouopp987654 valid until 5 January 2026.",
        )
    )
    assert voucher.amount == "3.50"
    assert voucher.voucher_validity == datetime(2026, 1, 5)


def test_capitalise() -> None:
    """The first character is upper-cased and the rest preserved."""
    assert capitalise("hello WORLD") == "Hello WORLD"


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("Confirmation of your order", "confirmation"),
        ("Order cancellation confirmation", "cancellation"),
        ("Your £5.00 Price Promise voucher", "voucher"),
        ("Some unrelated newsletter", "Unknown"),
        (None, "Unknown"),
    ],
)
def test_ocado_email_typer(subject: str | None, expected: str) -> None:
    """Subjects classify to the expected email type."""
    assert _ocado_email_typer(subject) == expected


@pytest.mark.parametrize(
    ("days", "icon"),
    [
        (-1, "mdi:close-circle"),
        (0, "mdi:truck-fast"),
        (5, "mdi:numeric-5-circle"),
        (12, "mdi:numeric-9-plus-circle"),
    ],
)
def test_iconify(days: int, icon: str) -> None:
    """Days-until maps to the right countdown icon."""
    assert iconify(days) == icon


def test_get_window() -> None:
    """A start/end pair renders as an HH:MM window string."""
    start = datetime(2025, 6, 22, 10, 0)
    end = datetime(2025, 6, 22, 11, 30)
    assert get_window(start, end) == "10:00 - 11:30"


def test_unfold_ics() -> None:
    """RFC 5545 folded continuation lines are rejoined."""
    assert _unfold_ics("SUMMARY:Order\n 1234567890") == ["SUMMARY:Order1234567890"]


def test_parse_ics() -> None:
    """An Ocado calendar attachment yields order number and delivery window."""
    ics = (
        "BEGIN:VEVENT\n"
        "DTSTART:20250622T100000\n"
        "DTEND:20250622T110000\n"
        "SUMMARY:Ocado delivery for order 1234567890\n"
        "END:VEVENT\n"
    )
    order_number, start, end = parse_ics(ics)
    assert order_number == "1234567890"
    assert start is not None and end is not None
    assert (start.year, start.month, start.day, start.hour) == (2025, 6, 22, 10)
    assert (end.hour, end.minute) == (11, 0)
