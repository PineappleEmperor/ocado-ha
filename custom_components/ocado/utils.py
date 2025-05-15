"""Utilities for Ocado UK"""
import base64
from datetime import date, datetime, timedelta, timezone
import email
from email.policy import default as default_policy
from imaplib import IMAP4_SSL as imap
import logging
import re

from dateutil.parser import parse

from .const import(
    OCADO_ADDRESS,
    OCADO_CUTOFF_SUBJECT,
    OCADO_SMARTPASS_SUBJECT,
    OCADO_SUBJECT_DICT,
    REGEX_DATE,
    REGEX_DAY_FULL,
    REGEX_MONTH_FULL,
    REGEX_YEAR,
    REGEX_TIME,
    REGEX_ORDINALS,
    OcadoEmail,
    OcadoEmails,
    OcadoOrder,
    EMPTY_ORDER,
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
    raw = re.search(pattern ,message)
    if raw:
        return raw.group('total')
    _LOGGER.error("Failed to parse estimated total from message.")
    raise ValueError("Failed to parse estimated total from message.")


def get_delivery_datetimes(message: str) -> list[datetime] | None:
    """Parse and return the delivery datetime."""
    raw = re.search(fr"Delivery\sdate:\s{{1,20}}(?:{REGEX_DAY_FULL})\s(?P<day>{REGEX_DATE})\s(?P<month>{REGEX_MONTH_FULL})", message)
    if raw:
        month = raw.group('month')
        day = raw.group('day')
    else:
        _LOGGER.error("Delivery date not found when retrieving delivery datetime from message.")
        raise ValueError("Delivery date not found when retrieving delivery datetime from message.")
    year_raw = re.search(fr"(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})", message)
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
    raw = re.search(r"(?:Order\sref\.:)?(?:Order\sis\s)?(?:\s{1,20})(?P<order_number>\d{10})",message)
    if raw:
        return raw.group('order_number')
    _LOGGER.error("No order number retrieved from message %s.", message[:20])
    raise ValueError("No order number retrieved from message %s.", message[:20])


def capitalise(text: str) -> str:
    """Helper function to capitalise text."""
    return text[0].upper() + text[1:]



# reversed so that we start with the newest message and break on it
def email_triage(self) -> OcadoEmails:
    # imap_account_email: str,imap_account_password: str,imap_server: str, imap_port: int, imap_folder: str, imap_days: int) -> OcadoEmails:
    """Access the IMAP inbox and retrieve all the relevant Ocado UK emails from the last month."""
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
    ocado_totalled_orders =     []
    ocado_new_totals =          []
    ocado_receipts =            []
    # total = len(message_ids[0].split())
    # _LOGGER.debug("Beginning triaging of %s emails retrieved.", str(total))
    # i = 0
    for message_id in reversed(message_ids[0].split()):
        # i += 1
        # _LOGGER.debug("Starting on message %s/%s", str(i), str(total))
        result, message_data = server.fetch(message_id,"(RFC822)")
        message_data = message_data[0][1]
        ocado_email = _parse_email(message_id, message_data)
        # If the type of email is a cancellation, add the order number to check for later
        if ocado_email.type == "cancellation":
            # _LOGGER.debug("Cancellation email found and added to cancelled orders.")
            ocado_cancelled.append(ocado_email.order_number)
        # If the order number isn't in the list of cancelled order numbers
        if ocado_email.order_number not in ocado_cancelled:
            # This is done first, since if the order number exists already from a confirmation, we still want to add the receipt.
            if ocado_email.type == "receipt":
                # We only care about the most recent receipt
                if len(ocado_receipts) == 0:
                    # _LOGGER.debug("Ocado order (%s) added to receipts.", ocado_email.order_number)
                    ocado_receipts.append(ocado_email)                    
                    # TODO add code to download the receipt attachment
                    # ocado_email.message_id
            elif ocado_email.type == "confirmation":
                # Make sure we're not adding an older version of an order we already have
                # _LOGGER.debug("Confirmed order is not in the list of confirmed orders? %s", ocado_email.order_number not in ocado_confirmed_orders)
                if ocado_email.order_number not in ocado_confirmed_orders:
                    ocado_confirmed_orders.append(ocado_email.order_number)
                    # _LOGGER.debug("Ocado order (%s) added to confirmations.", ocado_email.order_number)
                    ocado_confirmations.append(ocado_email)
            elif ocado_email.type == "new_total":
                # Make sure we're not adding an older version of an order we already have
                if ocado_email.order_number not in ocado_totalled_orders:
                    ocado_totalled_orders.append(ocado_email.order_number)
                    # _LOGGER.debug("Ocado order (%s) added to totals.", ocado_email.order_number)
                    ocado_new_totals.append(ocado_email)


    server.close()
    server.logout()
    _LOGGER.debug("Finished with IMAP and closed the connection.")
    # Combine the order numbers in case the lists aren't the same.
    ocado_orders = ocado_confirmed_orders + list(set(ocado_totalled_orders) - set(ocado_confirmed_orders))
    triaged_emails = OcadoEmails(
        orders = ocado_orders,
        cancelled = ocado_cancelled,
        confirmations = ocado_confirmations,
        new_totals = ocado_new_totals,
        receipts = ocado_receipts,
    )
    return triaged_emails


def _ocado_email_typer(subject: str) -> str:
    """Classify the type of Ocado email."""
    ocado_email_type = OCADO_SUBJECT_DICT.get(subject, None)
    return ocado_email_type


def _parse_email(message_id: bytes, message_data: bytes) -> OcadoEmail:
    """Given message data, return RetrievedEmail object."""
    email_message = email.message_from_bytes(message_data, policy=default_policy)
    email_date = get_email_from_datetime(email_message.get("Date"))
    email_from_address = get_email_from_address(email_message.get('From'))
    email_subject = email_message.get("Subject")
    email_body = ""
    # multipart will return true if there are attachments, text, html versions of the body, etc.
    # if multipart returns true, get_payload will return a list instead of a string.
    if email_message.is_multipart():
        email_body = (email_message.get_body(preferencelist=('plain','html'))).as_string()
    # best guess with HTML emails, which we need to use in some situations to grab tracking numbers
    else:
        email_body = email_message.get_body().as_string().replace('=','').replace('\n','')
    if re.search(r"base64",email_body):
        # need to remove the encoding info before decoding
        email_body = re.sub(r"(?:.*\n.*)(base64\n\n)","",email_body)
        email_body = base64.b64decode(email_body.encode("utf8")).decode("utf8")
    order_number = get_order_number(email_body)
    # need to add the receipt download for
    ocado_email = OcadoEmail(
        message_id = message_id,
        email_type = _ocado_email_typer(email_subject),
        date = email_date,
        from_address = email_from_address,
        subject = email_subject,
        body = email_body,
        order_number = order_number,
    )
    return ocado_email


def receipt_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado receipt email into an OcadoOrder object."""
    # TODO return order number and actual total.
    return ocado_email

def order_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado confirmation email into an OcadoOrder object."""
    message = ocado_email.body
    delivery_datetime, delivery_window_end = get_delivery_datetimes(message)
    # _LOGGER.debug("Successfully retrieved delivery_datetime, and delivery_window_end as %s, %s.", str(delivery_datetime), str(delivery_window_end))
    order = OcadoOrder(
        updated             = ocado_email.date,
        order_number        = ocado_email.order_number,
        delivery_datetime   = delivery_datetime,
        delivery_window_end = delivery_window_end,
        edit_datetime       = get_edit_datetime(message),
        estimated_total     = get_estimated_total(message),
    )
    # _LOGGER.debug("Returning parsed order: %s, %s, %s, %s, %s, %s", order.updated, order.order_number, str(order.delivery_datetime), str(order.delivery_window_end), str(order.edit_datetime), order.estimated_total)
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


def get_window(delivery_datetime: datetime, delivery_window_end: datetime) -> str:
    """Returns the delivery window in string format."""
    start = delivery_datetime.strftime("%H:%M")
    end = delivery_window_end.strftime("%H:%M")
    return start + " - " + end


def sort_orders(orders: list[OcadoOrder]) -> tuple[OcadoOrder, OcadoOrder]:
    """Sorts the list of orders and returns the next and upcoming orders."""
    # First, sort by the date, but note that the first order could be in the distant future.
    # _LOGGER.debug("Initial sort by delivery_datetime.")
    # for order in orders:
    #     _LOGGER.debug("Order %s", order.order_number)
    orders.sort(key=lambda item:item.delivery_datetime)
    orders.reverse()
    _LOGGER.debug("Completed initial sort.")
    # for order in orders:
    #     _LOGGER.debug("Order %s", order.delivery_datetime)
    # so do a for loop, if delivery_datetime is >= today, then do a diff and check against the current diff?
    # There's probably a better way of doing this..
    today = date.today()
    # _LOGGER.debug("Using today = %s", str(today))
    diff = 2**32
    next = EMPTY_ORDER
    upcoming = EMPTY_ORDER
    i = 0
    total = len(orders)
    
    try:
        for order in orders:
            i += 1
            _LOGGER.debug("Sorting with order %s/%s", i, total)            
            if order.delivery_datetime is not None:
                order_date = order.delivery_datetime.date()
                _LOGGER.debug("Order date is %s", str(order_date))
                if order_date >= today:
                    order_diff = (order_date - today).days
                    _LOGGER.debug("order diff is %s", order_diff)
                    # Could have more than one order in a day.. Surely not?!
                    _LOGGER.debug("Checking diff to see if this is the closest email.")
                    if order_diff < diff:
                        _LOGGER.debug("Order diff is smaller!")
                        upcoming = next
                        next = order
                        diff = order_diff
        return next, upcoming
    except ValueError:
        _LOGGER.error("Failed to sort orders, latest input: %s", order)
        raise ValueError("Failed to sort orders, latest input: %s", order)



def set_order(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    if (order.delivery_window_end is not None) and (order.delivery_datetime is not None):
        today = now.date()
        _LOGGER.debug("Order has both datetimes needed.")
        _LOGGER.debug("Order has datetime check: %s is >= %s?: %s", order.delivery_window_end, now, order.delivery_window_end >= now)
        if order.delivery_window_end >= now:
            _LOGGER.debug("Order is in the future.")
            days_until_next_delivery = (order.delivery_datetime.date() - today).days
            self._attr_state = order.delivery_datetime.date()
            self._attr_icon = iconify(days_until_next_delivery)
            attributes = {
                "updated":      order.updated,
                "order_number": order.order_number,
                "delivery_datetime": order.delivery_datetime,
                "delivery_window": get_window(order.delivery_datetime, order.delivery_window_end),
                "edit_deadline": order.edit_datetime,
                "estimated_total": order.estimated_total,
            }
            self._hass_custom_attributes = attributes
            return True
    _LOGGER.debug("Order is not in the future.")
    return False

def set_edit_order(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    if (order.edit_datetime is not None):
        today = now.date()
        if order.edit_datetime >= now:
            days_until_deadline = (order.edit_datetime.date() - today).days
            self._attr_state = order.edit_datetime
            self._attr_icon = iconify(days_until_deadline)
            attributes = {
                "updated":      order.updated,
                "order_number": order.order_number,
            }
            self._hass_custom_attributes = attributes
            return True
    return False
