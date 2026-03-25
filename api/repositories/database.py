import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Configuração da URL (usando a variável de ambiente do Docker ou local)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:senha123@postgres:5432/evolution")

# 2. Criação do Engine
engine = create_engine(DATABASE_URL, echo=False)

# 3. Fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Definição do Base (DEVE ser definido aqui para que o models.py o importe)
Base = declarative_base()

def reset_database():
    # Importamos os modelos aqui dentro APENAS para o SQLAlchemy
    # 'registrar' as classes antes de criar as tabelas.
    from . import models
    print("Resetando banco de dados...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)