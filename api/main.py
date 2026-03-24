from routes.webhook_routes import router as webhook_router
from fastapi import FastAPI
from repositories.database import engine, Base, reset_database
app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
reset_database()
app.include_router(webhook_router)
