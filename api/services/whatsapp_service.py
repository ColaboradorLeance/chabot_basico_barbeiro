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

    async def send_list(self, phone: str):
        url = f"{EVOLUTION_URL}/message/sendList/{INSTANCE_NAME}"

        # Estrutura Flat (v2) conforme exigido pelo seu log de erro
        payload = {
            "number": phone,
            "title": "💈 Barbearia Evolution",  # Exigido pelo erro
            "description": "Escolha o seu serviço:",
            "buttonText": "Ver Catálogo",  # Exigido pelo erro
            "footerText": "Barbearia Evolution",  # Exigido pelo erro
            "sections": [  # Exigido pelo erro
                {
                    "title": "Serviços Disponíveis",
                    "rows": [
                        {
                            "title": "Corte de Cabelo",
                            "description": "R$ 40,00",
                            "rowId": "corte"
                        },
                        {
                            "title": "Barba",
                            "description": "R$ 30,00",
                            "rowId": "barba"
                        }
                    ]
                }
            ]
        }

        headers = {
            "apikey": API_KEY,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)

            print(f"\n--- DEBUG EVOLUTION API ---")
            print(f"Status Code: {response.status_code}")
            print(f"Resposta: {response.text}")
            print(f"---------------------------\n")