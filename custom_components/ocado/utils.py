"""Utilities for Ocado UK."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from imaplib import IMAP4_SSL as imap
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from dateutil.parser import parse

from .const import (
    EMPTY_ORDER,
    MARKETING_OCADO_ADDRESS,
    NEW_OCADO_ADDRESS,
    OCADO_ADDRESS,
    OCADO_CUTOFF_SUBJECT,
    OCADO_RENEWAL_SUBJECT,
    OCADO_SMARTPASS_SUBJECT,
    OCADO_SUBJECT_DICT,
    OCADO_VOUCHER_SUBJECT,
    REGEX_APM_TIME,
    REGEX_DATE,
    REGEX_DAY_FULL,
    REGEX_EDIT_UNTIL,
    REGEX_ISO_TIME,
    REGEX_MONTH_FULL,
    REGEX_ORDINALS,
    REGEX_VOUCHER_CODE,
    REGEX_YEAR,
    OcadoAuthError,
    OcadoEmail,
    OcadoEmails,
    OcadoOrder,
    OcadoVoucher,
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
    return parse(email_date_raw, fuzzy=True, dayfirst=True)


def get_estimated_total(message: str) -> str:
    """Find and return the estimated total from a 'what you returned' email."""
    pattern = r"(?:Total\s\(estimated\)\:\s£)(?P<total>\d+.\d{1,2})"
    raw = re.search(pattern, message, re.MULTILINE)
    if raw:
        return raw.group('total')
    pattern = r"Total\s\(estimated\):\s{1,20}(?P<total>\d+.\d{2})\sGBP"
    raw = re.search(pattern, message, re.MULTILINE)
    if raw:
        return raw.group('total')
    _LOGGER.error("Failed to parse estimated total from message.")
    raise ValueError("Failed to parse estimated total from message.")


def get_delivery_datetimes(message: str | None) -> tuple[datetime, datetime] | tuple[None, None]:
    """Parse and return the delivery datetime."""
    if message is None:
        return None, None
    pattern = fr"(?:Delivery\sdate:\s)(?P<day>{REGEX_DATE})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})"
    raw = re.search(pattern, message, re.MULTILINE)
    if raw:
        month = raw.group('month')
        day = raw.group('day')
        year = raw.group('year')
    else:
        pattern = fr"Delivery\sdate:\s{{1,20}}(?:{REGEX_DAY_FULL})\s(?P<day>{REGEX_DATE})\s(?P<month>{REGEX_MONTH_FULL})"
        raw = re.search(pattern, message, re.MULTILINE)
        if raw:
            month = raw.group('month')
            day = raw.group('day')
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
        else:
            _LOGGER.error("Delivery date not found when retrieving delivery datetime from message.")
            raise ValueError("Delivery date not found when retrieving delivery datetime from message.")
    pattern = fr"(?:Delivery\stime:)(?:\sBetween)?(?:\s{{1,20}})(?P<start>{REGEX_ISO_TIME})\sand\s(?P<end>{REGEX_ISO_TIME})"
    delivery_time_raw = re.search(pattern, message, re.MULTILINE)
    if delivery_time_raw:
        _LOGGER.debug("ISO time found")
        start_time = delivery_time_raw.group('start')
        end_time = delivery_time_raw.group('end')
        delivery_datetime_raw = year + '-' + month + '-' + day + ' ' + start_time
        delivery_datetime = datetime.strptime(delivery_datetime_raw,'%Y-%B-%d %H:%M')
        delivery_window_end_raw = year + '-' + month + '-' + day + ' ' + end_time
        delivery_window_end = datetime.strptime(delivery_window_end_raw,'%Y-%B-%d %H:%M')
    else:
        pattern = fr"(?:Delivery\stime:)(?:\sBetween)?(?:\s{{1,20}})(?P<start>{REGEX_APM_TIME})\sand\s(?P<end>{REGEX_APM_TIME})"
        delivery_time_raw = re.search(pattern, message, re.MULTILINE)
        if delivery_time_raw:
            _LOGGER.debug("ISO time found")
            start_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('start')))
            end_time = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",delivery_time_raw.group('end')))
            delivery_datetime_raw = year + '-' + month + '-' + day + ' ' + start_time
            delivery_datetime = datetime.strptime(delivery_datetime_raw,'%Y-%B-%d %I:%M%p')
            delivery_window_end_raw = year + '-' + month + '-' + day + ' ' + end_time
            delivery_window_end = datetime.strptime(delivery_window_end_raw,'%Y-%B-%d %I:%M%p')
        else:
            _LOGGER.error("Time not found when retrieving delivery datetime from message.")
            raise ValueError("Time not found when retrieving delivery datetime from message.")
    return delivery_datetime, delivery_window_end


def get_edit_datetime(message: str) -> datetime:
    """Parse the edit deadline datetime."""
    pattern = fr"{REGEX_EDIT_UNTIL}(?P<time>{REGEX_ISO_TIME})(?:\son\s)(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})"
    raw = re.search(pattern, message)
    _LOGGER.debug("Trying to get edit datetime")
    if raw:
        _LOGGER.debug("First attempt found datetime")
        edit_datetime_raw = raw.group('year') + '-' + raw.group('month') + '-' + raw.group('day') + ' ' + raw.group('time')
        return datetime.strptime(edit_datetime_raw,'%Y-%B-%d %H:%M')
    _LOGGER.debug("Trying backup pattern with non ISO time")
    pattern = fr"{REGEX_EDIT_UNTIL}(?P<time>{REGEX_APM_TIME})(?:\son\s|,\s)?(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})?\s?(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})"
    raw = re.search(pattern, message, re.MULTILINE)
    if raw:
        _LOGGER.debug("Second attempt found datetime")
        edit_datetime_raw = raw.group('year') + '-' + raw.group('month') + '-' + raw.group('day') + ' ' + raw.group('time').replace(" ","").replace(".",":").zfill(7)
        edit_datetime_raw = re.sub(r"pm",r"PM",re.sub(r"am",r"AM",edit_datetime_raw))
        return datetime.strptime(edit_datetime_raw,'%Y-%B-%d %I:%M%p')
    _LOGGER.error("No edit date found in message.")
    raise ValueError("No edit date found in message.")


def get_order_number(message: str) -> str | None:
    """Parse the order number, or return None when absent."""
    raw = re.search(r"(?:Order\sref(?:\.|erence):\s)?(?:Order\sis\s)?(?P<order_number>\d{10,14})",message)
    if raw:
        return raw.group('order_number')
    return None


def get_ics_text(email_message: EmailMessage) -> str | None:
    """Return the text of the first calendar (.ics) part of an email, if present."""
    for part in email_message.walk():
        filename = part.get_filename() or ""
        if part.get_content_type() == "text/calendar" or filename.lower().endswith(".ics"):
            try:
                return part.get_content()
            except (LookupError, ValueError):
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="replace")
    return None


def _unfold_ics(ics_text: str) -> list[str]:
    """Unfold RFC 5545 line continuations (a leading space or tab folds the prior line)."""
    unfolded: list[str] = []
    for line in ics_text.splitlines():
        if line[:1] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _parse_ics_datetime(value: str) -> datetime | None:
    """Parse an ICS date-time value, returning a naive local datetime."""
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parse(value)
    except (ValueError, OverflowError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def parse_ics(ics_text: str) -> tuple[str | None, datetime | None, datetime | None]:
    """Parse an Ocado calendar attachment for the order number and delivery window."""
    order_number = None
    start = None
    end = None
    for line in _unfold_ics(ics_text):
        name, sep, value = line.partition(":")
        if not sep:
            continue
        key = name.split(";", 1)[0].upper()
        if key == "DTSTART":
            start = _parse_ics_datetime(value)
        elif key == "DTEND":
            end = _parse_ics_datetime(value)
        elif key in ("SUMMARY", "DESCRIPTION", "UID") and order_number is None:
            order_number = get_order_number(value)
    if order_number is None:
        order_number = get_order_number(ics_text)
    return order_number, start, end


def capitalise(text: str) -> str:
    """Helper function to capitalise text."""
    return text[0].upper() + text[1:]


# reversed so that we start with the newest message and break on it
def email_triage(self) -> tuple[list[Any], OcadoEmails | None]:
    """Access the IMAP inbox and retrieve all the relevant Ocado UK emails from the last month."""
    _LOGGER.debug("Beginning email triage")
    today = date.today()
    server = imap(host = self.imap_host, port = self.imap_port, timeout= 30)
    try:
        server.login(self.email_address, self.password)
    except imap.error as err:
        raise OcadoAuthError("IMAP login failed") from err
    server.select(self.imap_folder, readonly=True)
    pattern = fr'SINCE "{(today - timedelta(days=self.imap_days)).strftime("%d-%b-%Y")}" (OR (FROM "{OCADO_ADDRESS}") (OR (FROM "{NEW_OCADO_ADDRESS}") (FROM "{MARKETING_OCADO_ADDRESS}"))) NOT SUBJECT "{OCADO_CUTOFF_SUBJECT}" NOT SUBJECT "{OCADO_SMARTPASS_SUBJECT}" NOT SUBJECT "{OCADO_RENEWAL_SUBJECT}"'
    result, message_ids = server.search(None, pattern)
    if result != "OK":
        _LOGGER.error("Could not connect to inbox.")
        raise ConnectionError("Could not connect to inbox.")
    ocado_cancelled =           []
    ocado_confirmations =       []
    ocado_confirmed_orders =    []
    ocado_total =               None
    ocado_voucher =             None
    # Check the previous message ids and return the old state if they're the same
    if self.data is not None:
        if self.data.get("message_ids") == message_ids:
            _LOGGER.debug("Returning previous state, since message_ids are unchanged.")
            server.close()
            server.logout()
            return message_ids, None
    total = len(message_ids[0].split())
    _LOGGER.debug("Beginning triaging of %s emails retrieved.", str(total))
    i=0
    for message_id in reversed(message_ids[0].split()):
        i+=1
        _LOGGER.debug("Starting on message %s/%s", str(i), str(total))
        result, message_data = server.fetch(message_id,"(RFC822)")
        if message_data is None:
            continue
        message_data = message_data[0][1]  # type: ignore[index]
        try:
            ocado_email = _parse_email(message_id, message_data)  # type: ignore[arg-type]
        except ValueError as err:
            _LOGGER.warning("Skipping email %s that could not be parsed: %s", message_id, err)
            continue
        # If the type of email is a cancellation, add the order number to check for later
        if ocado_email.email_type == "cancellation":
            _LOGGER.debug("Cancellation email found and added to cancelled orders.")
            ocado_cancelled.append(ocado_email.order_number)
        # If the order number isn't in the list of cancelled order numbers
        if ocado_email.order_number not in ocado_cancelled:
            if ocado_email.email_type in ("confirmation", "update"):
                # Make sure we're not adding an older version of an order we already have
                _LOGGER.debug("Confirmed order is not in the list of confirmed orders? %s", ocado_email.order_number not in ocado_confirmed_orders)
                if ocado_email.order_number not in ocado_confirmed_orders:
                    ocado_confirmed_orders.append(ocado_email.order_number)
                    ocado_confirmations.append(ocado_email)
                    _LOGGER.debug("Ocado order (%s) added to confirmations.", ocado_email.order_number)
            elif ocado_email.email_type == "new_total":
                # We only care about the most recent new total
                if ocado_total is None:
                    ocado_confirmed_orders.append(ocado_email.order_number)
                    ocado_total = ocado_email
                    _LOGGER.debug("Ocado order (%s) added to totals.", ocado_email.order_number)
            elif ocado_email.email_type == "voucher":
                # We only care about the most recent voucher
                if ocado_voucher is None:
                    ocado_voucher = ocado_email
                    _LOGGER.debug("Added a voucher.")
            else:
                _LOGGER.debug(
                    "Ignoring email subject=%r: unhandled type=%r, order_number=%s.",
                    ocado_email.subject, ocado_email.email_type, ocado_email.order_number,
                )
    server.close()
    server.logout()
    _LOGGER.debug("Finished with IMAP and closed the connection")
    # It's possible the total order number is repeated, so remove it
    ocado_orders = list(set(ocado_confirmed_orders))
    triaged_emails = OcadoEmails(
        orders = ocado_orders,
        cancelled = ocado_cancelled,
        confirmations = ocado_confirmations,
        total = ocado_total,
        voucher = ocado_voucher,
    )
    _LOGGER.debug("Returning triaged emails")
    return message_ids, triaged_emails


def _ocado_email_typer(subject: str | None) -> str:
    """Classify the type of Ocado email."""
    if subject is None:
        return "Unknown"
    ocado_email_type = OCADO_SUBJECT_DICT.get(subject, "Unknown")
    if ocado_email_type == "Unknown":
        try:
            if OCADO_VOUCHER_SUBJECT in subject:
                ocado_email_type = "voucher"
        except TypeError:
            pass
    return ocado_email_type


def _parse_email(message_id: bytes, message_data: bytes) -> OcadoEmail:
    """Given message data, return RetrievedEmail object."""
    email_message = BytesParser(policy=policy.default).parsebytes(message_data)
    # First try plaintext
    email_body = ""
    plaintext = email_message.get_body(preferencelist=('plain',))
    if plaintext:
        email_body = plaintext.get_content()
    else:
        # Now fallback to HTML..
        html = email_message.get_body(preferencelist=('html',))
        if html:
            html_body = html.get_content()
            soup = BeautifulSoup(html_body, 'html.parser')
            email_body = soup.get_text(separator='\n', strip=True)
        else:
            _LOGGER.error("Email subject %s body couldn't be parsed.", email_message.get("Subject"))
            raise ValueError(f"Email subject {email_message.get("Subject")} body couldn't be parsed.")
    ics_order_number = None
    ics_delivery_start = None
    ics_delivery_end = None
    ics_text = get_ics_text(email_message)
    if ics_text:
        ics_order_number, ics_delivery_start, ics_delivery_end = parse_ics(ics_text)
    order_number = ics_order_number or get_order_number(email_body)
    date_header = email_message.get("Date")
    from_header = email_message.get("From")
    if date_header is None or from_header is None:
        raise ValueError("Email is missing a Date or From header.")
    email_date = get_email_from_datetime(str(date_header))
    email_from_address = get_email_from_address(str(from_header))
    email_subject = email_message.get("Subject")
    email_type = _ocado_email_typer(email_subject)
    if email_type == "Unknown" and re.search(REGEX_VOUCHER_CODE, email_body, re.IGNORECASE):
        email_type = "voucher"
    return OcadoEmail(
        message_id          = message_id,
        email_type          = email_type,
        email_date          = email_date,
        from_address        = email_from_address,
        subject             = email_subject,
        body                = email_body,
        order_number        = order_number,
        delivery_datetime   = ics_delivery_start,
        delivery_window_end = ics_delivery_end,
    )


def total_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado total email into an OcadoOrder object."""
    message = ocado_email.body
    if message is None:
        return EMPTY_ORDER
    pattern = r"(?:New\sorder\stotal\s=\s£)(?P<total>\d+.\d{1,2})"
    raw = re.search(pattern, message, re.MULTILINE)
    if raw:
        total = raw.group("total")
    else:
        pattern = r"New\sorder\stotal:\s{1,20}(?P<total>\d+.\d{1,2})\sGBP"
        raw = re.search(pattern, message)
        if raw:
            total = raw.group("total")
        else:
            total = None
    return OcadoOrder(
        updated             = ocado_email.email_date,
        order_number        = ocado_email.order_number,
        delivery_datetime   = None,
        delivery_window_end = None,
        edit_datetime       = None,
        estimated_total     = total,
    )


def voucher_parse(ocado_email: OcadoEmail) -> OcadoVoucher:
    """Parse an Ocado Price Promise voucher email into an OcadoVoucher object."""
    message = ocado_email.body or ""
    subject = ocado_email.subject or ""
    subject_raw = re.search(r"£\s?(?P<amount>\d+\.\d{2})", subject)
    body_raw = re.search(r"£\s?(?P<amount>\d+\.\d{2})\s+voucher", message, re.IGNORECASE)
    if body_raw is None:
        body_raw = re.search(r"£\s?(?P<amount>\d+\.\d{2})", message)
    subject_amount = subject_raw.group("amount") if subject_raw else None
    body_amount = body_raw.group("amount") if body_raw else None
    if subject_amount and body_amount and subject_amount != body_amount:
        _LOGGER.warning(
            "Voucher amount mismatch: subject %s vs body %s; using subject.", subject_amount, body_amount
        )
    amount = subject_amount or body_amount
    voucher_code = None
    code_raw = re.search(REGEX_VOUCHER_CODE, message, re.IGNORECASE)
    if code_raw:
        voucher_code = code_raw.group(0)
    voucher_validity = None
    slash_raw = re.search(
        r"valid\s(?:for\sdeliveries\s)?until\s+(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})",
        message,
        re.IGNORECASE,
    )
    if slash_raw:
        voucher_validity = datetime.strptime(
            f"{slash_raw.group('year')}-{slash_raw.group('month')}-{slash_raw.group('day')}", "%Y-%m-%d"
        )
    else:
        validity_raw = re.search(
            fr"(?:valid\suntil|expires?(?:\son)?)\s*:?\s*(?P<day>{REGEX_DATE})(?:{REGEX_ORDINALS})?\s(?P<month>{REGEX_MONTH_FULL})\s(?P<year>{REGEX_YEAR})",
            message,
            re.IGNORECASE,
        )
        if validity_raw:
            validity_str = validity_raw.group("year") + "-" + validity_raw.group("month") + "-" + validity_raw.group("day")
            voucher_validity = datetime.strptime(validity_str, "%Y-%B-%d")
    return OcadoVoucher(
        issue_date          = ocado_email.email_date,
        voucher_validity    = voucher_validity,
        voucher             = voucher_code,
        amount              = amount,
    )


def order_parse(ocado_email: OcadoEmail) -> OcadoOrder:
    """Parse an Ocado confirmation email into an OcadoOrder object."""
    message = ocado_email.body
    if message is None:
        return EMPTY_ORDER
    if ocado_email.delivery_datetime is not None and ocado_email.delivery_window_end is not None:
        delivery_datetime = ocado_email.delivery_datetime
        delivery_window_end = ocado_email.delivery_window_end
    else:
        delivery_datetime, delivery_window_end = get_delivery_datetimes(message)
    return OcadoOrder(
        updated             = ocado_email.email_date,
        order_number        = ocado_email.order_number,
        delivery_datetime   = delivery_datetime,
        delivery_window_end = delivery_window_end,
        edit_datetime       = get_edit_datetime(message),
        estimated_total     = get_estimated_total(message),
    )


def iconify(days: int) -> str:
    """Parse a number of days into an icon."""
    if days < 0:
        return "mdi:close-circle"
    if days == 0:
        return "mdi:truck-fast"
    if days > 9:
        return "mdi:numeric-9-plus-circle"
    return "mdi:numeric-" + str(days) + "-circle"


def get_window(delivery_datetime: datetime, delivery_window_end: datetime) -> str:
    """Returns the delivery window in string format."""
    start = delivery_datetime.strftime("%H:%M")
    end = delivery_window_end.strftime("%H:%M")
    return start + " - " + end


def sort_orders(orders: list[OcadoOrder]) -> tuple[OcadoOrder, OcadoOrder]:
    """Sorts the list of orders and returns the next and upcoming orders."""
    # First, sort by the date, but note that the first order could be in the distant future.
    orders.sort(key=lambda item: item.delivery_datetime or datetime.min)
    orders.reverse()
    # There's probably a better way of doing this..
    today = date.today()
    now = datetime.now()
    diff = 2**32
    next_order = EMPTY_ORDER
    upcoming_order = EMPTY_ORDER
    for order in orders:
        if (order.delivery_datetime is not None) and (order.delivery_window_end is not None):
            order_date = order.delivery_datetime.date()
            if order_date >= today:
                # If the order is today, check if it's been delivered
                if order_date == today and order.delivery_window_end < now:
                    continue
                order_diff = (order_date - today).days
                # Could have more than one order in a day.. Going to ignore that case
                if order_diff < diff:
                    upcoming_order = next_order
                    next_order = order
                    diff = order_diff
    return next_order, upcoming_order



def set_order(self, order: OcadoOrder, now: datetime) -> bool:
    """This function validates an order is in the future and sets the state and attributes if it is."""
    _LOGGER.debug("Setting order")
    if (order.delivery_window_end is not None) and (order.delivery_datetime is not None):
        today = now.date()
        if order.delivery_window_end >= now:
            days_until_next_delivery = (order.delivery_datetime.date() - today).days
            self._attr_native_value = order.delivery_datetime.date()
            self._attr_icon = iconify(days_until_next_delivery)
            self._attr_extra_state_attributes = {
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
            self._attr_native_value = order.edit_datetime
            self._attr_icon = iconify(days_until_deadline)
            attributes = {
                "updated"               : order.updated,
                "order_number"          : order.order_number,
            }
            self._attr_extra_state_attributes = attributes
            return True
    return False





def set_voucher(self, voucher: OcadoVoucher, now: datetime) -> bool:
    """This function sets the state and attributes if the voucher is still valid."""
    _LOGGER.debug("Setting voucher")
    if voucher.amount is None:
        return False
    if voucher.voucher_validity is not None:
        validity = voucher.voucher_validity
        validity_dt = validity if isinstance(validity, datetime) else datetime.combine(validity, datetime.min.time())
        if validity_dt < now:
            return False
    self._attr_native_value = float(voucher.amount)
    self._attr_icon = "mdi:receipt-text"
    self._attr_extra_state_attributes = {
        "updated"               : voucher.issue_date,
        "voucher"               : voucher.voucher,
        "amount"                : voucher.amount,
        "valid_until"           : voucher.voucher_validity,
    }
    return True


def convert_attributes(obj):
    """Function to convert datetimes and dates in objects for serialisation."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def detect_attr_changes(d1: dict, d2: dict) -> bool:
    """Return True if the two attribute dicts differ once serialised."""
    return hash(json.dumps(d1, sort_keys=True, default=convert_attributes)) != hash(json.dumps(d2, sort_keys=True, default=convert_attributes))
