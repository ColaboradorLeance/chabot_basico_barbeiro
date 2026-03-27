from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User, Conversation, ConversationData, ProcessedMessage, Appointment, Barber
import json

class AppointmentRepository:
    def __init__(self):
        self.db: Session = SessionLocal()

    def get_user_state(self, phone: str):
        try:
            user = self.db.query(User).filter(User.phone == phone).first()
            if not user:
                return "START", {}

            conversation = self.db.query(Conversation).filter(Conversation.user_id == user.id).first()
            if not conversation:
                return "START", {}


            extra_data = {}
            for item in conversation.data:
                try:
                    # Tenta converter de JSON para objeto Python (Lista, Dict, Int...)
                    extra_data[item.key] = json.loads(item.value)
                except (json.JSONDecodeError, TypeError):
                    # Se falhar (ex: dados antigos), mantém o valor original
                    extra_data[item.key] = item.value

            # Retorna no formato esperado pelo seu SchedulingService: {"extra": {...}}
            return conversation.state, {"extra": extra_data}
        finally:
            self.db.close()

    def save(self, data: dict):
        print("Salvando no banco:", data)
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

                # A CORREÇÃO ESTÁ AQUI: Usa json.dumps para garantir aspas duplas e formatação correta
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
        finally:
            self.db.close()

    def message_already_processed(self, message_id: str) -> bool:
        try:
            exists = self.db.query(ProcessedMessage).filter(
                ProcessedMessage.message_id == message_id
            ).first()
            return exists is not None
        finally:
            self.db.close()

    def save_message_id(self, message_id: str):
        try:
            msg = ProcessedMessage(message_id=message_id)
            self.db.add(msg)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Se cair aqui, provavelmente já existe (concorrência)
            print(f"⚠️ Erro ao salvar message_id (provável duplicado): {message_id}")
        finally:
            self.db.close()

    def _refresh_session(self):
        if not self.db.is_active:
            self.db = SessionLocal()

    def get_appointments(self, phone: str):
        try:
            # Correção: O modelo Appointment usa cliente_phone, não user_id
            agendamentos = self.db.query(Appointment).filter(
                Appointment.cliente_phone == phone
            ).order_by(Appointment.data, Appointment.hora).all()
            return agendamentos
        finally:
            self.db.close()

    def has_available_slots(self, day: str, barber_id: int = None) -> bool:
        try:
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
                vagos = [s for s in all_slots if s not in ocupados_horas]

                if any(slot not in ocupados_horas for slot in all_slots):
                    return True

            return False
        finally:
            # CUIDADO: Se você fechar a sessão aqui, o repository pode parar de funcionar
            # em outras chamadas. Geralmente quem fecha a sessão é o Controller ou o Middleware.
            pass

    def get_all_barbers(self):
        return self.db.query(Barber).order_by(Barber.id.asc()).all()

    def get_available_hours(self, day: str, barber_id: int) -> list:
        try:
            all_slots = [f"{h:02d}:00" for h in range(8, 19)]

            # Filtra os agendamentos já existentes
            ocupados = self.db.query(Appointment).filter(
                Appointment.barber_id == barber_id,
                Appointment.data == day
            ).all()

            ocupados_horas = [a.hora for a in ocupados]

            # Retorna a lista de horas que NÃO estão ocupadas
            vagos = [slot for slot in all_slots if slot not in ocupados_horas]
            return vagos
        finally:
            pass




