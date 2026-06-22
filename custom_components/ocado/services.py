"""Services for the Ocado integration."""
from datetime import datetime
from io import BytesIO
import logging
import re

from pypdf import PdfReader

from .const import REGEX_DATE_FULL, OcadoReceipt

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
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Failed to process uploaded receipt: %s", e)
            ocado_receipt = None
        coordinator.last_uploaded_data = ocado_receipt
        await coordinator.async_request_refresh()
    hass.services.async_register(domain, "process_file", handle_process_file)
