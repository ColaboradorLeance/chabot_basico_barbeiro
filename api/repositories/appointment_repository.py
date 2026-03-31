import json
import random
import pytz
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User, Conversation, ConversationData, ProcessedMessage, Appointment, Barber


class AppointmentRepository:
    _user_processing = {}

    def __init__(self):
        self.db: Session = SessionLocal()
        # Define o fuso horário de São Paulo centralizado para toda a classe
        self.tz = pytz.timezone("America/Sao_Paulo")

    def _get_now(self):
        """Retorna o datetime atual no fuso horário de São Paulo."""
        return datetime.now(self.tz)

    def _is_today(self, day: str) -> bool:
        try:
            return datetime.strptime(day, "%Y-%m-%d").date() == self._get_now().date()
        except:
            return False

    def _is_future_time(self, day: str, hour: str, min_minutes: int = 0) -> bool:
        """Verifica se o horário agendado é no futuro em relação ao horário de São Paulo."""
        try:
            dt_naive = datetime.strptime(f"{day} {hour}", "%Y-%m-%d %H:%M")
            dt_aware = self.tz.localize(dt_naive)
            limite = self._get_now() + timedelta(minutes=min_minutes)
            return dt_aware > limite
        except Exception as e:
            print(f"Erro na validação de horário: {e}")
            return False

    def close(self):
        if self.db:
            self.db.close()

    def get_available_days(self, num_days=6):
        hoje = self._get_now().date()
        dias = []
        for i in range(num_days):
            dia = hoje + timedelta(days=i)
            dias.append(dia.strftime("%Y-%m-%d"))
        return dias

    def set_user_processing(self, phone: str, status: bool):
        if status:
            AppointmentRepository._user_processing[phone] = True
        else:
            AppointmentRepository._user_processing.pop(phone, None)

    def is_user_processing(self, phone: str) -> bool:
        return AppointmentRepository._user_processing.get(phone, False)

    # --- ESTADO DO USUÁRIO ---
    def get_user_state(self, phone: str):
        user = self.db.query(User).filter(User.phone == phone).first()
        if not user:
            return "START", {}

        conversation = self.db.query(Conversation).filter(Conversation.user_id == user.id).first()
        if not conversation:
            return "START", {}

        extra_data = {}
        for item in conversation.data:
            try:
                extra_data[item.key] = json.loads(item.value)
            except (json.JSONDecodeError, TypeError):
                extra_data[item.key] = item.value

        return conversation.state, {"extra": extra_data}

    def save(self, data: dict):
        try:
            user = self.db.query(User).filter(User.phone == data["phone"]).first()
            if not user:
                user = User(phone=data["phone"], name=data.get("name", "Cliente"))
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)

            conversation = self.db.query(Conversation).filter(Conversation.user_id == user.id).first()
            if not conversation:
                conversation = Conversation(
                    user_id=user.id,
                    state=data.get("state", "START"),
                    last_message=data.get("last_message")
                )
                self.db.add(conversation)
            else:
                conversation.state = data.get("state", conversation.state)
                conversation.last_message = data.get("last_message")
            self.db.commit()
            self.db.refresh(conversation)

            extra_data = data.get("extra", {})
            for key, value in extra_data.items():
                json_value = json.dumps(value)
                item = self.db.query(ConversationData).filter(
                    ConversationData.conversation_id == conversation.id,
                    ConversationData.key == key
                ).first()
                if item:
                    item.value = json_value
                else:
                    item = ConversationData(conversation_id=conversation.id, key=key, value=json_value)
                    self.db.add(item)
            self.db.commit()

            return {"user_id": user.id, "conversation_id": conversation.id}

        except Exception as e:
            self.db.rollback()
            print("Erro ao salvar:", e)
            raise e

    # --- MENSAGENS PROCESSADAS ---
    def message_already_processed(self, message_id: str) -> bool:
        exists = self.db.query(ProcessedMessage).filter(
            ProcessedMessage.message_id == message_id
        ).first()
        return exists is not None

    def save_message_id(self, message_id: str):
        try:
            msg = ProcessedMessage(message_id=message_id)
            self.db.add(msg)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"⚠️ Erro ao salvar message_id (provável duplicado): {message_id}")

    # --- AGENDAMENTOS ---
    def get_appointments(self, phone: str):
        return self.db.query(Appointment).filter(
            Appointment.cliente_phone == phone
        ).order_by(Appointment.data, Appointment.hora).all()

    def create_appointment(self, barber_id: int, data: str, hora: str, servico: str, phone: str):
        try:
            agendamento = Appointment(
                barber_id=barber_id,
                data=data,
                hora=hora,
                servico=servico,
                cliente_phone=phone
            )
            self.db.add(agendamento)
            self.db.commit()
            self.db.refresh(agendamento)
            return agendamento
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao salvar agendamento: {e}")
            return None

    def delete_appointment(self, appointment_id: int):
        agendamento = self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not agendamento:
            return False
        try:
            self.db.delete(agendamento)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao deletar agendamento: {e}")
            return False

    def has_available_slots(self, day: str, barber_id: int = None) -> bool:
        all_slots = [f"{h:02d}:00" for h in range(8, 19)]

        valid_slots = [h for h in all_slots if self._is_future_time(day, h)]
        if not valid_slots:
            return False

        query = self.db.query(Barber)
        if barber_id:
            query = query.filter(Barber.id == barber_id)

        barbeiros = query.all()
        for barber in barbeiros:
            ocupados = self.db.query(Appointment).filter(
                Appointment.barber_id == barber.id,
                Appointment.data == day
            ).all()
            ocupados_horas = [a.hora for a in ocupados]
            if any(slot not in ocupados_horas for slot in valid_slots):
                return True
        return False

    def get_all_barbers(self):
        return self.db.query(Barber).order_by(Barber.id.asc()).all()

    def get_available_hours(self, day: str, barber_id: int) -> list:
        all_slots = [f"{h:02d}:00" for h in range(8, 19)]
        ocupados = self.db.query(Appointment).filter(
            Appointment.barber_id == barber_id,
            Appointment.data == day
        ).all()
        ocupados_horas = [a.hora for a in ocupados]

        livres = [slot for slot in all_slots if slot not in ocupados_horas]
        # Aplica a validação de horário futuro com o timezone correto
        livres = [h for h in livres if self._is_future_time(day, h)]
        return livres

    def has_available_slots_any_barber(self, day: str) -> bool:
        all_slots = [f"{h:02d}:00" for h in range(8, 19)]
        valid_slots = [h for h in all_slots if self._is_future_time(day, h)]
        if not valid_slots:
            return False

        barbeiros = self.get_all_barbers()
        for barber in barbeiros:
            ocupados = self.db.query(Appointment).filter(
                Appointment.barber_id == barber.id,
                Appointment.data == day
            ).all()
            ocupados_horas = [a.hora for a in ocupados]
            if any(slot not in ocupados_horas for slot in valid_slots):
                return True
        return False

    def get_available_hours_any_barber(self, day: str) -> list:
        all_slots = [f"{h:02d}:00" for h in range(8, 19)]
        horarios_disponiveis = []
        for slot in all_slots:
            barbeiros = self.get_all_barbers()
            for barber in barbeiros:
                ocupado = self.db.query(Appointment).filter(
                    Appointment.barber_id == barber.id,
                    Appointment.data == day,
                    Appointment.hora == slot
                ).first()
                if not ocupado:
                    horarios_disponiveis.append(slot)
                    break

        horarios_disponiveis = [
            h for h in horarios_disponiveis
            if self._is_future_time(day, h)
        ]

        return horarios_disponiveis

    def get_random_available_barber(self, day: str, hour: str):
        barbeiros = self.get_all_barbers()
        disponiveis = []

        for barber in barbeiros:
            ocupado = self.db.query(Appointment).filter(
                Appointment.barber_id == barber.id,
                Appointment.data == day,
                Appointment.hora == hour
            ).first()

            if not ocupado:
                disponiveis.append(barber)

        if not disponiveis:
            return None

        return random.choice(disponiveis)