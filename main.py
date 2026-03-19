from fastapi import FastAPI, Request
import requests
import json

app = FastAPI()

# CONFIGURAÇÕES DA SUA INSTÂNCIA
EVOLUTION_URL = "http://localhost:8080"
API_KEY = "sua_chave_super_secreta_123"
INSTANCE_NAME = "meubot "


def enviar_texto(numero, texto):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
    payload = {
        "number": numero,
        "text": texto
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

@app.post("/webhook")
async def receber_dados(request: Request):
    print("Chegou algo")
    dados = await request.json()
    print(dados)
    return dados

# @app.post("/webhook")
# async def receber_dados(request: Request):
#     dados = await request.json()
#
#     # Filtramos apenas para o evento de "Mensagem Recebida" (upsert)
#     if dados.get("event") == "messages.upsert":
#         msg_data = dados.get("data", {})
#
#         # Ignora se a mensagem foi enviada por você mesmo no celular
#         if msg_data.get("key", {}).get("fromMe"):
#             return {"status": "ignorada"}
#
#         numero_remetente = msg_data.get("key", {}).get("remoteJid")
#         # Tenta extrair o texto da mensagem (pode estar em diferentes campos)
#         corpo_mensagem = msg_data.get("message", {})
#         texto_usuario = corpo_mensagem.get("conversation") or \
#                         corpo_mensagem.get("extendedTextMessage", {}).get("text") or ""
#
#         print(f"Mensagem de {numero_remetente}: {texto_usuario}")
#
#         # LOGICA SIMPLES DE RESPOSTA
#         if "ajuda" in texto_usuario.lower():
#             enviar_texto(numero_remetente, "Olá! Eu sou o seu bot Python. Como posso ajudar?")
#         elif "projeto" in texto_usuario.lower():
#             enviar_texto(numero_remetente, "Estou rodando com FastAPI e Evolution API!")
#
#     return {"status": "recebido"}


if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 é obrigatório. Se estiver 127.0.0.1, o Docker não entra.
    uvicorn.run(app, host="0.0.0.0", port=8000)