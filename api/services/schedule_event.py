import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))   # api/services/
CORE_DIR  = os.path.join(os.path.dirname(BASE_DIR), "core")  # api/core/
TOKEN_FILE         = os.getenv("GOOGLE_TOKEN_PATH",         os.path.join(CORE_DIR, "token.json"))
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_PATH", os.path.join(CORE_DIR, "client_secret.json"))

# ID do calendário — "primary" usa o calendário principal da conta autorizada
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")


class GoogleCalendarService:
    def __init__(self):
        self.service = build("calendar", "v3", credentials=self._get_credentials())

    def _get_credentials(self) -> Credentials:
        """
        Carrega as credenciais do token.json.
        Se o token estiver expirado, renova automaticamente.
        Se não existir, abre o navegador para autorização (apenas na primeira vez).
        """
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # Token expirado mas com refresh token disponível — renova silenciosamente
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)

        # Sem token — abre navegador para autorização (só acontece uma vez)
        elif not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            self._save_token(creds)

        return creds

    def _save_token(self, creds: Credentials):
        """Persiste o token atualizado em disco."""
        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    def create_event(
        self,
        nameEvent: str,
        descriptionEvent: str,
        startDateTimeEvent: str,
        endDateTimeEvent: str,
        destinateEmail: str,
    ) -> str:
        """
        Cria um evento no Google Agenda e convida o cliente por email.

        Args:
            nameEvent:           Título do evento (ex: "Corte: Barba com João")
            descriptionEvent:    Descrição do evento
            startDateTimeEvent:  Início no formato ISO 8601 (ex: "2025-07-10T14:00:00-03:00")
            endDateTimeEvent:    Fim no formato ISO 8601   (ex: "2025-07-10T15:00:00-03:00")
            destinateEmail:      Email do cliente para envio do convite

        Returns:
            Link HTML do evento criado (str)
        """
        event_body = {
            "summary": nameEvent,
            "description": descriptionEvent,
            "start": {
                "dateTime": startDateTimeEvent,
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": endDateTimeEvent,
                "timeZone": "America/Sao_Paulo",
            },
            # Cliente recebe convite no email informado
            "attendees": [
                {"email": destinateEmail},
            ],
            # Lembretes automáticos
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},   # Email 1h antes
                    {"method": "popup", "minutes": 30},   # Popup 30min antes
                ],
            },
            "guestsCanSeeOtherGuests": False,
        }

        created_event = (
            self.service.events()
            .insert(
                calendarId=CALENDAR_ID,
                body=event_body,
                sendUpdates="all",  # Dispara email de convite para o cliente
            )
            .execute()
        )

        return created_event.get("htmlLink", "https://calendar.google.com")