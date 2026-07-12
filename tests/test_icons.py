"""Tests for the icon-translations and strict-typing quality-scale rules.

The static-icon entities must resolve their icon from ``icons.json`` (no
hardcoded ``_attr_icon``); the countdown sensors keep a dynamic ``icon``
property. The package must ship a ``py.typed`` marker for strict typing.

``_attr_*`` are descriptors on HA's ``Entity`` base, so the literal a subclass
sets is read from ``cls.__dict__``, not by attribute access on the class.
"""

from datetime import date, datetime, time, timedelta
import json
from pathlib import Path

from custom_components.ocado import calendar as ocado_calendar, sensor as ocado_sensor
from custom_components.ocado.const import OcadoOrder
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from homeassistant.helpers.icon import async_get_icons

PACKAGE = Path(ocado_sensor.__file__).parent
ICONS   = json.loads((PACKAGE / "icons.json").read_text())

# (entity class, platform, translation_key) for entities whose icon lives in icons.json.
STATIC_ICON_ENTITIES = [
    (ocado_sensor.OcadoTotal, "sensor", "last_total"),
    (ocado_sensor.OcadoVoucher, "sensor", "latest_voucher"),
    (ocado_sensor.OcadoOrderList, "sensor", "orders"),
    (ocado_sensor.OcadoMissing, "sensor", "missing_items"),
    (ocado_sensor.OcadoSubstitutions, "sensor", "substituted_items"),
    (ocado_calendar.OcadoDeliveryCalendar, "calendar", "deliveries"),
    (ocado_calendar.OcadoEditCalendar, "calendar", "edit_deadlines"),
]

# Entities whose icon is a runtime countdown — they must NOT be in icons.json.
DYNAMIC_ICON_ENTITIES = [
    (ocado_sensor.OcadoDelivery, "next_delivery"),
    (ocado_sensor.OcadoEdit, "next_edit_deadline"),
    (ocado_sensor.OcadoUpcoming, "upcoming_delivery"),
]


def test_icons_json_is_valid_mdi() -> None:
    """Every declared icon is a non-empty mdi string."""
    for platform in ICONS["entity"].values():
        for entry in platform.values():
            assert entry["default"].startswith("mdi:")


def test_static_entities_resolve_icon_from_icons_json() -> None:
    """Static-icon entities declare an icon in icons.json and no _attr_icon."""
    for cls, platform, key in STATIC_ICON_ENTITIES:
        assert "_attr_icon" not in cls.__dict__
        assert ICONS["entity"][platform][key]["default"].startswith("mdi:")


def test_dynamic_entities_are_not_in_icons_json() -> None:
    """Countdown sensors drive their icon from a property, not icons.json."""
    sensor_icons = ICONS["entity"]["sensor"]
    for cls, key in DYNAMIC_ICON_ENTITIES:
        assert key not in sensor_icons
        # The dynamic icon is a property defined on the class itself.
        assert isinstance(cls.__dict__["icon"], property)


def test_py_typed_marker_present() -> None:
    """The package ships a py.typed marker so its annotations are honoured."""
    assert (PACKAGE / "py.typed").is_file()


async def test_icons_json_loaded_by_home_assistant(hass, init_integration) -> None:
    """HA loads icons.json so the static entities have a resolvable default."""
    icons = await async_get_icons(hass, "entity", integrations=["ocado"])
    sensor_icons = icons["ocado"]["sensor"]
    assert sensor_icons["last_total"]["default"] == "mdi:receipt-text"
    assert sensor_icons["latest_voucher"]["default"] == "mdi:ticket-percent"
    # Dynamic countdown sensors are deliberately absent.
    assert "next_delivery" not in sensor_icons


async def test_dynamic_icon_is_countdown(hass, mock_config_entry) -> None:
    """The delivery sensor's icon reflects days remaining via iconify."""
    delivery = date.today() + timedelta(days=5)
    order = OcadoOrder(
        updated             = None,
        order_number        = "1",
        delivery_datetime   = datetime.combine(delivery, time(10, 0)),
        delivery_window_end = datetime.combine(delivery, time(11, 0)),
        edit_datetime       = None,
        estimated_total     = None,
    )
    coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
    coordinator.data = {"next": order, "upcoming": None, "orders": [order]}
    entity = ocado_sensor.OcadoDelivery(coordinator)
    assert entity.icon == "mdi:numeric-5-circle"
