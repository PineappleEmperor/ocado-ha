from homeassistant.components.file_upload import async_get_uploaded_file
from io import BytesIO
from pypdf import PdfReader

async def async_register_services(hass, entry, domain):
    async def handle_process_file(call):
        file_info = entry.options.get("file_info") or entry.data.get("file_info")
        if not file_info:
            return
        uploaded = await async_get_uploaded_file(hass, file_info["file_id"])
        try:
            reader = PdfReader(BytesIO(uploaded.read()))
            receipt_list = []
            for page in reader.pages:
                receipt_list += page.extract_text().split('\n')
        except:
            receipt_list = []
    hass.services.async_register(domain, "process_file", handle_process_file)
