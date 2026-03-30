# repositories/appointment_repository.py
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User, Conversation, ConversationData, ProcessedMessage, Appointment, Barber
import json

class AppointmentRepository:
    _user_processing = {}
    def __init__(self):
        self.db: Session = SessionLocal()

    def close(self):
        if self.db:
            self.db.close()

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
        query = self.db.query(Barber)
        if barber_id:
            query = query.filter(Barber.id == barber_id)
        barbeiros = query.all()
        if not barbeiros:
            return False
        for barber in barbeiros:
            ocupados = self.db.query(Appointment).filter(
                Appointment.barber_id == barber.id,
                Appointment.data == day
            ).all()
            ocupados_horas = [a.hora for a in ocupados]
            if any(slot not in ocupados_horas for slot in all_slots):
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
        return [slot for slot in all_slots if slot not in ocupados_horas]