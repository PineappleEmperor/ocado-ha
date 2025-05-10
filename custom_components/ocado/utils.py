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
)

_LOGGER = logging.getLogger(__name__)


def get_email_from_address(message: str) -> str:
    """Parse the originating from address and return a lower case string."""    
    message_from = message.get('From')
    message_split = message_from.split('<')
    if len(message_split)==2:
        return message_split[1][:-1].lower()
    if len(message_split)==1:
        return message_from.lower()
    _LOGGER.error("No from address was found in email %s", message.get('Subject'))
    raise ValueError(f"No from address was found in email {message.get('Subject')}")


def get_email_from_date(email_date_raw: str) -> date:
    """Parse the date of the email from the given string."""
    email_datetime = parse(email_date_raw, fuzzy=True, dayfirst=True)
    return email_datetime.date()


def get_estimated_total(message: str) -> str:
    """Find and return the estimated total from a 'what you returned' email."""
    raw = re.search(r"Total\s\(estimated\):\s{1,20}(?P<total>\d+.\d{2})\sGBP",message)
    if raw:
        return raw.group('total')
    _LOGGER.error("Failed to parse estimated total from message %s.", message.get('Subject'))
    raise ValueError(f"Failed to parse estimated total from message {message.get('Subject')}.")


def get_delivery_datetimes(message: str) -> list[datetime] | None:
    """Parse and return the delivery datetime."""
    raw = re.search(fr"Delivery\sdate:\s{1,20}(?:{REGEX_DAY_FULL})\s(?P<day>{REGEX_DATE})\s(?P<month>{REGEX_MONTH_FULL})",message)
    if raw:
        raw = raw.group(0)
        month = raw.group('month')
        day = raw.group('day')
    else:
        _LOGGER.error("Delivery date not found when retrieving delivery datetime from message.")
        raise ValueError("Delivery date not found when retrieving delivery datetime from message.")
    year_raw = re.search(rf"(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})",message)
    if year_raw:
        year = year_raw.group('year')
        # in case the delivery occurs after NY, since the year comes from the edit date
        if year_raw.group('month') == 'December' and month == 'January':
            year = str(int(year) + 1)
    else:
        _LOGGER.error("Year not found when retrieving delivery datetime from message.")
        raise ValueError("Year not found when retrieving delivery datetime from message.")
    delivery_time_raw = re.search(fr"Delivery\stime:\s{1,20}(?P<start>{REGEX_TIME})\s-\s(?P<end>{REGEX_TIME})",message)
    if delivery_time_raw:
        start_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('start')))
        end_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('end')))
    else:        
        _LOGGER.error("Start time not found when retrieving delivery datetime from message %s.", message.get('Subject'))
        raise ValueError(f"Start time not found when retrieving delivery datetime from message {message.get('Subject')}.")
    delivery_datetime_raw = year + '-' + month + '-' + day + ' ' + start_time
    delivery_datetime = datetime.strptime(delivery_datetime_raw,'%Y-%B-%d %I:%M%p')
    delivery_window_end_raw = year + '-' + month + '-' + day + ' ' + end_time
    delivery_window_end = datetime.strptime(delivery_window_end_raw,'%Y-%B-%d %I:%M%p')
    return delivery_datetime, delivery_window_end


def get_edit_datetime(message: str) -> datetime:
    """Parse the edit deadline datetime."""
    raw = re.search(fr"(?:You\scan\sedit\sthis\sorder\suntil:?\s)(?P<time>({REGEX_TIME})(?:on\s)(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>({REGEX_YEAR})",message)
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
    _LOGGER.error("No order number retrieved from message.")
    raise ValueError("No order number retrieved from message.")


def capitalise(text: str) -> str:
    """Helper function to capitalise text."""
    return text[0].upper() + text[1:]



# reversed so that we start with the newest message and break on it
def email_triage(imap_account_email: str,imap_account_password: str,imap_server: str, imap_port: int, imap_folder: str, imap_days: int) -> OcadoEmails:
    """Access the IMAP inbox and retrieve all the relevant Ocado UK emails from the last month."""
    today = date.today()
    server = imap(host = imap_server, port = imap_port, timeout= 30)
    server.login(imap_account_email, imap_account_password)
    server.select(imap_folder, readonly=True)
    flags = fr'SINCE "{(today - timedelta(days=imap_days)).strftime("%d-%b-%Y")}" FROM "{OCADO_ADDRESS}" NOT SUBJECT "{OCADO_CUTOFF_SUBJECT}"'
    result, message_ids = server.search(None,flags)
    if result != "OK":
        _LOGGER.error("Could not connect to inbox.")
        raise ConnectionError("Could not connect to inbox.")
    ocado_cancelled =       []
    ocado_confirmations =   []
    ocado_orders =          []
    ocado_new_totals =      []
    ocado_receipts =        []
    for message_id in reversed(message_ids[0].split()):
        result, message_data = server.fetch(message_id,"(RFC822)")
        message_data = message_data[0][1]
        ocado_email = _parse_email(message_id, message_data)
        # If the type of email is a cancellation, add the order number to check for later
        if ocado_email.type == "cancellation":
            ocado_cancelled.append(ocado_email.order_number)
        # If the order number isn't in the list of cancelled order numbers
        if ocado_email.order_number not in ocado_cancelled:
            # Make sure we're not adding an older version of an order we already have
            if ocado_email.order_number not in ocado_orders:
                ocado_orders.append(ocado_email.order_number)
            # Next, put it into the correct list
            if ocado_email.type == "confirmation":
                ocado_confirmations.append(ocado_email)
            elif ocado_email.type == "new_total":
                ocado_new_totals.append(ocado_email)
            elif ocado_email.type == "receipt":
                # We only care about the most recent receipt
                if len(ocado_receipts) == 0:
                    ocado_receipts.append(ocado_email)                    
                    # TODO add code to download the receipt attachment
                    # ocado_email.message_id
    server.close()
    server.logout()
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
    ocado_email_type = OCADO_SUBJECT_DICT.get(subject, default = None)
    return ocado_email_type


def _parse_email(message_id: bytes, message_data: bytes) -> OcadoEmail:
    """Given message data, return RetrievedEmail object."""
    email_message = email.message_from_bytes(message_data, policy=default_policy)
    email_date = get_email_from_date(email_message.get("Date"))
    email_from_address = get_email_from_address(email_message)
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


def order_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado confirmation email into an OcadoOrder object."""
    message = ocado_email.body
    delivery_datetime, delivery_window_end = get_delivery_datetimes(message)
    order = OcadoOrder(
        order_number = ocado_email.order_number,
        delivery_datetime = delivery_datetime,
        delivery_window_end = delivery_window_end,
        edit_datetime = get_edit_datetime(message),
        estimated_total = get_estimated_total(message),
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


def get_window(delivery_datetime: datetime, delivery_window_end: datetime) -> str:
    """Returns the delivery window in string format."""
    start = delivery_datetime.strftime("%H:%M")
    end = delivery_window_end.strftime("%H:%M")
    return start + " - " + end