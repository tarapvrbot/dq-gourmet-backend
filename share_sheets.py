"""
Share Google Sheets with service account using your own OAuth client.
Requiere: oauth_client.json (descargado de GCP Console → n8n-workshops-client)

Uso: python3 share_sheets.py
"""
import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

SHEETS_TO_SHARE = [
    ("DQ GOURMET", "19zI3rH30cpNiMqq4iTZZtoMWDm47qYFkEJ8C241-dRU"),
    ("DQ KIDS",    "1Zl98pwjJjxsuvifMY32iqELR9K6NmFTXvNuMYiuXru8"),
]
SERVICE_ACCOUNT = "don-quijote-sheets@n8n-workshops-lg.iam.gserviceaccount.com"
OAUTH_FILE = "oauth_client.json"

if not os.path.exists(OAUTH_FILE):
    print(f"✗ Falta {OAUTH_FILE}")
    print("  1. Ve a: console.cloud.google.com/auth/clients?project=n8n-workshops-lg")
    print("  2. Haz clic en 'n8n-workshops-client'")
    print("  3. Descarga el JSON y guárdalo aquí como oauth_client.json")
    exit(1)

# Load client secrets
with open(OAUTH_FILE) as f:
    client_data = json.load(f)

# Support both 'web' and 'installed' key
cred_type = "web" if "web" in client_data else "installed"
client_id = client_data[cred_type]["client_id"]
client_secret = client_data[cred_type]["client_secret"]

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("✅ Autorizado. Puedes cerrar esta pestaña.".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *args): pass

def main():
    print("\n🔑 Don Quijote — Compartir Google Sheets con Service Account")
    print("=" * 55)

    # Build flow using the downloaded credentials
    flow = Flow.from_client_config(
        client_data,
        scopes=SCOPES,
        redirect_uri="http://localhost:8080"
    )

    # For web app clients, we need to add localhost to authorized URIs
    # If it fails, we'll use the OOB method
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline"
    )

    # Start callback server
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    print(f"\n→ Abriendo navegador para autenticación de Google Drive...")
    webbrowser.open(auth_url)
    print("  Haz clic en 'Permitir/Allow' en el navegador")
    print("  Espera hasta 60 segundos...\n")

    timeout = 60
    while auth_code is None and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if not auth_code:
        print("✗ Timeout. Asegúrate de que http://localhost:8080 está en los URIs autorizados")
        print("  Ve a GCP Console → n8n-workshops-client → Editar → Añadir URI de redirección: http://localhost:8080")
        return

    flow.fetch_token(code=auth_code)
    creds = flow.credentials

    service = build("drive", "v3", credentials=creds)

    print("✅ Autenticado. Compartiendo hojas...\n")

    for name, sheet_id in SHEETS_TO_SHARE:
        try:
            service.permissions().create(
                fileId=sheet_id,
                body={
                    "type": "user",
                    "role": "writer",
                    "emailAddress": SERVICE_ACCOUNT,
                },
                sendNotificationEmail=False,
            ).execute()
            print(f"✅ {name} compartido con service account")
        except Exception as e:
            if "already" in str(e).lower():
                print(f"✓  {name} ya estaba compartido")
            else:
                print(f"✗  {name}: {e}")

    print("\n🏁 Listo! Ejecuta ahora: python3 setup_sheets.py")

if __name__ == "__main__":
    main()
