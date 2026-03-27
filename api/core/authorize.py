# authorize.py — Rode este script UMA VEZ para gerar o token.json
# Depois disso o bot funciona automaticamente, sem precisar rodar de novo.

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Pasta onde este arquivo está — resolve o problema de caminhos relativos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE         = os.path.join(BASE_DIR, "token.json")

def main():
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"❌ Arquivo não encontrado: {CLIENT_SECRET_FILE}")
        print("Coloque o client_secret.json na mesma pasta que este script.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES
    )

    # Abre o navegador para você autorizar
    creds = flow.run_local_server(port=0)

    # Salva o token para uso futuro do bot
    with open(TOKEN_FILE, "w") as token_file:
        token_file.write(creds.to_json())

    print(f"✅ Autorização concluída! token.json gerado em: {TOKEN_FILE}")
    print("Agora você pode rodar o bot normalmente.")

if __name__ == "__main__":
    main()