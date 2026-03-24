from fastapi import APIRouter, Request
from controllers.webhook_controller import WebhookController

router = APIRouter()

@router.post("/webhook")
async def receber_dados(request: Request):
    controller = WebhookController()
    return await controller.handle(request)
