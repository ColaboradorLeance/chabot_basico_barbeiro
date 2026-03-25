from token import AWAIT
from datetime import datetime, timedelta
from services.whatsapp_service import WhatsAppService
import asyncio
from repositories.appointment_repository import AppointmentRepository
from core.messages import MSG_START, MSG_OPTION_SERVICE, MSG_SERVICE, ALERTA, MSG_BUSCANDO_AGENDAMENTO, MENSAGEM_AGENDAMENTO_NOT_FOUND, MSG_MEUS_AGENDAMENTOS



class SchedulingService:
    async def process_flow(self, mensagem: str, current_state: str, phone: str, context_data: str) -> dict:
        msg = mensagem.strip().lower()
        whatsapp_service = WhatsAppService()

        if current_state == "START":
            await whatsapp_service.send_media(phone)
            await whatsapp_service.send_text(phone, MSG_START)
            await asyncio.sleep(1)
            await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
            return {"next_state": "SERVICE"}

        elif current_state == "SERVICE":
            if mensagem == "1":
                await whatsapp_service.send_text(phone, MSG_SERVICE)
                return {"next_state": "CHOOSE_BARBEIRO"}
            elif mensagem == "2":
                await whatsapp_service.send_text(phone, MSG_BUSCANDO_AGENDAMENTO)
                await asyncio.sleep(1)
                repo = AppointmentRepository()
                agendamentos = repo.get_appointments(phone)
                if not agendamentos:
                    await whatsapp_service.send_text(phone, MENSAGEM_AGENDAMENTO_NOT_FOUND)
                    await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                    return {"next_state": "SERVICE"}
                else:
                    msg_agendamentos = ""
                    for ag in agendamentos:
                        msg_agendamentos += f"✂️ {ag.servico} - {ag.data} às {ag.hora}\n"

                    msg_agendados = self.build_cancel_menu(agendamentos)
                    await whatsapp_service.send_text(phone, MSG_BUSCANDO_AGENDAMENTO, msg_agendamentos)
                    await whatsapp_service.send_text(phone, msg_agendados)
                    return {"next_state": "VISUALIZACAO_AGENDAMENTO"}
            else:
                await whatsapp_service.send_text(phone, ALERTA)
                await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                return {"next_state": "SERVICE"}

        elif current_state == "VISUALIZACAO_AGENDAMENTO":
            pass
        elif current_state == "CHOOSE_BARBEIRO":
            if mensagem == "0":
                await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                return {"next_state": "SERVICE"}
            menu_barber = await self.send_barber_menu()
            await whatsapp_service.send_text(phone, menu_barber)
            return {"next_state": "CHOOSE_DAY"}

        elif current_state == "CHOOSE_DAY":
            if mensagem == "0":
                menu_barber = await self.send_barber_menu()
                await whatsapp_service.send_text(phone, menu_barber)
                return {"next_state": "CHOOSE_BARBEIRO"}
            menu_days, avaliable_days = self.build_available_days_menu()
            await whatsapp_service.send_text(phone, menu_days)
            return {"next_state": "CHOOSE_HOUR"}

        elif current_state == "CHOOSE_HOUR":
            if mensagem == "0":
                menu_days, avaliable_days = self.build_available_days_menu()
                await whatsapp_service.send_text(phone, menu_days)
            await whatsapp_service.send_text(phone, "vai corinthians")



    def build_cancel_menu(self, agendamentos: list) -> str:
        menu = "❌ Escolha o agendamento que deseja cancelar:\n\n"
        for i, ag in enumerate(agendamentos, 1):
            menu += f"{i}️⃣ {ag.servico} - {ag.data} às {ag.hora}\n"

        menu += "\n🔙 Digite 0️⃣ para voltar ao menu principal."
        return menu

    def build_available_days_menu(self, days_ahead: int = 7):
        repo = AppointmentRepository()
        menu = "📅 Escolha o dia do seu corte:\n\n"
        today = datetime.today()
        option_number = 1
        available_days = []

        for i in range(days_ahead):
            day = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            if repo.has_available_slots(day):
                display_day = (today + timedelta(days=i)).strftime("%d/%m/%Y")
                menu += f"{option_number}️⃣ {display_day}\n"
                available_days.append(day)
                option_number += 1

        menu += "\n🔙 Digite 0️⃣ para voltar ao menu principal."
        return menu, available_days

    async def send_barber_menu(self):
        repo = AppointmentRepository()
        barbers = repo.get_all_barbers()
        menu = "✂️ Escolha o barbeiro:\n\n"
        for i, barber in enumerate(barbers, 1):
            menu += f"{i}️⃣ {barber.nome}\n"
        menu += "\n🔙 Digite 0️⃣ para voltar ao menu principal."
        return menu