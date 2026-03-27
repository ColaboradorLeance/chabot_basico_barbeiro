import asyncio
import json
from datetime import datetime, timedelta
from services.whatsapp_service import WhatsAppService
from repositories.appointment_repository import AppointmentRepository
from core.messages import (
    MSG_START, MSG_OPTION_SERVICE, MSG_SERVICE, ALERTA,
    MSG_BUSCANDO_AGENDAMENTO, MENSAGEM_AGENDAMENTO_NOT_FOUND
)

class SchedulingService:
    async def process_flow(self, mensagem: str, current_state: str, phone: str, context_data: dict) -> dict:
        msg = mensagem.strip().lower()
        whatsapp_service = WhatsAppService()
        repo = AppointmentRepository()

        # Tratamento de segurança para o extra
        extra = context_data.get('extra', {})
        if isinstance(extra, str) and extra.strip():
            try:
                extra = json.loads(extra)
            except:
                extra = {}
        if extra is None: extra = {}

        # --- ESTADO INICIAL ---
        if current_state == "START":
            await whatsapp_service.send_media(phone)
            await whatsapp_service.send_text(phone, MSG_START)
            await asyncio.sleep(1)
            await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
            return {"next_state": "SERVICE"}

        # --- MENU PRINCIPAL ---
        elif current_state == "SERVICE":
            if mensagem == "1":
                await whatsapp_service.send_text(phone, MSG_SERVICE)
                return {"next_state": "CHOOSE_SERVICE", "extra": extra}
            elif mensagem == "2":
                await whatsapp_service.send_text(phone, MSG_BUSCANDO_AGENDAMENTO)
                agendamentos = repo.get_appointments(phone)
                if not agendamentos:
                    await whatsapp_service.send_text(phone, MENSAGEM_AGENDAMENTO_NOT_FOUND)
                    await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                    return {"next_state": "SERVICE"}
                else:
                    msg_agendados = self.build_cancel_menu(agendamentos)
                    await whatsapp_service.send_text(phone, msg_agendados)
                    return {"next_state": "VISUALIZACAO_AGENDAMENTO"}
            else:
                await whatsapp_service.send_text(phone, ALERTA)
                return {"next_state": "SERVICE"}

        # --- ESCOLHA DO SERVIÇO ---
        elif current_state == "CHOOSE_SERVICE":
            if mensagem == "0":
                await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                return {"next_state": "SERVICE"}

            servicos = {"1": "Corte", "2": "Barba", "3": "Depilação", "4": "Luzes"}
            extra["servico_nome"] = servicos.get(mensagem, "Corte")

            menu_barber = await self.send_barber_menu()
            await whatsapp_service.send_text(phone, menu_barber)
            return {"next_state": "CHOOSE_BARBEIRO", "extra": extra}

        # --- ESCOLHA DO BARBEIRO ---
        elif current_state == "CHOOSE_BARBEIRO":
            if mensagem == "0":
                await whatsapp_service.send_text(phone, MSG_SERVICE)
                return {"next_state": "CHOOSE_SERVICE"}

            barbeiros = repo.get_all_barbers()
            try:
                index = int(mensagem) - 1
                if 0 <= index < len(barbeiros):
                    barbeiro = barbeiros[index]
                    menu_days, available_days = self.build_available_days_menu(barbeiro.id)

                    extra["id_barber"] = barbeiro.id
                    extra["barber_name"] = barbeiro.nome
                    extra["available_days"] = available_days

                    await whatsapp_service.send_text(phone, menu_days)
                    return {"next_state": "CHOOSE_DAY", "extra": extra}
            except:
                pass
            return {"next_state": "CHOOSE_BARBEIRO"}

        # --- ESCOLHA DO DIA ---
        elif current_state == "CHOOSE_DAY":
            if mensagem == "0":
                menu_barber = await self.send_barber_menu()
                await whatsapp_service.send_text(phone, menu_barber)
                return {"next_state": "CHOOSE_BARBEIRO"}

            available_days = extra.get('available_days', [])
            try:
                index = int(mensagem) - 1
                if 0 <= index < len(available_days):
                    data_escolhida = available_days[index]
                    menu_hours, available_hours = self.build_available_hours_menu(data_escolhida, extra["id_barber"])

                    extra["chosen_day"] = data_escolhida
                    extra["available_hours"] = available_hours

                    await whatsapp_service.send_text(phone, menu_hours)
                    return {"next_state": "CHOOSE_HOUR", "extra": extra}
            except:
                pass
            return {"next_state": "CHOOSE_DAY", "extra": extra}

        # --- ESCOLHA DA HORA ---
        elif current_state == "CHOOSE_HOUR":
            if mensagem == "0":
                menu_days, _ = self.build_available_days_menu(extra["id_barber"])
                await whatsapp_service.send_text(phone, menu_days)
                return {"next_state": "CHOOSE_DAY", "extra": extra}

            available_hours = extra.get('available_hours', [])
            try:
                index = int(mensagem) - 1
                if 0 <= index < len(available_hours):
                    hora_escolhida = available_hours[index]
                    extra["chosen_hour"] = hora_escolhida

                    resumo = (
                        f"📝 *Resumo do Agendamento*\n\n"
                        f"✂️ Serviço: {extra.get('servico_nome')}\n"
                        f"👤 Barbeiro: {extra.get('barber_name')}\n"
                        f"📅 Data: {extra.get('chosen_day')}\n"
                        f"⏰ Hora: {hora_escolhida}\n\n"
                        "Para finalizar, digite seu *Email*:"
                    )
                    await whatsapp_service.send_text(phone, resumo)
                    return {"next_state": "FINALIZE", "extra": extra}
            except:
                pass
            return {"next_state": "CHOOSE_HOUR", "extra": extra}

        # --- FINALIZAÇÃO E INTEGRAÇÃO GOOGLE CALENDAR ---
        elif current_state == "FINALIZE":
            email_cliente = mensagem.strip()
            data_escolhida = extra.get('chosen_day')
            hora_escolhida = extra.get('chosen_hour')
            servico = extra.get('servico_nome', 'Serviço')
            barbeiro = extra.get('barber_name', 'Barbeiro')

            await whatsapp_service.send_text(phone, "⏳ Gerando seu convite na agenda, um momento...")

            try:
                # 1. Importação LOCAL para não derrubar o app no boot
                from .schedule_event import GoogleCalendarService
                calendar = GoogleCalendarService()

                # 2. Formatação de Datas
                start_dt = datetime.strptime(f"{data_escolhida} {hora_escolhida}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(hours=1)
                start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:00-03:00")
                end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:00-03:00")

                # 3. Chamada Não-Bloqueante
                link_invite = await asyncio.to_thread(
                    calendar.create_event,
                    nameEvent=f"Corte: {servico} com {barbeiro}",
                    descriptionEvent=f"Agendamento confirmado para {servico}.",
                    startDateTimeEvent=start_iso,
                    endDateTimeEvent=end_iso,
                    destinateEmail=email_cliente
                )

                await whatsapp_service.send_text(phone,
                    f"✅ *Agendamento Confirmado!*\n\n"
                    f"Convite enviado para: {email_cliente}\n"
                    f"📅 Link:\n{link_invite}\n\nAté logo! 💈"
                )
                return {"next_state": "START", "extra": {}}

            except Exception as e:
                print(f"❌ ERRO CALENDAR: {str(e)}")
                await whatsapp_service.send_text(phone, "⚠️ Reservado! Mas tive um erro ao gerar o link da agenda.")
                return {"next_state": "START", "extra": {}}

        return {"next_state": current_state, "extra": extra}

    # --- MÉTODOS AUXILIARES ---
    def build_available_days_menu(self, id_barber: int):
        repo = AppointmentRepository()
        menu = "📅 Escolha o dia do seu corte:\n\n"
        today = datetime.today()
        available_days = []
        option = 1
        for i in range(7):
            current_date = today + timedelta(days=i)
            day_str = current_date.strftime("%Y-%m-%d")
            if repo.has_available_slots(day_str, id_barber):
                menu += f"{option}️⃣ {current_date.strftime('%d/%m (%A)')}\n"
                available_days.append(day_str)
                option += 1
        menu += "\n🔙 Digite 0️⃣ para voltar."
        return menu, available_days

    def build_available_hours_menu(self, day_str: str, id_barber: int):
        repo = AppointmentRepository()
        vagos = repo.get_available_hours(day_str, id_barber)
        menu = f"⏰ Horários para {day_str}:\n\n"
        for i, hora in enumerate(vagos, 1):
            menu += f"{i}️⃣ {hora}\n"
        menu += "\n🔙 Digite 0️⃣ para voltar."
        return menu, vagos

    async def send_barber_menu(self):
        repo = AppointmentRepository()
        barbers = repo.get_all_barbers()
        menu = "✂️ Escolha o barbeiro:\n\n"
        for i, b in enumerate(barbers, 1):
            menu += f"{i}️⃣ {b.nome}\n"
        menu += "\n🔙 Digite 0️⃣ para voltar."
        return menu