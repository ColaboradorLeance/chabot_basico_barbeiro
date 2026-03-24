from services.scheduling_service import SchedulingService
from services.whatsapp_service import WhatsAppService
from repositories.appointment_repository import AppointmentRepository


class MessageService:
    async def process_message(self, data: dict):
        mensagem = self._extract_message(data)
        phone = self._extract_remote_jid(data)
        message_id = self._extract_message_id(data)
        if not mensagem or not phone:
            return

        clean_phone = phone.split("@")[0]

        repo = AppointmentRepository()
        if repo.message_already_processed(message_id):
            print(f"🚫 Mensagem duplicada ignorada: {message_id}")
            return

        repo = AppointmentRepository()
        repo.save_message_id(message_id)
        repo = AppointmentRepository()

        if mensagem.lower() == "reset":
            repo.save({"phone": clean_phone, "state": "START"})
            whatsapp = WhatsAppService()
            await whatsapp.send_text(clean_phone, "🔄 Fluxo resetado. Mande um 'Oi' para recomeçar.")
            from repositories.database import reset_database
            reset_database()
            return

        current_state, context_data = repo.get_user_state(clean_phone)
        scheduling = SchedulingService()
        resultado = await scheduling.process_flow(mensagem, current_state, clean_phone)

        # Salva o novo estado
        repo.save({
            "phone": clean_phone,
            "state": resultado.get("next_state"),
            "last_message": mensagem
        })

    def _extract_message(self, data: dict) -> str:
        msg_content = data.get("data", {}).get("message", {})

        # Captura ID de Listas
        list_id = msg_content.get("listResponseMessage", {}).get("singleSelectReply", {}).get("selectedRowId")
        if list_id: return list_id

        # Captura ID de Botões
        btn_id = msg_content.get("buttonsResponseMessage", {}).get("selectedButtonId")
        if btn_id: return btn_id

        return msg_content.get("conversation") or \
            msg_content.get("extendedTextMessage", {}).get("text") or ""

    def _extract_remote_jid(self, data: dict) -> str:
        try:
            return data.get("data", {}).get("key", {}).get("remoteJidAlt", "")
        except:
            return ""

    def _extract_message_id(self, data: dict) -> str:
        return data.get("data", {}).get("key", {}).get("id")