"""Calendar platform for the Ocado UK integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DELIVERY_TITLE,
    CONF_EDIT_TITLE,
    DEFAULT_DELIVERY_TITLE,
    DEFAULT_EDIT_TITLE,
    OCADO_DELIVERY_DEVICE_DESCRIPTION,
    OcadoOrder,
)
from .coordinator import OcadoConfigEntry, OcadoUpdateCoordinator
from .utils import delivery_title_fields, edit_title_fields, render_event_title

PARALLEL_UPDATES = 0

EDIT_MARKER_DURATION = timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OcadoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ocado calendars."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        [OcadoDeliveryCalendar(coordinator), OcadoEditCalendar(coordinator)]
    )


class OcadoCalendar(CoordinatorEntity[OcadoUpdateCoordinator], CalendarEntity):
    """Base calendar that projects the coordinator's live order list as events."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator)
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION

    def _orders(self) -> list[OcadoOrder]:
        """Return the current order list, or an empty list when there's no data."""
        data = self.coordinator.data
        orders = data.get("orders") if data else None
        return orders or []

    def _title_format(self, key: str, default: str) -> str:
        """Return the configured event-title template, or the default."""
        entry = self.coordinator.config_entry
        return entry.options.get(key, default) if entry else default

    def _build_events(self) -> list[CalendarEvent]:
        """Build the calendar events from the current orders. Overridden per calendar."""
        raise NotImplementedError

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming or currently-ongoing event."""
        now = dt_util.now()
        upcoming = sorted(
            (e for e in self._build_events() if e.end > now), key=lambda e: e.start
        )
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the events that overlap the requested range."""
        return [
            e
            for e in self._build_events()
            if e.end > start_date and e.start < end_date
        ]


class OcadoDeliveryCalendar(OcadoCalendar):
    """A calendar of Ocado delivery windows."""

    _attr_translation_key = "deliveries"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the delivery calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = "ocado_deliveries_calendar"
        # Device name already ends in "Deliveries"; pin the entity_id so it
        # doesn't auto-generate as calendar.ocado_uk_deliveries_deliveries.
        self.entity_id = "calendar.ocado_uk_deliveries"

    def _build_events(self) -> list[CalendarEvent]:
        """One event per order delivery window, skipping orders without one."""
        title_format = self._title_format(CONF_DELIVERY_TITLE, DEFAULT_DELIVERY_TITLE)
        events: list[CalendarEvent] = []
        for order in self._orders():
            start, end = order.delivery_datetime, order.delivery_window_end
            if start is None or end is None:
                continue
            start, end = dt_util.as_local(start), dt_util.as_local(end)
            if end <= start:
                continue
            number = order.order_number
            events.append(
                CalendarEvent(
                    start=start,
                    end=end,
                    summary=render_event_title(
                        title_format, delivery_title_fields(order), DEFAULT_DELIVERY_TITLE
                    ),
                    uid=f"ocado-delivery-{number}" if number else None,
                )
            )
        return events


class OcadoEditCalendar(OcadoCalendar):
    """A calendar of Ocado order amend-by deadlines."""

    _attr_translation_key = "edit_deadlines"
    _attr_icon = "mdi:calendar-edit"

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the edit-deadline calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = "ocado_edit_deadlines_calendar"

    def _build_events(self) -> list[CalendarEvent]:
        """A short marker event at each order's edit deadline."""
        title_format = self._title_format(CONF_EDIT_TITLE, DEFAULT_EDIT_TITLE)
        events: list[CalendarEvent] = []
        for order in self._orders():
            deadline = order.edit_datetime
            if deadline is None:
                continue
            start = dt_util.as_local(deadline)
            number = order.order_number
            events.append(
                CalendarEvent(
                    start=start,
                    end=start + EDIT_MARKER_DURATION,
                    summary=render_event_title(
                        title_format, edit_title_fields(order), DEFAULT_EDIT_TITLE
                    ),
                    uid=f"ocado-edit-{number}" if number else None,
                )
            )
        return events
