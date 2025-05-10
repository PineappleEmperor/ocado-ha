"""Constants for the Ocado integration."""
from datetime import date, datetime

DOMAIN = "ocado"

OCADO_ADDRESS = "customerservices@ocado.com"
OCADO_CANCELLATION_SUBJECT = "Order cancellation confirmation"
OCADO_CONFIRMATION_SUBJECT = "Confirmation of your order"
OCADO_CUTOFF_SUBJECT = "Don't miss the cut-off time for editing your order"
OCADO_NEW_TOTAL_SUBJECT = "What you returned, and your new total"
OCADO_RECEIPT_SUBJECT = "Your receipt for today's Ocado delivery"
OCADO_SUBJECT_DICT = {
    OCADO_CANCELLATION_SUBJECT: "cancellation",
    OCADO_CONFIRMATION_SUBJECT: "confirmation",
    OCADO_NEW_TOTAL_SUBJECT: "new_total",
    OCADO_RECEIPT_SUBJECT: "receipt"
}

CONF_IMAP_DAYS = 'imap_days'
CONF_IMAP_FOLDER = 'imap_folder'
CONF_IMAP_PORT = 'imap_port'
CONF_IMAP_SERVER = 'imap_host'
CONF_IMAP_SSL = 'imap_ssl'
CONF_SCAN_INTERVAL = 'scan_interval'

DEFAULT_IMAP_DAYS = 31
DEFAULT_IMAP_FOLDER = 'INBOX'
DEFAULT_IMAP_PORT = 993
DEFAULT_IMAP_SERVER = 'imap.gmail.com'
DEFAULT_IMAP_SSL = 'ssl'
DEFAULT_SCAN_INTERVAL = 600

DEVICE_CLASS = "ocado_deliveries"

EMAIL_ATTR_FROM = 'from'
EMAIL_ATTR_SUBJECT = 'subject'
EMAIL_ATTR_BODY = 'body'
EMAIL_ATTR_DATE = 'date'

REGEX_DATE = r"3[01]|[12][0-9]|0?[1-9]"
REGEX_DAY_FULL = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
REGEX_DAY_SHORT = r"Mon|Tue|Wed|Thu|Fri|Sat|Sun"
REGEX_MONTH_FULL = r"January|February|March|April|May|June|July|August|September|October|November|December"
REGEX_MONTH_SHORT = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
REGEX_YEAR = r"(?:19|20)\d{2}"
REGEX_TIME = r"(0?[1-9]|1[0-2]):[0-5][0-9] ?([AaPp][Mm])?"
REGEX_ORDINALS = r"st|nd|rd|th"

REGEX_WEIGHT = r"(?:\d+)?k?g?\s?"
REGEX_EACH = REGEX_WEIGHT + r"\([\\u00a3|£]\d{1,2}.\d{2}\/EACH\)"
REGEX_WEIGHT_QUANTITY_COST = REGEX_WEIGHT + r"\d\/\d\s?\d{1,2}.\d{1,2}"
REGEX_WEIGHT_QUANTITY_EACH = REGEX_EACH + r"\s?\d\/\d{1,2}.?\d{1,2}?\s?\d{1,2}.\d{2}"

EMPTY_ATTRIBUTES = {
    "order_number": None,
    "delivery_date": None,
    "delivery_window": None,
    "edit_date": None,
    "edit_time": None,
    "estimated_total": None,
}

class OcadoEmail:
    """Class for retrieved emails."""
    def __init__(self,
        message_id = None,
        email_type = None,
        date = None,
        from_address = None,
        subject = None,
        body = None,
        order_number = None,
    ):
        self.message_id = message_id
        self.type = email_type
        self.date = date
        self.from_address = from_address
        self.subject = subject
        self.body = body
        self.order_number = order_number

class OcadoEmails:
    """Class for all retrieved emails."""
    def __init__(self,
        orders = None,
        cancelled = None,
        confirmations = None,
        new_totals = None,
        receipts = None,
    ):
        self.orders = orders
        self.cancelled = cancelled
        self.confirmations = confirmations
        self.new_totals = new_totals
        self.receipts = receipts

class OcadoOrder:
    """Class for Ocado orders."""
    def __init__(self,
        updated: datetime,
        order_number: str,
        delivery_datetime: datetime,
        delivery_window= str,
        edit_datetime= datetime,
        estimated_total= float,
    ):
        self.updated = updated
        self.order_number = order_number
        self.delivery_datetime = delivery_datetime
        self.delivery_window = delivery_window
        self.edit_datetime = edit_datetime
        self.estimated_total = estimated_total
    def __str__(self):
        return f'"updated:{self.updated}, "order_number":{self.order_number}, "delivery_datetime":{self.delivery_datetime}, "delivery_end_datetime":{self.delivery_end_datetime}, "edit_datetime":{self.edit_datetime}, "estimated_total":{self.estimated_total}'
