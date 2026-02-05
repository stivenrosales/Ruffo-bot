"""Cliente de Google Sheets."""

import os
from typing import Optional, Any
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import structlog

from src.config.settings import settings

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

_service = None


def get_sheets_service():
    """Obtiene o crea el servicio de Google Sheets."""
    global _service

    if _service is not None:
        return _service

    creds = None
    credentials_path = settings.google_credentials_path
    token_path = "token.json"

    # Intentar cargar credenciales de service account primero
    if credentials_path.endswith(".json") and os.path.exists(credentials_path):
        try:
            # Verificar si es service account
            import json

            with open(credentials_path) as f:
                cred_data = json.load(f)

            if "type" in cred_data and cred_data["type"] == "service_account":
                creds = ServiceAccountCredentials.from_service_account_file(
                    credentials_path, scopes=SCOPES
                )
                logger.info("Using service account credentials")
            else:
                # OAuth credentials
                if os.path.exists(token_path):
                    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, SCOPES
                        )
                        creds = flow.run_local_server(port=0)

                    with open(token_path, "w") as token:
                        token.write(creds.to_json())
                logger.info("Using OAuth credentials")
        except Exception as e:
            logger.error("Error loading credentials", error=str(e))
            raise

    _service = build("sheets", "v4", credentials=creds)
    return _service


class SheetsClient:
    """Cliente para interactuar con Google Sheets."""

    def __init__(self):
        self.service = get_sheets_service()
        self.spreadsheet_id = settings.google_sheets_id
        self.sheet_name = settings.google_sheets_name

    def read_range(self, range_notation: str) -> list[list[Any]]:
        """Lee un rango de celdas."""
        try:
            full_range = f"{self.sheet_name}!{range_notation}"
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=full_range)
                .execute()
            )
            return result.get("values", [])
        except Exception as e:
            logger.error("Error reading range", range=range_notation, error=str(e))
            return []

    def read_all(self) -> list[list[Any]]:
        """Lee toda la hoja."""
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=self.sheet_name)
                .execute()
            )
            return result.get("values", [])
        except Exception as e:
            logger.error("Error reading sheet", error=str(e))
            return []

    def get_headers(self) -> list[str]:
        """Obtiene los headers (primera fila)."""
        data = self.read_range("1:1")
        return data[0] if data else []

    def get_all_as_dicts(self) -> list[dict]:
        """Lee toda la hoja como lista de diccionarios."""
        data = self.read_all()
        if not data or len(data) < 2:
            return []

        headers = data[0]
        rows = []
        for row in data[1:]:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            rows.append(row_dict)
        return rows

    def search(self, query: str, columns: Optional[list[str]] = None) -> list[dict]:
        """Busca en la hoja por query."""
        all_data = self.get_all_as_dicts()
        if not all_data:
            return []

        query_lower = query.lower()
        results = []

        for row in all_data:
            # Si se especifican columnas, buscar solo en esas
            if columns:
                search_text = " ".join(
                    str(row.get(col, "")).lower() for col in columns
                )
            else:
                search_text = " ".join(str(v).lower() for v in row.values())

            if query_lower in search_text:
                results.append(row)

        return results


# Instancia global del cliente
sheets_client: Optional[SheetsClient] = None


def get_client() -> SheetsClient:
    """Obtiene la instancia del cliente de Sheets."""
    global sheets_client
    if sheets_client is None:
        sheets_client = SheetsClient()
    return sheets_client
