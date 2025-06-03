"""Utilities for Ocado UK"""
import base64
from datetime import date, datetime, timedelta
import email
from email.policy import default as default_policy
from imaplib import IMAP4_SSL as imap
import io
from pypdf import PdfReader
import json
import logging
import re
from typing import Any

from dateutil.parser import parse

from .const import(
    OCADO_ADDRESS,
    OCADO_CUTOFF_SUBJECT,
    OCADO_SMARTPASS_SUBJECT,
    OCADO_SUBJECT_DICT,
    REGEX_DATE,
    REGEX_DATE_FULL,
    REGEX_DAY_FULL,
    REGEX_MONTH_FULL,
    REGEX_YEAR,
    REGEX_TIME,
    REGEX_ORDINALS,
    STRING_NO_BBD,
    REGEX_END_INDEX,
    STRING_FREEZER,
    OcadoEmail,
    OcadoEmails,
    OcadoOrder,
    BBDLists,
    OcadoReceipt,
    EMPTY_ORDER,
    DAYS,
)

_LOGGER = logging.getLogger(__name__)


def get_email_from_address(message: str) -> str:
    """Parse the originating from address and return a lower case string."""    
    message_split = message.split('<')
    if len(message_split)==2:
        return message_split[1][:-1].lower()
    if len(message_split)==1:
        return message.lower()
    _LOGGER.error("No from address was found in email from message.")
    raise ValueError("No from address was found in email from message.")


def get_email_from_datetime(email_date_raw: str) -> date:
    """Parse the date of the email from the given string."""
    email_datetime = parse(email_date_raw, fuzzy=True, dayfirst=True)
    return email_datetime


def get_estimated_total(message: str) -> str:
    """Find and return the estimated total from a 'what you returned' email."""
    pattern = r"Total\s\(estimated\):\s{1,20}(?P<total>\d+.\d{2})\sGBP"
    raw = re.search(pattern, message)
    if raw:
        return raw.group('total')
    _LOGGER.error("Failed to parse estimated total from message.")
    raise ValueError("Failed to parse estimated total from message.")


def get_delivery_datetimes(message: str | None) -> tuple[datetime, datetime] | tuple[None, None]:
    """Parse and return the delivery datetime."""
    pattern = fr"Delivery\sdate:\s{{1,20}}(?:{REGEX_DAY_FULL})\s(?P<day>{REGEX_DATE})\s(?P<month>{REGEX_MONTH_FULL})"
    if message is None:
        return None, None
    raw = re.search(pattern, message)
    if raw:
        month = raw.group('month')
        day = raw.group('day')
    else:
        _LOGGER.error("Delivery date not found when retrieving delivery datetime from message.")
        raise ValueError("Delivery date not found when retrieving delivery datetime from message.")
    pattern = fr"(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})"
    year_raw = re.search(pattern, message)
    if year_raw:
        year = year_raw.group('year')
        # in case the delivery occurs after NY, since the year comes from the edit date
        if year_raw.group('month') == 'December' and month == 'January':
            year = str(int(year) + 1)
    else:
        _LOGGER.error("Year not found when retrieving delivery datetime from message.")
        raise ValueError("Year not found when retrieving delivery datetime from message.")
    pattern = fr"Delivery\stime:\s{{1,20}}(?P<start>{REGEX_TIME})\sand\s(?P<end>{REGEX_TIME})"
    delivery_time_raw = re.search(pattern, message)    
    if delivery_time_raw:
        start_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('start')))
        end_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('end')))
    else:        
        _LOGGER.error("Time not found when retrieving delivery datetime from message.")
        raise ValueError("Time not found when retrieving delivery datetime from message.")
    delivery_datetime_raw = year + '-' + month + '-' + day + ' ' + start_time
    delivery_datetime = datetime.strptime(delivery_datetime_raw,'%Y-%B-%d %I:%M%p')
    delivery_window_end_raw = year + '-' + month + '-' + day + ' ' + end_time
    delivery_window_end = datetime.strptime(delivery_window_end_raw,'%Y-%B-%d %I:%M%p')
    return delivery_datetime, delivery_window_end


def get_edit_datetime(message: str) -> datetime:
    """Parse the edit deadline datetime."""
    pattern = fr"(?:You\scan\sedit\sthis\sorder\suntil:?\s)(?P<time>{REGEX_TIME})(?:\son\s)(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})"
    raw = re.search(pattern, message)
    if raw:
        edit_datetime_raw = raw.group('year') + '-' + raw.group('month') + '-' + raw.group('day') + ' ' + raw.group('time')
        return datetime.strptime(edit_datetime_raw,'%Y-%B-%d %H:%M')
    _LOGGER.error("No edit date found in message.")
    raise ValueError("No edit date found in message.")


def get_order_number(message: str) -> str:
    """Parse the order number."""
    raw = re.search(r"(?:Order\sref(\.|erence):)?(?:Order\sis\s)?(?:\s{1,20})(?P<order_number>\d{10})",message)
    if raw:
        return raw.group('order_number')
    _LOGGER.error("No order number retrieved from message %s.", message[:20])
    raise ValueError("No order number retrieved from message %s.", message[:20])


def capitalise(text: str) -> str:
    """Helper function to capitalise text."""
    return text[0].upper() + text[1:]



# reversed so that we start with the newest message and break on it
def email_triage(self) -> tuple[list[Any], OcadoEmails | None]:
    """Access the IMAP inbox and retrieve all the relevant Ocado UK emails from the last month."""
    _LOGGER.debug("Beginning email triage")
    today = date.today()
    server = imap(host = self.imap_host, port = self.imap_port, timeout= 30)
    server.login(self.email_address, self.password)
    server.select(self.imap_folder, readonly=True)
    pattern = fr'SINCE "{(today - timedelta(days=self.imap_days)).strftime("%d-%b-%Y")}" FROM "{OCADO_ADDRESS}" NOT SUBJECT "{OCADO_CUTOFF_SUBJECT}" NOT SUBJECT "{OCADO_SMARTPASS_SUBJECT}"'
    result, message_ids = server.search(None, pattern)
    if result != "OK":
        _LOGGER.error("Could not connect to inbox.")
        raise ConnectionError("Could not connect to inbox.")
    ocado_cancelled =           []
    ocado_confirmations =       []
    ocado_confirmed_orders =    []
    ocado_total =               None
    ocado_receipt =             None
    # Check the previous message ids and return the old state if they're the same
    if self.data is not None:
        if self.data.get("message_ids") == message_ids:
            _LOGGER.debug("Returning previous state, since message_ids are unchanged.")
            server.close()
            server.logout()
            return message_ids, None
    for message_id in reversed(message_ids[0].split()):
        result, message_data = server.fetch(message_id,"(RFC822)")
        if message_data is None:
            continue
        message_data = message_data[0][1] # type: ignore
        ocado_email = _parse_email(message_id, message_data) # type: ignore
        # If the type of email is a cancellation, add the order number to check for later
        if ocado_email.type == "cancellation":
            ocado_cancelled.append(ocado_email.order_number)
        # If the order number isn't in the list of cancelled order numbers
        if ocado_email.order_number not in ocado_cancelled:
            # This is done first, since if the order number exists already from a confirmation, we still want to add the receipt.
            if ocado_email.type == "receipt":
                # We only care about the most recent receipt
                if ocado_receipt is None:
                    ocado_receipt = OcadoReceipt(ocado_email.date, ocado_email.order_number)
                    email_message = email.message_from_bytes(message_data, policy=default_policy) # type: ignore
                    for part in email_message.iter_attachments():
                        if part.get_content_type() == 'application/pdf':
                            pdf_data = part.get_payload(decode=True)
                            pdf_stream = io.BytesIO(pdf_data) # type: ignore
                            try:
                                reader = PdfReader(pdf_stream)
                                page = reader.pages[0]
                                receipt_list = page.extract_text().split('\n')
                            except:  # noqa: E722
                                receipt_list = []
                                continue
                            # Calculate the indices of the different lists
                            fridge_index = HeaderIndex("Fridge", receipt_list)
                            cupboard_index = HeaderIndex("Cupboard", receipt_list)
                            end_index = FindEndIndex(receipt_list)
                            # Set up the BBD lists
                            fridge = BBDLists(fridge_index, None, None)
                            cupboard = BBDLists(cupboard_index, None, None)
                            # Set the end indices
                            if fridge.index_start is not None:
                                if cupboard.index_start is not None:
                                    fridge.index_end = cupboard.index_start - 2        
                                    cupboard.index_end = end_index
                                else:
                                    fridge.index_end = end_index
                            # Now calculate the BBDs properly
                            delivery_date_raw = re.search(REGEX_DATE_FULL, receipt_list[6])
                            if delivery_date_raw is not None:
                                delivery_date_raw = delivery_date_raw.group()
                                _LOGGER.debug("delivery_date_raw found (in 6) as %s", delivery_date_raw)
                            else:
                                delivery_date_raw = re.search(REGEX_DATE_FULL, receipt_list[7])
                                if delivery_date_raw is not None:
                                    delivery_date_raw = delivery_date_raw.group()
                                    _LOGGER.debug("delivery_date_raw found (in 7) as %s", delivery_date_raw)
                            if delivery_date_raw is None:
                                raise Exception
                            _LOGGER.debug("delivery_date_raw found as %s", delivery_date_raw)
                            fridge.update_bbds(receipt_list)
                            cupboard.update_bbds(receipt_list)
                            # Now save the lists as new attributes
                            for day in DAYS[:-1]:
                                _LOGGER.debug("Attempting to get %s from fridge & cupboard", day)
                                _LOGGER.debug("Fridge: %s", getattr(fridge, day))
                                _LOGGER.debug("Cupboard: %s", getattr(cupboard, day))
                                # I think the number of cupboard bbds will be small, so combining.
                                day_list = getattr(fridge, day) + getattr(cupboard, day)
                                setattr(ocado_receipt, day, day_list)
                            setattr(ocado_receipt, "date_dict", fridge.date_dict)
            elif ocado_email.type == "confirmation":
                # Make sure we're not adding an older version of an order we already have
                if ocado_email.order_number not in ocado_confirmed_orders:
                    ocado_confirmed_orders.append(ocado_email.order_number)
                    ocado_confirmations.append(ocado_email)
            elif ocado_email.type == "new_total":
                # We only care about the most recent new total
                if ocado_total is None:
                    ocado_confirmed_orders.append(ocado_email.order_number)
                    ocado_total = ocado_email


    server.close()
    server.logout()
    # It's possible the total order number is repeated, so remove it
    ocado_orders = list(set(ocado_confirmed_orders))
    triaged_emails = OcadoEmails(
        orders = ocado_orders,
        cancelled = ocado_cancelled,
        confirmations = ocado_confirmations,
        total = ocado_total,
        receipt = ocado_receipt,
    )
    _LOGGER.debug("Returning triaged emails")
    return message_ids, triaged_emails


def _ocado_email_typer(subject: str) -> str:
    """Classify the type of Ocado email."""
    ocado_email_type = OCADO_SUBJECT_DICT.get(subject, "Unknown")
    return ocado_email_type


def _parse_email(message_id: bytes, message_data: bytes) -> OcadoEmail:
    """Given message data, return RetrievedEmail object."""
    email_message = email.message_from_bytes(message_data, policy=default_policy)
    email_date = get_email_from_datetime(email_message.get("Date")) # type: ignore
    email_from_address = get_email_from_address(email_message.get('From')) # type: ignore
    email_subject = email_message.get("Subject")
    email_body = ""
    # multipart will return true if there are attachments, text, html versions of the body, etc.
    # if multipart returns true, get_payload will return a list instead of a string.
    if email_message.is_multipart():
        email_body = (email_message.get_body(preferencelist=('plain','html'))).as_string() # type: ignore
    # best guess with HTML emails, which we need to use in some situations to grab tracking numbers
    else:
        email_body = email_message.get_body().as_string().replace('=','').replace('\n','') # type: ignore
    if re.search(r"base64",email_body):
        # need to remove the encoding info before decoding
        email_body = re.sub(r"(?:.*\n.*)(base64\n\n)","",email_body)
        email_body = base64.b64decode(email_body.encode("utf8")).decode("utf8")
    order_number = get_order_number(email_body)
    # need to add the receipt download for
    ocado_email = OcadoEmail(
        message_id          = message_id,
        email_type          = _ocado_email_typer(email_subject), # type: ignore
        date                = email_date,
        from_address        = email_from_address,
        subject             = email_subject,
        body                = email_body,
        order_number        = order_number,
    )
    return ocado_email


def total_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado total email into an OcadoOrder object."""
    # TODO return order number and actual total.
    message = ocado_email.body
    if message is None:
        return EMPTY_ORDER
    pattern = r"New\sorder\stotal:\s{1,20}(?P<total>\d+.\d{1,2})\sGBP"
    raw = re.search(pattern, message)
    if raw:
        total = raw.group("total")
    else:
        total = None
    total = OcadoOrder(
        updated             = ocado_email.date,
        order_number        = ocado_email.order_number,
        delivery_datetime   = None,
        delivery_window_end = None,
        edit_datetime       = None,
        estimated_total     = total,
    )
    return total


def order_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado confirmation email into an OcadoOrder object."""
    message = ocado_email.body
    if message is None:
        return EMPTY_ORDER
    delivery_datetime, delivery_window_end = get_delivery_datetimes(message)
    order = OcadoOrder(
        updated             = ocado_email.date,
        order_number        = ocado_email.order_number,
        delivery_datetime   = delivery_datetime,
        delivery_window_end = delivery_window_end,
        edit_datetime       = get_edit_datetime(message),
        estimated_total     = get_estimated_total(message),
    )
    return order


def iconify(days: int) -> str:
    """Parse a number of days into an icon."""
    if days < 0:
        return "mdi:close-circle"
    elif days == 0:
        return "mdi:truck-fast"
    elif days > 9:
        return "mdi:numeric-9-plus-circle"
    else:
        return "mdi:numeric-" + str(days) + "-circle"


def bbd_iconify(days: int) -> str:
    """Parse a number of days into a bbd icon."""
    if days < 0:
        return "mdi:close-circle"
    elif days == 0:
        return "mdi:calendar-remove"
    elif days > 9:
        return "mdi:numeric-9-plus-circle"
    else:
        return "mdi:numeric-" + str(days) + "-circle"


def get_window(delivery_datetime: datetime, delivery_window_end: datetime) -> str:
    """Returns the delivery window in string format."""
    start = delivery_datetime.strftime("%H:%M")
    end = delivery_window_end.strftime("%H:%M")
    return start + " - " + end


def sort_orders(orders: list[OcadoOrder]) -> tuple[OcadoOrder, OcadoOrder]:
    """Sorts the list of orders and returns the next and upcoming orders."""
    # First, sort by the date, but note that the first order could be in the distant future.
    orders.sort(key=lambda item:item.delivery_datetime) # type: ignore
    orders.reverse()
    # There's probably a better way of doing this..
    today = date.today()
    now = datetime.now()
    diff = 2**32
    next = EMPTY_ORDER
    upcoming = EMPTY_ORDER
    try:
        for order in orders:
            if (order.delivery_datetime is not None) and (order.delivery_window_end is not None):
                order_date = order.delivery_datetime.date()
                if order_date >= today:
                    # If the order is today, check if it's been delivered
                    if order_date == today:
                        if  order.delivery_window_end < now:
                            continue
                    order_diff = (order_date - today).days
                    # Could have more than one order in a day.. Going to ignore that case
                    if order_diff < diff:
                        upcoming = next
                        next = order
                        diff = order_diff
        return next, upcoming
    except ValueError:
        _LOGGER.error("Failed to sort orders, latest input: %s", order) # type: ignore
        raise ValueError("Failed to sort orders, latest input: %s", order) # type: ignore



def set_order(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    _LOGGER.debug("Setting order")
    if (order.delivery_window_end is not None) and (order.delivery_datetime is not None):
        today = now.date()
        if order.delivery_window_end >= now:
            days_until_next_delivery = (order.delivery_datetime.date() - today).days
            self._attr_state = order.delivery_datetime.date()
            self._attr_icon = iconify(days_until_next_delivery)
            self._hass_custom_attributes = {
                "updated"               : order.updated,
                "order_number"          : order.order_number,
                "delivery_datetime"     : order.delivery_datetime,
                "delivery_window"       : get_window(order.delivery_datetime, order.delivery_window_end),
                "edit_deadline"         : order.edit_datetime,
                "estimated_total"       : order.estimated_total,
            }
            return True
    _LOGGER.debug("Order is not in the future.")
    return False

def set_edit_order(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    _LOGGER.debug("Setting edit order")
    if (order.edit_datetime is not None):
        today = now.date()
        if order.edit_datetime >= now:
            days_until_deadline = (order.edit_datetime.date() - today).days
            self._attr_state = order.edit_datetime
            self._attr_icon = iconify(days_until_deadline)
            attributes = {
                "updated"               : order.updated,
                "order_number"          : order.order_number,
            }
            self._hass_custom_attributes = attributes
            return True
    return False


def set_total(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    _LOGGER.debug("Setting total order")
    if (order.estimated_total is not None):
            self._attr_state = str(order.estimated_total)
            self._attr_icon = "mdi:receipt-text"
            attributes = {
                "updated"               : order.updated,
                "order_number"          : order.order_number,
            }
            self._hass_custom_attributes = attributes
            return True
    return False


def set_bbds(self, email: OcadoReceipt, day: str, now: datetime) -> bool:
    """This function validates a pdf receipt and returns the formatted BBDs."""
    _LOGGER.debug("Setting bbd")
    if hasattr(email, day) is True and hasattr(email, "date_dict") is True:
        today = now.date()
        date_dict = getattr(email, "date_dict")
        day_list = getattr(email, day)
        if day_list is not None: # type: ignore            
            day_date = date_dict.get(DAYS.index(day))
            days_until = (day_date - today).days
            self._attr_state = len(day_list)
            self._attr_icon = bbd_iconify(days_until)
            attributes = {
                "updated"               : email.updated,
                "order_number"          : email.order_number,
                "date"                  : day_date,
                "bbds"                  : day_list,
            }
            self._hass_custom_attributes = attributes
            return True
    return False


def convert_attributes(obj):
    """Function to convert datetimes and dates in objects for serialisation"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def detect_attr_changes(d1: dict,d2: dict) -> bool:
    return hash(json.dumps(d1, sort_keys=True, default=convert_attributes)) != hash(json.dumps(d2, sort_keys=True, default=convert_attributes))


def HeaderIndex(string: str, receipt_list: list) -> int | None:
    """Returns the first index of a header in a list and removes any other occurences from the list."""
    count = receipt_list.count(string)
    indices = []
    if count == 0:
        return None
    index = 0
    while count > 0:
        index = receipt_list.index(string, index)
        indices.append(index)
        index += 1
        count -= 1
    first_index = indices.pop(0)
    for i in range(len(indices)):
        receipt_list.pop(indices[i])
    return first_index


def BBDIndex(string: str, receipt_list: list) -> list[int] | None:
    """Returns the indices of all occurences in a list."""
    count = receipt_list.count(string)
    indices = []
    if count == 0:
        return None
    index = 0
    while count > 0:
        index = receipt_list.index(string, index)
        indices.append(index)
        index += 1
        count -= 1
    return indices


def FindEndIndex(receipt_list: list) -> int:
    index = -1
    if STRING_NO_BBD in receipt_list:
        index = receipt_list.index(STRING_NO_BBD)
        return index
    elif STRING_FREEZER in receipt_list:
        index = receipt_list.index(STRING_FREEZER)
        return index
    else:
        for i in range(len(receipt_list)):
            if re.search(REGEX_END_INDEX, receipt_list[i]):
                index = receipt_list[i]
                break
        return index
