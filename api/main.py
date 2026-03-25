from routes.webhook_routes import router as webhook_router
from fastapi import FastAPI
from repositories.database import engine, Base, reset_database
from repositories.database import SessionLocal
from repositories.models import Barber
app = FastAPI()



@app.on_event("startup")
def startup():
    reset_database()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    barbers = ["Barbeiro João", "Barbeiro Pedro", "Barbeiro Lucas", "Barbeiro Rafael"]
    for nome in barbers:
        barber = Barber(nome=nome)
        db.add(barber)
    db.commit()
    db.close()


# 4️⃣ Inclui as rotas
app.include_router(webhook_router)