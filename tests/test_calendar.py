"""Tests for the Ocado calendar platform."""

from datetime import datetime, timedelta

from custom_components.ocado.calendar import OcadoDeliveryCalendar, OcadoEditCalendar
from custom_components.ocado.const import OcadoOrder
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


def _order(
    *,
    number: str | None = "1234567890",
    delivery: datetime | None,
    end: datetime | None,
    edit: datetime | None,
) -> OcadoOrder:
    """Build an OcadoOrder for the calendar to render."""
    return OcadoOrder(
        updated=dt_util.now(),
        order_number=number,
        delivery_datetime=delivery,
        delivery_window_end=end,
        edit_datetime=edit,
        estimated_total="63.50",
    )


def _with_orders(
    hass: HomeAssistant, mock_config_entry, orders: list[OcadoOrder]
) -> OcadoUpdateCoordinator:
    """Return a coordinator preloaded with the given orders."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    coordinator.data = {"orders": orders}
    return coordinator


async def test_delivery_calendar_lists_and_next(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The delivery calendar exposes window events and the next upcoming one."""
    now = dt_util.now()
    soon = (now + timedelta(days=2)).replace(tzinfo=None)
    later = (now + timedelta(days=9)).replace(tzinfo=None)
    orders = [
        _order(delivery=soon, end=soon + timedelta(hours=1), edit=None),
        _order(number="999", delivery=later, end=later + timedelta(hours=1), edit=None),
    ]
    cal = OcadoDeliveryCalendar(_with_orders(hass, mock_config_entry, orders))

    events = await cal.async_get_events(
        hass, now - timedelta(days=1), now + timedelta(days=30)
    )
    assert len(events) == 2

    in_range = await cal.async_get_events(
        hass, now - timedelta(days=1), now + timedelta(days=5)
    )
    assert len(in_range) == 1

    assert cal.event is not None
    assert cal.event.summary == "Ocado delivery #1234567890"
    assert cal.event.start.date() == (now + timedelta(days=2)).date()


async def test_edit_calendar_marks_deadline(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The edit calendar marks each order's amend deadline."""
    now = dt_util.now()
    edit = (now + timedelta(days=1)).replace(tzinfo=None)
    orders = [_order(delivery=None, end=None, edit=edit)]
    cal = OcadoEditCalendar(_with_orders(hass, mock_config_entry, orders))

    assert cal.event is not None
    assert cal.event.summary == "Amend by — order #1234567890"
    assert cal.event.end - cal.event.start == timedelta(minutes=15)


async def test_calendar_skips_incomplete_orders(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Orders without the required datetimes produce no events."""
    now = dt_util.now()
    bad = (now + timedelta(days=3)).replace(tzinfo=None)
    orders = [
        _order(delivery=None, end=None, edit=None),
        _order(delivery=bad, end=bad - timedelta(hours=1), edit=None),
    ]
    delivery_cal = OcadoDeliveryCalendar(_with_orders(hass, mock_config_entry, orders))
    edit_cal = OcadoEditCalendar(_with_orders(hass, mock_config_entry, orders))

    assert await delivery_cal.async_get_events(
        hass, now - timedelta(days=1), now + timedelta(days=30)
    ) == []
    assert edit_cal.event is None


async def test_calendar_empty_when_no_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A calendar with no coordinator data has no events."""
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    cal = OcadoDeliveryCalendar(coordinator)
    assert cal.event is None
    assert await cal.async_get_events(
        hass, dt_util.now(), dt_util.now() + timedelta(days=7)
    ) == []
