import httpx
from core.config import EVOLUTION_URL, API_KEY, INSTANCE_NAME


class WhatsAppService:
    def __init__(self):
        self.headers = {
            "apikey": API_KEY,
            "content-type": "application/json"
        }

    async def send_text(self, phone: str, text: str):
        url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
        payload = {"number": phone, "text": text}
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=self.headers)

    async def send_media(self, phone: str):
        url = f"{EVOLUTION_URL}/message/sendMedia/{INSTANCE_NAME}"
        url_img = "https://static.vecteezy.com/system/resources/thumbnails/048/115/758/small/barber-haircut-mascot-png.png"
        payload = {"number": phone, "media": url_img, "mediatype": "image"}
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=self.headers)
