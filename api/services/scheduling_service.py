import asyncio
from zoneinfo import ZoneInfo
import json
import re
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

        # 1. Abre a conexão
        repo = AppointmentRepository()

        try:  # Tudo dentro do try para garantir que o close() será chamado
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
                        return {
                            "next_state": "VISUALIZACAO_AGENDAMENTO",
                            "extra": {
                                **extra,
                                "agendamentos": [a.id for a in agendamentos]
                            }
                        }
                else:
                    await whatsapp_service.send_text(phone, ALERTA)
                    return {"next_state": "SERVICE"}

            elif current_state == "VISUALIZACAO_AGENDAMENTO":

                if mensagem == "0":
                    await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                    return {"next_state": "SERVICE", "extra": {}}

                agendamentos_ids = extra.get("agendamentos", [])

                try:
                    index = int(mensagem) - 1

                    if 0 <= index < len(agendamentos_ids):
                        appointment_id = agendamentos_ids[index]

                        sucesso = repo.delete_appointment(appointment_id)

                        if sucesso:
                            await whatsapp_service.send_text(phone, "✅ Agendamento cancelado com sucesso!")
                        else:
                            await whatsapp_service.send_text(phone, "❌ Erro ao cancelar agendamento.")

                        await whatsapp_service.send_text(phone, MSG_OPTION_SERVICE)
                        return {"next_state": "SERVICE", "extra": {}}

                except:
                    pass

                await whatsapp_service.send_text(phone, "⚠️ Opção inválida.")
                return {"next_state": "VISUALIZACAO_AGENDAMENTO", "extra": extra}

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
                        menu_hours, available_hours = self.build_available_hours_menu(data_escolhida,
                                                                                      extra["id_barber"])

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

                        # Formata a data para DD/MM/YYYY
                        try:
                            data_formatada = datetime.strptime(extra.get('chosen_day'), "%Y-%m-%d").strftime("%d/%m/%Y")
                        except:
                            data_formatada = extra.get('chosen_day')

                        resumo = (
                            f"📝 *Resumo do Agendamento*\n\n"
                            f"✂️ Serviço: {extra.get('servico_nome')}\n"
                            f"👤 Barbeiro: {extra.get('barber_name')}\n"
                            f"📅 Data: {data_formatada}\n"
                            f"⏰ Hora: {hora_escolhida}\n\n"
                            "Para finalizar, digite seu *Email*:"
                        )
                        await whatsapp_service.send_text(phone, resumo)
                        return {"next_state": "CONFIRM_EMAIL", "extra": extra}
                except:
                    pass
                return {"next_state": "CHOOSE_HOUR", "extra": extra}

            elif current_state == "CONFIRM_EMAIL":
                email = mensagem.strip()

                if extra.get("email_digitado"):
                    if msg in ["1", "sim", "s"]:
                        return await self.process_flow(
                            mensagem=extra.get("email_digitado"),
                            current_state="FINALIZE",
                            phone=phone,
                            context_data={"extra": extra}
                        )
                    elif msg in ["2", "não", "nao", "n"]:
                        await whatsapp_service.send_text(phone, "✏️ Ok! Digite novamente seu email:")
                        extra.pop("email_digitado", None)
                        return {"next_state": "CONFIRM_EMAIL", "extra": extra}
                    else:
                        await whatsapp_service.send_text(
                            phone,
                            "⚠️ Resposta inválida.\n\n1️⃣ Sim\n2️⃣ Não"
                        )
                        return {"next_state": "CONFIRM_EMAIL", "extra": extra}

                regex_email = r"^[\w\.-]+@[\w\.-]+\.\w+$"
                if not re.match(regex_email, email):
                    await whatsapp_service.send_text(
                        phone,
                        "❌ Email inválido.\n\nPor favor, digite um email válido:"
                    )
                    return {"next_state": "CONFIRM_EMAIL", "extra": extra}

                # Salva e pede confirmação
                extra["email_digitado"] = email

                await whatsapp_service.send_text(
                    phone,
                    f"📧 Você digitou: *{email}*\n\nEstá correto?\n\n1️⃣ Sim\n2️⃣ Não"
                )

                return {"next_state": "CONFIRM_EMAIL", "extra": extra}

            elif current_state == "FINALIZE":
                email_cliente = extra.get("email_digitado")
                data_escolhida = extra.get('chosen_day')
                hora_escolhida = extra.get('chosen_hour')
                servico = extra.get('servico_nome', 'Serviço')
                barbeiro = extra.get('barber_name', 'Barbeiro')

                await whatsapp_service.send_text(phone, "⏳ Gerando seu convite na agenda, um momento...")

                try:
                    # Importação LOCAL para não derrubar o app no boot
                    from .schedule_event import GoogleCalendarService
                    calendar = GoogleCalendarService()

                    start_dt = datetime.strptime(f"{data_escolhida} {hora_escolhida}", "%Y-%m-%d %H:%M")
                    data_formatada = start_dt.strftime("%d/%m/%Y")
                    hora_formatada = start_dt.strftime("%H:%M")
                    end_dt = start_dt + timedelta(hours=1)
                    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:00-03:00")
                    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:00-03:00")

                    link_invite = await asyncio.to_thread(
                        calendar.create_event,
                        nameEvent=f"Corte: {servico} com {barbeiro}",
                        descriptionEvent=f"Agendamento confirmado para {servico}.",
                        startDateTimeEvent=start_iso,
                        endDateTimeEvent=end_iso,
                        destinateEmail=email_cliente
                    )

                    await whatsapp_service.send_text(
                        phone,
                        f"✅ *Agendamento Confirmado!*\n\n"
                        f"✂️ Serviço: {servico}\n"
                        f"👤 Barbeiro: {barbeiro}\n"
                        f"📅 Data: {data_formatada}\n"
                        f"⏰ Hora: {hora_formatada}\n\n"
                        f"📧 Convite enviado para: {email_cliente}\n\n"
                        "O cliente receberá o convite no email informado e poderá adicioná-lo ao próprio calendário. Até logo! 💈"
                    )
                    repo.create_appointment(
                        barber_id=extra.get("id_barber"),
                        data=data_escolhida,
                        hora=hora_escolhida,
                        servico=servico,
                        phone=phone
                    )
                    return {"next_state": "START", "extra": {}}

                except Exception as e:
                    print(f"❌ ERRO CALENDAR: {str(e)}")
                    await whatsapp_service.send_text(phone, "⚠️ Reservado! Mas tive um erro ao gerar o link da agenda.")
                    return {"next_state": "START", "extra": {}}

            return {"next_state": current_state, "extra": extra}

        finally:
            # 🛑 FECHA A CONEXÃO PRINCIPAL AQUI
            repo.close()

    def build_available_days_menu(self, id_barber: int):
        repo = AppointmentRepository()
        try:
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
        finally:
            repo.close()  # 🛑 FECHA CONEXÃO SECUNDÁRIA

    def build_available_hours_menu(self, day_str: str, id_barber: int):
        repo = AppointmentRepository()
        try:
            vagos = repo.get_available_hours(day_str, id_barber)

            try:
                data_formatada = datetime.strptime(day_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                data_formatada = day_str

            menu = f"⏰ Horários para {data_formatada}:\n\n"

            def number_to_emoji(n):
                emoji_map = {
                    0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣",
                    5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣",
                    10: "🔟", 11: "1️⃣1️⃣"
                }
                return emoji_map.get(n, str(n))

            for i, hora in enumerate(vagos, 1):
                menu += f"{number_to_emoji(i)} {hora}\n"

            menu += "\n🔙 Digite 0️⃣ para voltar."
            return menu, vagos
        finally:
            repo.close()  # 🛑 FECHA CONEXÃO SECUNDÁRIA

    async def send_barber_menu(self):
        repo = AppointmentRepository()
        try:
            barbers = repo.get_all_barbers()
            menu = "✂️ Escolha o barbeiro:\n\n"
            for i, b in enumerate(barbers, 1):
                menu += f"{i}️⃣ {b.nome}\n"
            menu += "\n🔙 Digite 0️⃣ para voltar."
            return menu
        finally:
            repo.close()

    def build_cancel_menu(self, agendamentos):
        if not agendamentos:
            return "❌ Nenhum agendamento encontrado."
        menu = "📅 *Seus agendamentos:*\n\n"
        for i, ag in enumerate(agendamentos, 1):
            try:
                data_formatada = datetime.strptime(ag.data, "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                data_formatada = ag.data
            menu += (
                f"{i}️⃣ {ag.servico}\n"
                f"👤 Barbeiro ID: {ag.barber_id}\n"
                f"📅 {data_formatada} às {ag.hora}\n\n"
            )
        menu += "Digite o número para cancelar ou 0️⃣ para voltar."
        return menu