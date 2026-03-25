from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User, Conversation, ConversationData, ProcessedMessage, Appointment, Barber

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

            # Recupera os dados extras já salvos (ex: serviço escolhido, data)
            extra_data = {item.key: item.value for item in conversation.data}
            return conversation.state, extra_data
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
                item = self.db.query(ConversationData).filter(
                    ConversationData.conversation_id == conversation.id,
                    ConversationData.key == key
                ).first()
                if item:
                    item.value = str(value)
                else:
                    item = ConversationData(conversation_id=conversation.id, key=key, value=str(value))
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

    def has_available_slots(self, day: str) -> bool:
        try:
            all_slots = [f"{h:02d}:00" for h in range(8, 19)]
            barbeiros = self.db.query(Barber).all()

            print(f"DEBUG: Barbeiros encontrados no banco: {len(barbeiros)}")  # Adicione isso

            if not barbeiros:
                return False

            for barber in barbeiros:
                ocupados = self.db.query(Appointment).filter(
                    Appointment.barber_id == barber.id,
                    Appointment.data == day
                ).all()
                ocupados_horas = [a.hora for a in ocupados]

                # Se houver qualquer slot livre para qualquer barbeiro, retorna True
                if any(slot not in ocupados_horas for slot in all_slots):
                    return True
            return False
        finally:
            self.db.close()

    def get_all_barbers(self):
        """Busca todos os barbeiros cadastrados no banco."""
        return self.db.query(Barber).all()