"""
Don Quijote Gourmet & Kids — Setup Google Sheets
=================================================
Ejecuta este script UNA VEZ para crear las cabeceras y formato en ambas hojas.

Requisitos ANTES de ejecutar:
  1. Compartir ambas hojas con: don-quijote-sheets@n8n-workshops-lg.iam.gserviceaccount.com (como Editor)
  2. Actualizar .env con los IDs correctos de GOURMET_SHEET_ID y KIDS_SHEET_ID
  3. credentials.json en esta carpeta

Uso:
  python3 setup_sheets.py
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
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
    "🏷️ Brand",
]

FORMAT_HEADER = {
    "backgroundColor": {"red": 0.05, "green": 0.05, "blue": 0.05},
    "textFormat": {
        "foregroundColor": {"red": 0.784, "green": 0.659, "blue": 0.298},
        "bold": True,
        "fontSize": 11,
    },
    "horizontalAlignment": "CENTER",
}

SHEETS = {
    "GOURMET": os.getenv("GOURMET_SHEET_ID", os.getenv("GOOGLE_SHEET_ID")),
    "KIDS":    os.getenv("KIDS_SHEET_ID"),
}


def setup_sheet(client, sheet_id, brand_name):
    if not sheet_id or sheet_id.startswith("PEGA_AQUI"):
        print(f"⚠  {brand_name}: SHEET_ID no configurado, saltando.")
        return False

    try:
        sh = client.open_by_key(sheet_id)
        sheet = sh.sheet1

        sheet.clear()
        sheet.append_row(HEADERS)
        sheet.format(f"A1:{chr(64 + len(HEADERS))}1", FORMAT_HEADER)
        sheet.freeze(rows=1)

        print(f"✅ {brand_name} sheet configurado correctamente")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        return True
    except Exception as e:
        print(f"✗  {brand_name}: Error — {e}")
        return False


def main():
    print("\n🍽  Don Quijote — Setup Google Sheets\n")

    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)

    results = {}
    for brand, sheet_id in SHEETS.items():
        results[brand] = setup_sheet(client, sheet_id, brand)

    print("\n── Resumen ──────────────────────────────────")
    for brand, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {brand}")
    print()

    if not all(results.values()):
        print("⚠  Para completar el setup:")
        print("   1. Crea una nueva Google Sheet para Gourmet (sheets.new)")
        print("   2. Compártela con: don-quijote-sheets@n8n-workshops-lg.iam.gserviceaccount.com (Editor)")
        print("   3. Copia el ID de la URL y ponlo en .env como GOURMET_SHEET_ID=...")
        print("   4. Para KIDS: comparte la hoja 1Zl98pwjJjxsuvifMY32iqELR9K6NmFTXvNuMYiuXru8 con el mismo email")
        print("   5. Vuelve a ejecutar: python3 setup_sheets.py")


if __name__ == "__main__":
    main()
