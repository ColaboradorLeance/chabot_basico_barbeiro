# database.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:senha123@postgres:5432/evolution")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def reset_database():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS conversation_data CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados resetado e limpo com sucesso!")