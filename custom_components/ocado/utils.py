"""Utilities for Ocado UK."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from imaplib import IMAP4_SSL as imap
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from dateutil.parser import parse

from homeassistant.util import dt as dt_util

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
    ORDER_NUMBER_SHORT_LEN,
    REGEX_APM_TIME,
    REGEX_DATE,
    REGEX_DAY_FULL,
    REGEX_EDIT_UNTIL,
    REGEX_ISO_TIME,
    REGEX_MISSING_ITEM,
    REGEX_MONTH_FULL,
    REGEX_ORDINALS,
    REGEX_SUBSTITUTION,
    REGEX_VOUCHER_CODE,
    REGEX_YEAR,
    OcadoAuthError,
    OcadoDeliveryUpdate,
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
    ocado_delivery_update =     None
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
            elif ocado_email.email_type == "delivery_update":
                if ocado_delivery_update is None:
                    ocado_delivery_update = ocado_email
                    _LOGGER.debug("Added a delivery update for order %s.", ocado_email.order_number)
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
        delivery_update = ocado_delivery_update,
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


def parse_substitutions(body: str) -> list[dict[str, str]]:
    """Return the ordered/sent item pairs from a delivery-update email body."""
    return [
        {"ordered": match.group(2).strip(), "sent": match.group(4).strip()}
        for match in re.finditer(REGEX_SUBSTITUTION, body)
    ]


def parse_missing_items(body: str) -> list[dict[str, Any]]:
    """Return the missing items, ignoring bullets that belong to substitution pairs."""
    without_subs = re.sub(REGEX_SUBSTITUTION, "", body)
    return [
        {"qty": int(match.group(1)), "item": match.group(2).strip()}
        for match in re.finditer(REGEX_MISSING_ITEM, without_subs)
    ]


def delivery_update_parse(ocado_email: OcadoEmail) -> OcadoDeliveryUpdate:
    """Parse a delivery-day update email into missing and substituted items."""
    body = ocado_email.body or ""
    return OcadoDeliveryUpdate(
        updated             = ocado_email.email_date,
        order_number        = ocado_email.order_number,
        missing             = parse_missing_items(body),
        substitutions       = parse_substitutions(body),
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


def _order_number_fields(order: OcadoOrder) -> dict[str, str]:
    """Full and shortened order-number token values."""
    number = order.order_number or ""
    return {
        "order_number": number,
        "order_number_short": number[-ORDER_NUMBER_SHORT_LEN:],
    }


def delivery_title_fields(order: OcadoOrder) -> dict[str, str]:
    """Token values available to the delivery event title."""
    fields = _order_number_fields(order)
    start, end = order.delivery_datetime, order.delivery_window_end
    fields["total"] = order.estimated_total or ""
    fields["date"] = dt_util.as_local(start).strftime("%d/%m/%Y") if start else ""
    fields["window"] = get_window(start, end) if start and end else ""
    return fields


def edit_title_fields(order: OcadoOrder) -> dict[str, str]:
    """Token values available to the edit-deadline event title."""
    fields = _order_number_fields(order)
    deadline = order.edit_datetime
    fields["deadline"] = (
        dt_util.as_local(deadline).strftime("%d/%m/%Y %H:%M") if deadline else ""
    )
    return fields


def render_event_title(fmt: str, fields: dict[str, str], default: str) -> str:
    """Format an event title, falling back to the default on a bad template."""
    try:
        return fmt.format(**fields)
    except (KeyError, IndexError, ValueError):
        return default.format(**fields)


def validate_title_template(fmt: str, tokens: tuple[str, ...]) -> None:
    """Raise ValueError if a title template uses unknown tokens or bad braces."""
    try:
        fmt.format(**dict.fromkeys(tokens, ""))
    except (KeyError, IndexError, ValueError) as err:
        raise ValueError(f"Invalid title template: {err}") from err


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



def active_delivery(data: dict[str, Any] | None, now: datetime) -> OcadoOrder | None:
    """Return the soonest order whose delivery window has not yet ended.

    Prefers the ``next`` order, falling back to ``upcoming`` once the next
    order's window has passed. Recomputed on every read, so the sensor rolls
    onto the following order automatically with no timer.
    """
    if not data:
        return None
    for key in ("next", "upcoming"):
        order = data.get(key)
        if order and order.delivery_window_end and order.delivery_window_end >= now:
            return order
    return None


def active_edit(data: dict[str, Any] | None, now: datetime) -> OcadoOrder | None:
    """Return the soonest order whose edit deadline has not yet passed."""
    if not data:
        return None
    for key in ("next", "upcoming"):
        order = data.get(key)
        if order and order.edit_datetime and order.edit_datetime >= now:
            return order
    return None


def upcoming_delivery(data: dict[str, Any] | None, now: datetime) -> OcadoOrder | None:
    """Return the ``upcoming`` order while its delivery window is still in the future."""
    if not data:
        return None
    order = data.get("upcoming")
    if order and order.delivery_window_end and order.delivery_window_end >= now:
        return order
    return None


def delivery_attributes(order: OcadoOrder | None) -> dict[str, Any]:
    """State attributes for a delivery sensor; all-``None`` when there's no order."""
    if order is None:
        return {
            "updated"           : None,
            "order_number"      : None,
            "delivery_datetime" : None,
            "delivery_window"   : None,
            "edit_deadline"     : None,
            "estimated_total"   : None,
        }
    start, end = order.delivery_datetime, order.delivery_window_end
    return {
        "updated"           : order.updated,
        "order_number"      : order.order_number,
        "delivery_datetime" : start,
        "delivery_window"   : get_window(start, end) if start and end else None,
        "edit_deadline"     : order.edit_datetime,
        "estimated_total"   : order.estimated_total,
    }


def edit_attributes(order: OcadoOrder | None) -> dict[str, Any]:
    """State attributes for an edit-deadline sensor; all-``None`` when there's no order."""
    if order is None:
        return {"updated": None, "order_number": None}
    return {"updated": order.updated, "order_number": order.order_number}



def voucher_if_valid(data: dict[str, Any] | None, now: datetime) -> OcadoVoucher | None:
    """Return the cached voucher while it still has an amount and is in date."""
    voucher = data.get("voucher") if data else None
    if voucher is None or voucher.amount is None:
        return None
    validity = voucher.voucher_validity
    if validity is not None:
        validity_dt = (
            validity if isinstance(validity, datetime)
            else datetime.combine(validity, datetime.min.time())
        )
        if validity_dt < now:
            return None
    return voucher


def voucher_attributes(voucher: OcadoVoucher | None) -> dict[str, Any]:
    """State attributes for the voucher sensor; all-``None`` when there's no valid voucher."""
    if voucher is None:
        return {"updated": None, "voucher": None, "amount": None, "valid_until": None}
    return {
        "updated"     : voucher.issue_date,
        "voucher"     : voucher.voucher,
        "amount"      : voucher.amount,
        "valid_until" : voucher.voucher_validity,
    }
