"""Sensor setup for Ocado UK Integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import OcadoOrder
from .coordinator import OcadoConfigEntry
from .entity import OcadoEntity
from .utils import (
    active_delivery,
    active_edit,
    delivery_attributes,
    edit_attributes,
    iconify,
    upcoming_delivery,
    voucher_attributes,
    voucher_if_valid,
)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OcadoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ocado sensors."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        [
            OcadoDelivery(coordinator),
            OcadoEdit(coordinator),
            OcadoTotal(coordinator),
            OcadoUpcoming(coordinator),
            OcadoOrderList(coordinator),
            OcadoVoucher(coordinator),
        ]
    )


def _money(value: str | None) -> float | None:
    """Coerce a parsed money string to a float for monetary statistics."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class OcadoDelivery(OcadoEntity, SensorEntity):
    """The next delivery whose window has not yet ended."""

    _attr_translation_key = "next_delivery"
    _attr_unique_id = "ocado_next_delivery"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def _order(self) -> OcadoOrder | None:
        """Return the order this sensor currently reflects, if any."""
        return active_delivery(self.coordinator.data, datetime.now())

    @property
    def native_value(self) -> datetime | None:
        """The local-time start of the delivery window."""
        order = self._order()
        if order and order.delivery_datetime:
            return dt_util.as_local(order.delivery_datetime)
        return None

    @property
    def icon(self) -> str:
        """A countdown icon to the delivery day."""
        order = self._order()
        if order and order.delivery_datetime:
            return iconify((order.delivery_datetime.date() - date.today()).days)
        return "mdi:help-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Order number, window, edit deadline and estimated total."""
        return delivery_attributes(self._order())


class OcadoEdit(OcadoEntity, SensorEntity):
    """The next order amend-by deadline that has not yet passed."""

    _attr_translation_key = "next_edit_deadline"
    _attr_unique_id = "ocado_next_edit_deadline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def _order(self) -> OcadoOrder | None:
        """Return the order whose edit deadline this sensor reflects, if any."""
        return active_edit(self.coordinator.data, datetime.now())

    @property
    def native_value(self) -> datetime | None:
        """The local-time edit deadline."""
        order = self._order()
        if order and order.edit_datetime:
            return dt_util.as_local(order.edit_datetime)
        return None

    @property
    def icon(self) -> str:
        """A countdown icon to the edit deadline."""
        order = self._order()
        if order and order.edit_datetime:
            return iconify((order.edit_datetime.date() - date.today()).days)
        return "mdi:help-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Order number for the order being edited."""
        return edit_attributes(self._order())


class OcadoUpcoming(OcadoEntity, SensorEntity):
    """The delivery after next, while its window is still in the future."""

    _attr_translation_key = "upcoming_delivery"
    _attr_unique_id = "ocado_upcoming_delivery"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def _order(self) -> OcadoOrder | None:
        """Return the upcoming order, if any."""
        return upcoming_delivery(self.coordinator.data, datetime.now())

    @property
    def native_value(self) -> datetime | None:
        """The local-time start of the upcoming delivery window."""
        order = self._order()
        if order and order.delivery_datetime:
            return dt_util.as_local(order.delivery_datetime)
        return None

    @property
    def icon(self) -> str:
        """A countdown icon to the upcoming delivery day."""
        order = self._order()
        if order and order.delivery_datetime:
            return iconify((order.delivery_datetime.date() - date.today()).days)
        return "mdi:help-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Order number, window, edit deadline and estimated total."""
        return delivery_attributes(self._order())


class OcadoTotal(OcadoEntity, SensorEntity):
    """The estimated total of the most recent delivery."""

    _attr_translation_key = "last_total"
    _attr_unique_id = "ocado_last_total"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "GBP"

    def _total(self) -> OcadoOrder | None:
        """Return the cached total order, if any."""
        data = self.coordinator.data
        return data.get("total") if data else None

    @property
    def native_value(self) -> float | None:
        """The estimated total in GBP."""
        total = self._total()
        return _money(total.estimated_total) if total else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Order number and when it was last updated."""
        total = self._total()
        if total is None:
            return {"updated": dt_util.now(), "order_number": None}
        return {"updated": total.updated, "order_number": total.order_number}


class OcadoVoucher(OcadoEntity, SensorEntity):
    """The latest Price Promise voucher, while it is still in date."""

    _attr_translation_key = "latest_voucher"
    _attr_unique_id = "ocado_latest_voucher"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "GBP"

    @property
    def native_value(self) -> float:
        """The voucher amount in GBP, or zero when there's no valid voucher."""
        voucher = voucher_if_valid(self.coordinator.data, datetime.now())
        return _money(voucher.amount) or 0 if voucher else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Voucher code, amount and validity."""
        return voucher_attributes(voucher_if_valid(self.coordinator.data, datetime.now()))


class OcadoOrderList(OcadoEntity, SensorEntity):
    """The count of all known Ocado orders, with the orders in an attribute."""

    _attr_translation_key = "orders"
    _attr_unique_id = "ocado_orders"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def _orders(self) -> list[OcadoOrder]:
        """Return the current order list, or an empty list."""
        data = self.coordinator.data
        return (data.get("orders") if data else None) or []

    @property
    def native_value(self) -> int:
        """The number of known orders."""
        return len(self._orders())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Every known order, serialised."""
        return {"orders": [order.as_dict() for order in self._orders()]}
