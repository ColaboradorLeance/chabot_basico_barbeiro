from fastapi import Request
from services.message_service import MessageService


class WebhookController:

    async def handle(self, request: Request):
        dados = await request.json()
        evento = dados.get("event")

        if evento != "messages.upsert":
            return {"status": "ignorado", "reason": f"evento_{evento}_nao_suportado"}

        message_data = dados.get("data", {})
        key = message_data.get("key", {})

        if key.get("fromMe") is True:
            return {"status": "ignorado", "reason": "mensagem_propria"}

        service = MessageService()
        await service.process_message(dados)
        return {"status": "recebido"}