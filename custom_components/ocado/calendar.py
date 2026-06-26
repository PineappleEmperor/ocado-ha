"""Calendar platform for the Ocado UK integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import OCADO_DELIVERY_DEVICE_DESCRIPTION, OcadoOrder
from .coordinator import OcadoConfigEntry, OcadoUpdateCoordinator

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
                    summary=f"Ocado delivery #{number}" if number else "Ocado delivery",
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
                    summary=(
                        f"Amend by — order #{number}" if number else "Ocado amend deadline"
                    ),
                    uid=f"ocado-edit-{number}" if number else None,
                )
            )
        return events
