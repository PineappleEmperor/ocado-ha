"""Constants for the Ocado integration."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import json
import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN                          = "ocado"

OCADO_ADDRESS                   = "customerservices@ocado.com"
NEW_OCADO_ADDRESS               = "noreply@email.ocado.com"
MARKETING_OCADO_ADDRESS         = "marketing.ocado.com"
OCADO_CANCELLATION_SUBJECT      = "Order cancellation confirmation"
OCADO_CONFIRMATION_SUBJECT      = "Confirmation of your order"
OCADO_CUTOFF_SUBJECT            = "Don't miss the cut-off time for editing your order"
OCADO_NEW_TOTAL_SUBJECT         = "What you returned, and your new total"
OCADO_RECEIPT_SUBJECT           = "Your receipt for today's Ocado delivery"
OCADO_NEW_NEW_TOTAL_SUBJECT     = "Your receipt and updates for today’s delivery"
OCADO_SMARTPASS_SUBJECT         = "Payment successful: Smart Pass membership"
OCADO_RENEWAL_SUBJECT           = "Your Smart Pass will be renewed"
OCADO_UPDATE_SUBJECT            = "Confirmation of your order changes"
OCADO_VOUCHER_SUBJECT           = "Price Promise voucher"
OCADO_SUBJECT_DICT = {
    OCADO_CANCELLATION_SUBJECT:   "cancellation",
    OCADO_CONFIRMATION_SUBJECT:   "confirmation",
    OCADO_UPDATE_SUBJECT:         "update",
    OCADO_NEW_TOTAL_SUBJECT:      "new_total",
    OCADO_RECEIPT_SUBJECT:        "receipt",
    OCADO_NEW_NEW_TOTAL_SUBJECT:  "new_total",
}
OCADO_DELIVERY_DEVICE_DESCRIPTION = DeviceInfo(
    identifiers     = {(DOMAIN, "deliveries")},
    name            = "Ocado (UK) Deliveries",
    manufacturer    = "Ocado-ha",
    model           = "Delivery Sensor",
    sw_version      = "1.0",
)
OCADO_BBD_DEVICE_DESCRIPTION = DeviceInfo(
    identifiers     = {(DOMAIN, "bbd")},
    name            = "Ocado (UK) Best Befores",
    manufacturer    = "Ocado-ha",
    model           = "Best Before Sensor",
    sw_version      = "1.0",
)
OCADO_DELIVERY_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_next_delivery",
    name                        = "Ocado Next Delivery",
)
OCADO_EDIT_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_next_edit_deadline",
    name                        = "Ocado Next Edit Deadline",
)
OCADO_TOTAL_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_last_total",
    name                        = "Ocado Last Total",
    device_class                = SensorDeviceClass.MONETARY,
    native_unit_of_measurement  = "GBP",
    icon                        = "mdi:receipt-text",
)
OCADO_UPCOMING_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_upcoming_delivery",
    name                        = "Ocado Upcoming Delivery",
)
OCADO_ORDER_LIST_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_orders",
    name                        = "Ocado Orders",
)
OCADO_BBD_DESCRIPTION = SensorEntityDescription(
    key                         = "ocado_bbd",
    name                        = "Ocado Best Before",
)

CONF_IMAP_DAYS      = 'imap_days'
CONF_IMAP_FOLDER    = 'imap_folder'
CONF_IMAP_PORT      = 'imap_port'
CONF_IMAP_SERVER    = 'imap_host'
CONF_IMAP_SSL       = 'imap_ssl'

DEFAULT_IMAP_DAYS   = 31
DEFAULT_IMAP_FOLDER = 'INBOX'
DEFAULT_IMAP_PORT   = 993
DEFAULT_IMAP_SERVER = 'imap.gmail.com'
DEFAULT_IMAP_SSL    = 'ssl'
DEFAULT_SCAN_INTERVAL = 600

DEVICE_CLASS        = "ocado_deliveries"

EMAIL_ATTR_FROM     = 'from'
EMAIL_ATTR_SUBJECT  = 'subject'
EMAIL_ATTR_BODY     = 'body'
EMAIL_ATTR_DATE     = 'date'

MIN_IMAP_DAYS       = 7
MIN_SCAN_INTERVAL   = 60

REGEX_EDIT_UNTIL    = r"(?:You\scan\sedit\sthis\sorder\suntil:?\s)"

REGEX_DATE          = r"3[01]|[12][0-9]|0?[1-9]"
REGEX_DAY_FULL      = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
REGEX_DAY_SHORT     = r"Mon|Tue|Wed|Thu|Fri|Sat|Sun"
REGEX_MONTH_FULL    = r"January|February|March|April|May|June|July|August|September|October|November|December"
REGEX_MONTH_SHORT   = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
REGEX_MONTH         = r"1[0-2]|0?[1-9]"
REGEX_YEAR          = r"(?:19|20)\d{2}"
# If this eventually fails due to other formats being used, python-dateutil should be used
REGEX_DATE_FULL     = r"((?:" + REGEX_DATE + r")\/(?:" + REGEX_MONTH + r")\/(?:" + REGEX_YEAR + r"))"
REGEX_ISO_TIME      = r"([01][0-9]|2[0-3]):([0-5][0-9])"
REGEX_APM_TIME      = r"(1[0-2]|0?[1-9])(?::|.)([0-5][0-9])\s?([AaPp][Mm])?"
REGEX_ORDINALS      = r"st|nd|rd|th"

REGEX_VOUCHER_CODE  = r"\bvou[a-z]*\d{6,}\b"
REGEX_AMOUNT        = r"(?:\d+x)?\d+k?(?:g|l|ml)"
REGEX_COLUMNS       = r"\s?\d+\/\d+\s?\d+.\d{2}\*?"
REGEX_EACH          = r"\((?:£|\\u00a3)\d+\.\d{2}\/\s?each\)"

STRING_PLUS         = "Products with a 'use-by' date over one week"
STRING_NO_BBD       = "Products with no 'use-by' date" # only applicable to cupboard
REGEX_END_INDEX     = r"You've saved £\d+.\d{2} today"
STRING_FREEZER      = 'Freezer'
STRING_PREFIX       = 'Use by end of '
STRING_HEADER       = ["Delivered /", "Ordered", "Price", "to", "pay", "(£)"]

DAYS = [
    "mon",
    "tue",
    "wed",
    "thu",
    "fri",
    "sat",
    "sun",
    "longer"
]

LONG_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

WEEKDAY_MAP = {
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}

EMPTY_ATTRIBUTES = {
    "order_number"          : None,
    "delivery_date"         : None,
    "delivery_window"       : None,
    "edit_date"             : None,
    "edit_time"             : None,
    "estimated_total"       : None,
}

@dataclass
class OcadoEmail:
    """Class for retrieved emails."""
    message_id          : bytes | None
    email_type          : str   | None
    email_date          : date  | None
    from_address        : str   | None
    subject             : str   | None
    body                : str   | None
    order_number        : str   | None
    delivery_datetime   : datetime | None = None
    delivery_window_end : datetime | None = None

@dataclass
class OcadoVoucher:
    """Class for Ocado Vouchers."""
    issue_date                  : datetime  | date | None
    voucher_validity            : datetime  | date | None
    voucher                     : str       | None
    amount                      : str       | None

@dataclass
class OcadoReceipt:
    """Class for Ocado Receipts."""
    updated                     : datetime  | date | None
    order_number                : str       | None

    mon                         : list[str] = field(default_factory=list)
    tue                         : list[str] = field(default_factory=list)
    wed                         : list[str] = field(default_factory=list)
    thu                         : list[str] = field(default_factory=list)
    fri                         : list[str] = field(default_factory=list)
    sat                         : list[str] = field(default_factory=list)
    sun                         : list[str] = field(default_factory=list)

    date_dict                   : dict      = field(default_factory=dict)

    def update_from(self, other: "OcadoReceipt") -> None:
        """Update this receipt from another, only if order_number matches."""
        if self.order_number != other.order_number:
            raise ValueError(
                f"Order numbers do not match: {self.order_number} != {other.order_number}"
            )
        for attr in ["mon", "tue", "wed", "thu", "fri", "sat", "sun", "date_dict"]:
            value = getattr(other, attr)
            if value:
                setattr(self, attr, value)

    def toJSON(self):
        """Return a JSON representation of the receipt."""
        return json.dumps(self, default=str)

@dataclass
class OcadoEmails:
    """Class for all retrieved emails."""
    orders              : list[str]             = field(default_factory=list)
    cancelled           : list[OcadoEmail]      = field(default_factory=list)
    confirmations       : list[OcadoEmail]      = field(default_factory=list)

    total               : OcadoEmail | None     = None
    receipt             : OcadoReceipt | None   = None
    voucher             : OcadoEmail | None      = None

@dataclass
class OcadoOrder:
    """Class for Ocado orders."""
    updated                     : datetime | date | None
    order_number                : str      | None
    delivery_datetime           : datetime | None
    delivery_window_end         : datetime | None
    edit_datetime               : datetime | None
    estimated_total             : str      | None

    def toJSON(self):
        """Return a JSON representation of the order."""
        return json.dumps(self, default=str)

EMPTY_ORDER = OcadoOrder(
        updated             = datetime.now(),
        order_number        = None,
        delivery_datetime   = None,
        delivery_window_end = None,
        edit_datetime       = None,
        estimated_total     = None,
    )

def capitalise(text):
    """Capitalise the first letter of a string."""
    return text[0].upper() + text[1:]

@dataclass
class BBDs:
    """Class for a collection of BBD lists."""
    delivery_date       : date | None      = None
    date_dict           : dict[int, date]  = field(default_factory=dict)
    mon                 : list[str]        = field(default_factory=list)
    tue                 : list[str]        = field(default_factory=list)
    wed                 : list[str]        = field(default_factory=list)
    thu                 : list[str]        = field(default_factory=list)
    fri                 : list[str]        = field(default_factory=list)
    sat                 : list[str]        = field(default_factory=list)
    sun                 : list[str]        = field(default_factory=list)
    plus                : list[str]        = field(default_factory=list)

class BBDParser:
    """Class to parse a receipt into a BBDs object."""
    days_list               = DAYS[:-1]
    long_days_list          = LONG_DAYS
    header_string           = STRING_HEADER
    plus_string             = STRING_PLUS
    regex_date              = REGEX_DATE_FULL
    columns_regex           = REGEX_COLUMNS
    complete_columns_regex  = r"^" + columns_regex + r"$"
    amount_regex            = REGEX_AMOUNT
    each_regex              = REGEX_EACH

    def parse(self, receipt_list: list[str], index_start: int, index_end: int) -> BBDs:
        """Parse the receipt list between the given indices into BBD lists."""
        if index_start is None or index_end is None:
            raise ValueError("Index start and end must be provided")
        parsed_result = BBDs()

        delivery_date_raw = re.search(self.regex_date, receipt_list[11])
        if delivery_date_raw is not None:
            delivery_date_raw = delivery_date_raw.group()
        else:
            delivery_date_regex = r"Delivery date:\s(?:" + REGEX_DAY_FULL + r")\s" + REGEX_DATE_FULL
            match = re.search(delivery_date_regex, "\n".join(receipt_list))
            if match is not None:
                delivery_date_raw = match.group()
        if delivery_date_raw is None:
            raise ValueError("Could not extract delivery date")
        try:
            delivery_date = datetime.strptime(delivery_date_raw,"%d/%m/%Y").date()
        except ValueError as error:
            raise ValueError(f"No date retrieved from receipt_list. Last attempt was with {delivery_date_raw}") from error
        parsed_result.delivery_date = delivery_date

        # We also need to include the dates for the bbds, ideally this would be external, but oh well.
        date_dict: dict[int, date] = {}

        # Using the delivery date create the day<->date dict
        for i in range(1, 8):
            date_dict[(delivery_date + timedelta(days=i)).weekday()] = (delivery_date + timedelta(days=i))
        tomorrow = self.long_days_list[(delivery_date + timedelta(days=1)).weekday()]

        reduced_list = receipt_list[index_start + 1:index_end]

        # The first day has a prefix so we remove it
        first_day = reduced_list[0].split(' ')[-1]

        # convert tomorrow into an actual day
        if first_day == "tomorrow":
            first_day = tomorrow

        bbd_lists: list[list[str]] = [[] for _ in range(8)]
        active_index = self.long_days_list.index(first_day)
        # Loop over the relevant lines in the list
        for i in range(1, len(reduced_list)):
            line = reduced_list[i]
            # If the line is a day, we switch to the next bbd
            if line in self.long_days_list:
                active_index = self.long_days_list.index(line)
                continue
            # This is for the plus list, we use 7 since we use 0-6
            if line == self.plus_string:
                active_index = 7
                continue
            if line in self.header_string:
                continue
            if re.search(self.complete_columns_regex, line, flags = re.IGNORECASE):
                continue
            bbd_lists[active_index].append(line)

        # There's probably a better and more efficient way of doing this
        cleaned: list[list[str]] = []
        for day in bbd_lists:
            if not day:
                cleaned = [*cleaned, day]
                continue
            # need to recombine and remove the various column bits
            text = ' '.join(day)
            # start with the most complete strings to remove
            text = re.sub(self.columns_regex, '\n', text, flags = re.IGNORECASE)
            text = re.sub(self.amount_regex, '\n', text, flags = re.IGNORECASE)
            text = re.sub(self.each_regex, '\n', text, flags = re.IGNORECASE)
            day  = text.split('\n')
            # remove any whitespace/newlines
            day = list(map(str.strip, day))
            # Now remove any blank entries, some would have been a single space so order is important
            day = list(filter(None, day))
            day = [
                x.lower()
                .capitalize()
                .replace("ocado", "Ocado")
                .replace("m&s", "M&S")
                .replace("M&s", "M&S")
                for x in day
            ]
            day = list(map(capitalise, day))
            cleaned = [*cleaned, day]

        for i in range(7):
            setattr(self, self.days_list[i].lower(), cleaned[i])
        parsed_result.plus = cleaned[7]

        return parsed_result
