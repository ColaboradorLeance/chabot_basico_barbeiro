from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    state = Column(String)  # MENU, DATA, HORA...
    last_message = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    data = relationship("ConversationData", back_populates="conversation")


class ConversationData(Base):
    __tablename__ = "conversation_data"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    key = Column(String)
    value = Column(Text)

    conversation = relationship("Conversation", back_populates="data")

class ProcessedMessage(Base):
    __tablename__ = "processed_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"))
    data = Column(String)
    hora = Column(String)
    servico = Column(String)
    cliente_phone = Column(String)  # Certifique-se que este nome é o usado nos filtros

    # Dica: Adicione o relacionamento para facilitar buscas futuras
    barber = relationship("Barber", backref="appointments")

class Barber(Base):
    __tablename__ = "barbers"

    id = Column(Integer, primary_key=True)
    nome = Column(String)

    schedules = relationship("Schedule", back_populates="barber")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    barber_id = Column(Integer, ForeignKey("barbers.id"))
    day = Column(String, nullable=False)       # ex: "2026-03-25"
    time_slot = Column(String, nullable=False) # ex: "08:00", "08:30", "09:00"
    is_booked = Column(Integer, default=0)     # 0 = disponível, 1 = reservado

    barber = relationship("Barber", back_populates="schedules")