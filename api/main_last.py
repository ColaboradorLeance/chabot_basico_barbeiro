from fastapi import FastAPI, Request
import requests

app = FastAPI()

# AJUSTADO PARA O SEU DOCKER-COMPOSE
EVOLUTION_URL = "http://evolution_api:8080"  # Nome do serviço no compose
API_KEY = "1234"  # Igual ao seu docker-compose
INSTANCE_NAME = "meubot"


def enviar_texto(numero, texto):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
    payload = {
        "number": numero,
        "text": texto
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def home():
    return {"status": "online"}


@app.post("/webhook") # <--- Sem o "/messages-upsert" aqui
async def receber_dados(request: Request):
    print("Chegou algo no webhook!")
    dados = await request.json()
    print(dados)
    return {"status": "recebido"} # <--- O return que evita o 'None'


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
