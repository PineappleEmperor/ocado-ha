"""Services for the Ocado integration."""
from datetime import datetime
from io import BytesIO
import logging
import re

from pypdf import PdfReader

from .const import DAYS, REGEX_DATE_FULL, REGEX_DAY_FULL, BBDLists, OcadoReceipt
from .utils import FindEndIndex, HeaderIndex

_LOGGER = logging.getLogger(__name__)


async def async_register_services(hass, entry, domain):
    """Register the Ocado integration services."""
    async def handle_process_file(call):
        # Retrieve the file ID from the service call
        file_id = call.data.get("file_id")
        if not file_id:
            _LOGGER.warning("No file ID provided in the service call.")
            return
        # Access the uploaded file from hass.data
        uploaded = hass.data.get("file_upload", {}).get(file_id)
        if not uploaded:
            _LOGGER.warning("No file found for the provided file ID.")
            return
        coordinator = hass.data[domain][entry.entry_id]["coordinator"]
        try:
            reader = PdfReader(BytesIO(uploaded.read()))
            receipt_list = []
            for page in reader.pages:
                receipt_list += page.extract_text().split('\n')
            order_number_regex = r"(?:Order number:\s)\d{10,14}"
            try:
                match = re.search(order_number_regex, receipt_list[10])
                if match:
                    order_number = receipt_list[10].split(":")[1].strip()
                    _LOGGER.debug("order number found (in 10) as %s", order_number)
                else:
                    order_number = re.search(order_number_regex, "\n".join(receipt_list))
                    if order_number is not None:
                        _LOGGER.debug("order number found as %s", order_number)
                        order_number = order_number.group()
                    else:
                        _LOGGER.warning("Failed to extract order number from receipt")
                        order_number = None
            except ValueError:
                _LOGGER.warning("Failed to extract order number from receipt")
                order_number = None
            try:
                # check there's a date
                match = re.search(REGEX_DATE_FULL, receipt_list[11])
                if match:
                    order_date = datetime.strptime(match.group(), "%d/%m/%Y").date()
                else:
                    order_date = None
            except ValueError:
                _LOGGER.warning("Failed to extract order date from receipt")
                order_date = None
            ocado_receipt = OcadoReceipt(order_date, order_number)
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
            delivery_date_raw = re.search(REGEX_DATE_FULL, receipt_list[11])
            if delivery_date_raw is not None:
                delivery_date_raw = delivery_date_raw.group()
                _LOGGER.debug("delivery_date_raw found (in 11) as %s", delivery_date_raw)
            else:
                delivery_date_regex = r"Delivery date:\s(?:" + REGEX_DAY_FULL + r")\s" + REGEX_DATE_FULL
                delivery_date_raw = re.search(delivery_date_regex, "\n".join(receipt_list))
                if delivery_date_raw is not None:
                    delivery_date_raw = delivery_date_raw.group()
                    _LOGGER.debug("delivery_date_raw found (in 7) as %s", delivery_date_raw)
            if delivery_date_raw is None:
                raise ValueError("Could not extract delivery date from receipt")  # noqa: TRY301
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
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Failed to extract BBD details: %s", e)
            ocado_receipt = None
        coordinator.last_uploaded_data = ocado_receipt
        await coordinator.async_request_refresh()
    hass.services.async_register(domain, "process_file", handle_process_file)
