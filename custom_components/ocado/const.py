"""Constants for the Ocado integration."""
from datetime import date, datetime, timedelta
import json
import re

DOMAIN = "ocado"

OCADO_ADDRESS =                 "customerservices@ocado.com"
OCADO_CANCELLATION_SUBJECT =    "Order cancellation confirmation"
OCADO_CONFIRMATION_SUBJECT =    "Confirmation of your order"
OCADO_CUTOFF_SUBJECT =          "Don't miss the cut-off time for editing your order"
OCADO_NEW_TOTAL_SUBJECT =       "What you returned, and your new total"
OCADO_RECEIPT_SUBJECT =         "Your receipt for today's Ocado delivery"
OCADO_NEW_NEW_TOTAL_SUBJECT =   "Your receipt and updates for today’s delivery"
OCADO_SMARTPASS_SUBJECT =       "Payment successful: Smart Pass membership"
OCADO_SUBJECT_DICT = {
    OCADO_CANCELLATION_SUBJECT: "cancellation",
    OCADO_CONFIRMATION_SUBJECT: "confirmation",
    OCADO_NEW_TOTAL_SUBJECT:    "new_total",
    OCADO_RECEIPT_SUBJECT:      "receipt",
    OCADO_NEW_NEW_TOTAL_SUBJECT:"new_total"
}

CONF_IMAP_DAYS =     'imap_days'
CONF_IMAP_FOLDER =   'imap_folder'
CONF_IMAP_PORT =     'imap_port'
CONF_IMAP_SERVER =   'imap_host'
CONF_IMAP_SSL =      'imap_ssl'

DEFAULT_IMAP_DAYS =     31
DEFAULT_IMAP_FOLDER =   'INBOX'
DEFAULT_IMAP_PORT =     993
DEFAULT_IMAP_SERVER =   'imap.gmail.com'
DEFAULT_IMAP_SSL =      'ssl'
DEFAULT_SCAN_INTERVAL = 600

DEVICE_CLASS = "ocado_deliveries"

EMAIL_ATTR_FROM = 'from'
EMAIL_ATTR_SUBJECT = 'subject'
EMAIL_ATTR_BODY = 'body'
EMAIL_ATTR_DATE = 'date'

MIN_IMAP_DAYS = 7
MIN_SCAN_INTERVAL = 60

REGEX_DATE = r"3[01]|[12][0-9]|0?[1-9]"
REGEX_DAY_FULL = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
REGEX_DAY_SHORT = r"Mon|Tue|Wed|Thu|Fri|Sat|Sun"
REGEX_MONTH_FULL = r"January|February|March|April|May|June|July|August|September|October|November|December"
REGEX_MONTH_SHORT = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
REGEX_MONTH = r"1[0-2]|0?[1-9]"
REGEX_YEAR = r"(?:19|20)\d{2}"
# If this eventually fails due to other formats being used, python-dateutil should be used
REGEX_DATE_FULL = r"((?:" + REGEX_DATE + r")\/(?:" + REGEX_MONTH + r")\/(?:" + REGEX_YEAR + r"))"
REGEX_TIME = r"([01][0-9]|2[0-3]):([0-5][0-9])([AaPp][Mm])?"
REGEX_NOT_ISO_TIME = r"([0-9]|2[0-3]):([0-5][0-9])([AaPp][Mm])?"
REGEX_ORDINALS = r"st|nd|rd|th"

REGEX_AMOUNT = r"(?:\d+x)?\d+k?(?:g|l|ml)"
REGEX_COLUMNS = r"\s?\d+\/\d+\s?\£\d+.\d{2}\*?"
REGEX_EACH = r"\((?:£|\\u00a3)\d+\.\d{2}\/\s?each\)"

STRING_PLUS = "Products with a 'use-by' date over one week"
STRING_NO_BBD = "Products with no 'use-by' date" # only applicable to cupboard
REGEX_END_INDEX = r"You've saved £\d+.\d{2} today"
STRING_FREEZER = 'Freezer'
STRING_PREFIX = 'Use by end of '
STRING_HEADER = ["Delivered /", "Ordered", "Price", "to", "pay", "(£)"]

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

class OcadoEmail:
    """Class for retrieved emails."""
    def __init__(self,
        message_id          : bytes | None,
        email_type          : str   | None,
        date                : date  | None,
        from_address        : str   | None,
        subject             : str   | None,
        body                : str   | None,
        order_number        : str   | None,
    ):
        self.message_id     = message_id
        self.type           = email_type
        self.date           = date
        self.from_address   = from_address
        self.subject        = subject
        self.body           = body
        self.order_number   = order_number

class OcadoReceipt:
    """Class for Ocado Receipts."""
    def __init__(self,
        updated                     : datetime  | date | None,
        order_number                : str       | None,
        mon                         : list[str] | None  = [],
        tue                         : list[str] | None  = [],
        wed                         : list[str] | None  = [],
        thu                         : list[str] | None  = [],
        fri                         : list[str] | None  = [],
        sat                         : list[str] | None  = [],
        sun                         : list[str] | None  = [],
        date_dict                   : dict      | None  = {},
    ):
        self.updated                = updated
        self.order_number           = order_number
        self.mon                    = mon
        self.tue                    = tue
        self.wed                    = wed
        self.thu                    = thu
        self.fri                    = fri
        self.sat                    = sat
        self.sun                    = sun
        self.date_dict              = date_dict
    def toJSON(self):
        order = {}
        for k, v in vars(self).items():
            order[k] = str(v)
        return json.dumps(order)

class OcadoEmails:
    """Class for all retrieved emails."""
    def __init__(self,
        orders              : list[str],
        cancelled           : list[OcadoEmail],
        confirmations       : list[OcadoEmail],
        total               : OcadoEmail | None,
        receipt             : OcadoReceipt | None,
    ):
        self.orders         = orders
        self.cancelled      = cancelled
        self.confirmations  = confirmations
        self.total          = total
        self.receipt        = receipt

class OcadoOrder:
    """Class for Ocado orders."""
    def __init__(self,
        updated                     : datetime | date | None,
        order_number                : str      | None,
        delivery_datetime           : datetime | None,
        delivery_window_end         : datetime | None,
        edit_datetime               : datetime | None,
        estimated_total             : str      | None,
    ):
        self.updated                = updated
        self.order_number           = order_number
        self.delivery_datetime      = delivery_datetime
        self.delivery_window_end    = delivery_window_end
        self.edit_datetime          = edit_datetime
        self.estimated_total        = estimated_total
    def toJSON(self):
        order = {}
        for k, v in vars(self).items():
            order[k] = str(v)
        return json.dumps(order)

EMPTY_ORDER = OcadoOrder(
        updated             = datetime.now(),
        order_number        = None,
        delivery_datetime   = None,
        delivery_window_end = None,
        edit_datetime       = None,
        estimated_total     = None,
    )

def capitalise(text):
    return text[0].upper() + text[1:]

class BBDLists:
    """Class for a collection of BBD lists"""
    days_list               = DAYS[:-1]
    long_days_list          = LONG_DAYS
    header_string           = STRING_HEADER
    plus_string             = STRING_PLUS
    regex_date              = REGEX_DATE_FULL
    columns_regex           = REGEX_COLUMNS
    complete_columns_regex  = r"^" + columns_regex + r"$"
    amount_regex            = REGEX_AMOUNT
    each_regex              = REGEX_EACH
    def __init__(self,
        index_start         : int  | None,
        index_end           : int  | None,
        delivery_date       : date | None,
        date_dict           : dict | None   = {},
        mon                 : list[str]     = [],
        tue                 : list[str]     = [],
        wed                 : list[str]     = [],
        thu                 : list[str]     = [],
        fri                 : list[str]     = [],
        sat                 : list[str]     = [],
        sun                 : list[str]     = [],
        plus                : list[str]     = [],
    ):
        self.index_start    = index_start
        self.index_end      = index_end
        self.delivery_date  = delivery_date
        self.date_dict      = date_dict
        self.mon            = mon
        self.tue            = tue
        self.wed            = wed
        self.thu            = thu
        self.fri            = fri
        self.sat            = sat
        self.sun            = sun
        self.plus           = plus
    
    def update_bbds(self, receipt_list: list):
        if self.index_start is None or self.index_end is None:
            raise ValueError
        delivery_date_raw = re.search(self.regex_date, receipt_list[11])
        if delivery_date_raw is not None:
            delivery_date_raw = delivery_date_raw.group()
        else:
            delivery_date_regex = r"Delivery date:\s(?:" + REGEX_DAY_FULL + r")\s" + REGEX_DATE_FULL
            delivery_date_raw = re.search(delivery_date_regex, "\n".join(receipt_list))
            if delivery_date_raw is not None:
                delivery_date_raw = delivery_date_raw.group()
        if delivery_date_raw is None:
            raise Exception
        try:
            delivery_date = datetime.strptime(delivery_date_raw,"%d/%m/%Y").date()
        except ValueError:
            raise ValueError("No date retrieved from receipt_list. Last attempt was with %s", delivery_date_raw)
        self.delivery_date = delivery_date
        # We also need to include the dates for the bbds, ideally this would be external, but oh well.
        date_dict = dict()
        # Using the delivery date create the day<->date dict
        for i in range(1, 8):
            date_dict[(delivery_date + timedelta(days=i)).weekday()] = (delivery_date + timedelta(days=i))
        tomorrow = self.long_days_list[(delivery_date + timedelta(days=1)).weekday()]
        self.date_dict = date_dict
        reduced_list = receipt_list[self.index_start + 1:self.index_end]
        # The first day has a prefix so we remove it
        first_day = reduced_list[0].split(' ')[-1]
        # convert tomorrow into an actual day
        if first_day == "tomorrow":
            first_day = tomorrow
        bbd_lists = [[] for _ in range(8)]
        active_index = self.long_days_list.index(first_day) # type: ignore
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
            if re.search(self.complete_columns_regex, line, flags = re.I):
                continue
            bbd_lists[active_index].append(line)
        # There's probably a better and more efficient way of doing this
        updated_bbd_lists = []
        for day in bbd_lists:
            if day:
                # need to recombine and remove the various column bits
                day = ' '.join(day)            
                # start with the most complete strings to remove
                day = re.sub(self.columns_regex, '\n', day, flags = re.I)
                day = re.sub(self.amount_regex, '\n', day, flags = re.I)
                day = re.sub(self.each_regex, '\n', day, flags = re.I)
                day = day.split('\n')
                # remove any whitespace/newlines
                day = list(map(str.strip, day))
                # Now remove any blank entries, some would have been a single space so order is important
                day = list(filter(None, day))
                day = list(map(lambda x:x.lower().capitalize().replace('ocado', 'Ocado').replace('m&s', 'M&S').replace('M&s', 'M&S'), day))
                day = list(map(capitalise, day))
                updated_bbd_lists = updated_bbd_lists + [day]
            else:
                # if there are no items, add an empty list
                updated_bbd_lists = updated_bbd_lists + [[]]
        for i in range(7):
            setattr(self, self.days_list[i].lower(), updated_bbd_lists[i])
        self.longer = updated_bbd_lists[7]
