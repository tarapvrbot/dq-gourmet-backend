"""
Don Quijote Gourmet — Setup Google Sheet
=========================================
Ejecuta este script UNA VEZ para crear las cabeceras y formato del Sheet.

Uso:
  python3 setup_sheet.py

Requisitos:
  - credentials.json en esta carpeta (service account de Google)
  - GOOGLE_SHEET_ID en .env
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def setup():
    creds  = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).sheet1

    # ── Cabeceras ──────────────────────────────────────────────────────────
    headers = [
        "📅 Fecha",
        "👤 Nombre",
        "📧 Email",
        "📱 Teléfono",
        "🏠 Dirección",
        "🏙️ Ciudad",
        "📮 Código Postal",
        "🌍 País",
        "🛒 Productos",
        "💶 Subtotal",
        "🚚 Envío",
        "💰 Total",
        "✅ Estado",
        "🔑 Stripe ID",
    ]

    sheet.clear()
    sheet.append_row(headers)

    # ── Formato cabeceras (fondo oscuro, texto dorado) ─────────────────────
    sheet.format("A1:N1", {
        "backgroundColor": {"red": 0.05, "green": 0.05, "blue": 0.05},
        "textFormat": {
            "foregroundColor": {"red": 0.784, "green": 0.659, "blue": 0.298},
            "bold": True,
            "fontSize": 11,
        },
        "horizontalAlignment": "CENTER",
    })

    # ── Congelar primera fila ──────────────────────────────────────────────
    sheet.freeze(rows=1)

    # ── Anchos de columna ──────────────────────────────────────────────────
    # gspread no soporta anchos directamente, pero dejamos el sheet limpio
    print("✓ Google Sheet configurado correctamente")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

if __name__ == "__main__":
    setup()
