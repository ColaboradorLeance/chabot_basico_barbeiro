from services.whatsapp_service import WhatsAppService
import asyncio

class SchedulingService:
    async def process_flow(self, mensagem: str, current_state: str, phone: str) -> dict:
        msg = mensagem.strip().lower()
        whatsapp_service = WhatsAppService()

        if current_state == "START":
            await whatsapp_service.send_media(phone)
            await asyncio.sleep(1)
            msg_start = "💈 Barbearia Evolution\nOlá! O que você deseja utilizar hoje?"
            await whatsapp_service.send_text(phone, msg_start)
            await asyncio.sleep(1)
            await whatsapp_service.send_list(phone)

            return {"next_state": "SERVICE"}

        elif current_state == "SERVICO":
            return {
                "type": "text",
                "next_state": "SERVICE",

            }


        # elif current_state == "DATA":
        #     if msg == "voltar":
        #         return self.process_flow("", "START", context_data)
        #
        #     return {
        #         "type": "text",
        #         "next_state": "HORA",
        #         "extra_data": {"data": msg, "servico": context_data.get("servico")},
        #         "content": f"Data: {msg} 📅\n\nQual horário você prefere? (Ex: 14:00) ou digite *voltar*."
        #     }
        #
        # elif current_state == "HORA":
        #     if msg == "voltar":
        #         # Finge que o usuário clicou no mesmo serviço para pular direto para a pergunta de data
        #         servico_reverso = {"Corte de Cabelo": "corte", "Barba": "barba", "Cabelo + Barba": "combo"}
        #         id_anterior = servico_reverso.get(context_data.get("servico", ""), "corte")
        #         return self.process_flow(id_anterior, "SERVICO", context_data)
        #
        #     hora = msg
        #     servico = context_data.get("servico")
        #     data = context_data.get("data")
        #
        #     return {
        #         "type": "button",
        #         "next_state": "CONFIRMACAO",
        #         "extra_data": {"hora": hora, "data": data, "servico": servico},
        #         "content": {
        #             "text": f"Resumo do Agendamento:\n\n✂️ {servico}\n📅 {data}\n⏰ {hora}\n\nPodemos confirmar?",
        #             "buttons": [
        #                 {"id": "btn_sim", "text": "✅ Confirmar"},
        #                 {"id": "btn_nao", "text": "❌ Cancelar"}
        #             ]
        #         }
        #     }
        #
        # elif current_state == "CONFIRMACAO":
        #     if msg == "btn_sim":
        #         return {"type": "text", "next_state": "FINALIZADO", "extra_data": {},
        #                 "content": "Agendamento confirmado com sucesso! 🎉 Te esperamos na hora marcada."}
        #     elif msg == "btn_nao":
        #         return self.process_flow("", "START", context_data)
        #     else:
        #         return {"type": "text", "next_state": "CONFIRMACAO", "extra_data": context_data,
        #                 "content": "Por favor, clique em Confirmar ou Cancelar."}

        return self.process_flow("", "START", context_data)