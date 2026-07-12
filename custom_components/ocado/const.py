"""Constants for the Ocado integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

DOMAIN                          = "ocado"


class OcadoAuthError(Exception):
    """Raised when IMAP authentication fails (bad email/password)."""

OCADO_ADDRESS                   = "customerservices@ocado.com"
NEW_OCADO_ADDRESS               = "noreply@email.ocado.com"
MARKETING_OCADO_ADDRESS         = "marketing.ocado.com"
OCADO_CANCELLATION_SUBJECT      = "Order cancellation confirmation"
OCADO_CONFIRMATION_SUBJECT      = "Confirmation of your order"
OCADO_CUTOFF_SUBJECT            = "Don't miss the cut-off time for editing your order"
OCADO_NEW_TOTAL_SUBJECT         = "What you returned, and your new total"
OCADO_NEW_NEW_TOTAL_SUBJECT     = "Your receipt and updates for today’s delivery"
OCADO_SMARTPASS_SUBJECT         = "Payment successful: Smart Pass membership"
OCADO_RENEWAL_SUBJECT           = "Your Smart Pass will be renewed"
OCADO_UPDATE_SUBJECT            = "Confirmation of your order changes"
OCADO_VOUCHER_SUBJECT           = "Price Promise voucher"
OCADO_DELIVERY_UPDATE_SUBJECT   = "Your upcoming Ocado delivery"
OCADO_SUBJECT_DICT = {
    OCADO_CANCELLATION_SUBJECT:   "cancellation",
    OCADO_CONFIRMATION_SUBJECT:   "confirmation",
    OCADO_UPDATE_SUBJECT:         "update",
    OCADO_NEW_TOTAL_SUBJECT:      "new_total",
    OCADO_NEW_NEW_TOTAL_SUBJECT:  "new_total",
    OCADO_DELIVERY_UPDATE_SUBJECT: "delivery_update",
}
CONF_DELIVERY_TITLE = 'delivery_title'
CONF_EDIT_TITLE     = 'edit_title'
CONF_IMAP_DAYS      = 'imap_days'
CONF_IMAP_FOLDER    = 'imap_folder'
CONF_IMAP_PORT      = 'imap_port'
CONF_IMAP_SERVER    = 'imap_host'
CONF_IMAP_SSL       = 'imap_ssl'

DEFAULT_DELIVERY_TITLE = "Ocado delivery #{order_number}"
DEFAULT_EDIT_TITLE  = "Amend by — order #{order_number}"
DEFAULT_IMAP_DAYS   = 31
DEFAULT_IMAP_FOLDER = 'INBOX'
DEFAULT_IMAP_PORT   = 993
DEFAULT_IMAP_SERVER = 'imap.gmail.com'
DEFAULT_IMAP_SSL    = 'ssl'
DEFAULT_SCAN_INTERVAL = 600

ORDER_NUMBER_SHORT_LEN = 5
DELIVERY_TITLE_TOKENS = ("order_number", "order_number_short", "total", "date", "window")
EDIT_TITLE_TOKENS = ("order_number", "order_number_short", "deadline")

EMAIL_ATTR_FROM     = 'from'
EMAIL_ATTR_SUBJECT  = 'subject'
EMAIL_ATTR_BODY     = 'body'
EMAIL_ATTR_DATE     = 'date'

MIN_IMAP_DAYS       = 7
MIN_SCAN_INTERVAL   = 60

# Consecutive failed polls tolerated (cached data kept, sensors stay available)
# before the log escalates from debug to warning. ~1 hour at the default poll.
FAILURES_BEFORE_WARNING = 6
# Consecutive failed polls before a user-facing repair issue is raised. ~2 hours
# at the default poll. A quiet inbox is a success and never counts toward this.
FAILURES_BEFORE_REPAIR = 12

REGEX_EDIT_UNTIL    = r"(?:You\scan\sedit\sthis\sorder\suntil:?\s)"

REGEX_DATE          = r"3[01]|[12][0-9]|0?[1-9]"
REGEX_DAY_FULL      = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
REGEX_DAY_SHORT     = r"Mon|Tue|Wed|Thu|Fri|Sat|Sun"
REGEX_MONTH_FULL    = r"January|February|March|April|May|June|July|August|September|October|November|December"
REGEX_MONTH_SHORT   = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
REGEX_MONTH         = r"1[0-2]|0?[1-9]"
REGEX_YEAR          = r"(?:19|20)\d{2}"
REGEX_ISO_TIME      = r"([01][0-9]|2[0-3]):([0-5][0-9])"
REGEX_APM_TIME      = r"(1[0-2]|0?[1-9])(?::|.)([0-5][0-9])\s?([AaPp][Mm])?"
REGEX_ORDINALS      = r"st|nd|rd|th"

REGEX_VOUCHER_CODE  = r"\bvou[a-z]*\d{6,}\b"

REGEX_SUBSTITUTION  = r"•\s*(\d+)\s*x\s*(.+?)\s*\n\s*with\s*\n\s*•\s*(\d+)\s*x\s*(.+)"
REGEX_MISSING_ITEM  = r"•\s*(\d+)\s*x\s*(.+)"

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
class OcadoEmails:
    """Class for all retrieved emails."""
    orders              : list[str]             = field(default_factory=list)
    cancelled           : list[OcadoEmail]      = field(default_factory=list)
    confirmations       : list[OcadoEmail]      = field(default_factory=list)

    total               : OcadoEmail | None     = None
    voucher             : OcadoEmail | None      = None
    delivery_update     : OcadoEmail | None      = None


@dataclass
class OcadoDeliveryUpdate:
    """Missing and substituted items parsed from a delivery-day update email."""
    updated                     : datetime | date | None
    order_number                : str | None
    missing                     : list[dict[str, Any]]
    substitutions               : list[dict[str, str]]

@dataclass
class OcadoOrder:
    """Class for Ocado orders."""
    updated                     : datetime | date | None
    order_number                : str      | None
    delivery_datetime           : datetime | None
    delivery_window_end         : datetime | None
    edit_datetime               : datetime | None
    estimated_total             : str      | None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict of the order, with datetimes as ISO strings."""
        return {
            key: value.isoformat() if isinstance(value, (date, datetime)) else value
            for key, value in asdict(self).items()
        }

EMPTY_ORDER = OcadoOrder(
        updated             = datetime.now(),
        order_number        = None,
        delivery_datetime   = None,
        delivery_window_end = None,
        edit_datetime       = None,
        estimated_total     = None,
    )
