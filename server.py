"""
Don Quijote Gourmet & Kids — Servidor de Pedidos
=================================================
Flask + Stripe + Google Sheets + Multi-Channel Alerts

Multi-brand payment system with enhanced notifications:
  - Gourmet: Premium products (salsas, patés, etc.)
  - Kids: Educational cooking kits (kits, ingredients, mixes)

Alert Channels:
  - Email: Multiple recipients, branded templates
  - SMS: Twilio integration (optional)
  - Webhooks: Discord, Slack, custom endpoints (optional)
  - Admin Dashboard: Real-time order tracking

Flujo:
  1. Frontend envía pedido con brand metadata → POST /create-checkout
  2. Servidor crea sesión Stripe → devuelve URL de pago
  3. Cliente paga en Stripe
  4. Stripe llama a POST /webhook
  5. Servidor detecta brand en metadata → guarda en sheet + envía alertas por todos los canales
"""

import os
import json
import base64
import csv
import io
import hashlib
import sqlite3
import stripe
import gspread
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from functools import wraps
import logging

# Import alert system
from alerts import (
    AlertOrchestrator,
    AdminDashboard,
    AlertLogger,
    AlertConfig
)

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3456",
    "http://127.0.0.1:3456",
    "https://donquijote-kids.netlify.app",
    os.getenv("FRONTEND_URL", "*")
])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Stripe ────────────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# ── Config ────────────────────────────────────────────────────────────────
# Gourmet
GOURMET_NOTIFY_EMAIL = os.getenv("GOURMET_NOTIFY_EMAIL", "tarapachecovr@gmail.com")
GOURMET_SHEET_ID     = os.getenv("GOURMET_SHEET_ID", os.getenv("GOOGLE_SHEET_ID"))

# Kids
KIDS_NOTIFY_EMAIL    = os.getenv("KIDS_NOTIFY_EMAIL", "hola@donquijotekids.com")
KIDS_SHEET_ID        = os.getenv("KIDS_SHEET_ID")

# Shared
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3456")
KIDS_FRONTEND_URL    = os.getenv("KIDS_FRONTEND_URL", "https://donquijote-kids.netlify.app")

# Admin authentication
ADMIN_API_KEY        = os.getenv("ADMIN_API_KEY", "admin_key_not_set")

# Validate alert configuration on startup
valid, warnings = AlertConfig.validate()
if warnings:
    for warning in warnings:
        logger.warning(f"Alert config: {warning}")
    logger.info("Alert system will operate with reduced channels")


# ── SQLite ───────────────────────────────────────────────────────────────
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/tmp/orders.db")


def init_db():
    """Crea las tablas orders y visits si no existen."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT,
                nombre    TEXT,
                email     TEXT,
                telefono  TEXT,
                direccion TEXT,
                ciudad    TEXT,
                cp        TEXT,
                pais      TEXT,
                productos TEXT,
                subtotal  REAL,
                envio     REAL,
                total     REAL,
                estado    TEXT,
                stripe_id TEXT,
                brand     TEXT
            )
        """)
        # Tabla de visitas: una fila por cada vez que alguien entra a jugar.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT,   -- timestamp legible (dd/mm/YYYY HH:MM)
                dia         TEXT,   -- YYYY-MM-DD, para agrupar por día
                brand       TEXT,
                path        TEXT,   -- página a la que entró
                referrer    TEXT,   -- de dónde venía
                visitor_id  TEXT,   -- id anónimo generado en el navegador
                ip_hash     TEXT    -- hash de la IP (privacidad: no guardamos la IP real)
            )
        """)
        # Índices para que las consultas por día / visitante sean rápidas.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_dia ON visits(dia)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_visitor ON visits(visitor_id)")
        conn.commit()


def save_to_sqlite(order: dict, brand: str = "gourmet"):
    """Guarda el pedido en SQLite. No lanza excepciones al caller."""
    try:
        productos_str = " | ".join(
            f"{item['name']} x{item['qty']} (€{item['price']*item['qty']:.2f})"
            for item in order.get("items", [])
        )
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO orders
                   (fecha, nombre, email, telefono, direccion, ciudad, cp, pais,
                    productos, subtotal, envio, total, estado, stripe_id, brand)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    order.get("name", ""),
                    order.get("email", ""),
                    order.get("phone", ""),
                    order.get("address", ""),
                    order.get("city", ""),
                    order.get("zip", ""),
                    order.get("country", ""),
                    productos_str,
                    order.get("subtotal", 0),
                    order.get("shipping", 0),
                    order.get("total", 0),
                    "Pagado",
                    order.get("stripe_id", ""),
                    brand.upper(),
                ),
            )
            conn.commit()
        logger.info(f"Pedido {brand.upper()} guardado en SQLite: {order.get('name')}")
    except Exception as e:
        logger.error(f"Error SQLite ({brand}): {e}")


def save_visit(brand: str, path: str, referrer: str, visitor_id: str, ip: str):
    """Registra una visita (alguien que entra a jugar). No lanza excepciones al caller."""
    try:
        now = datetime.now()
        # Hasheamos la IP en lugar de guardarla: nos sirve para contar visitantes
        # únicos sin almacenar datos personales.
        ip_hash = hashlib.sha256((ip or "").encode("utf-8")).hexdigest()[:16] if ip else ""
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO visits
                   (fecha, dia, brand, path, referrer, visitor_id, ip_hash)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    now.strftime("%d/%m/%Y %H:%M"),
                    now.strftime("%Y-%m-%d"),
                    (brand or "kids").lower(),
                    (path or "")[:255],
                    (referrer or "")[:255],
                    (visitor_id or "")[:64],
                    ip_hash,
                ),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error guardando visita: {e}")


def get_visit_stats():
    """Devuelve estadísticas de visitas para el panel."""
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) AS c FROM visits").fetchone()["c"]
        # "Visitantes únicos" = combinaciones distintas de visitor_id o, si no hay,
        # de hash de IP.
        unique_total = conn.execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(visitor_id,''), ip_hash)) AS c FROM visits"
        ).fetchone()["c"]

        today_total = conn.execute(
            "SELECT COUNT(*) AS c FROM visits WHERE dia = ?", (today,)
        ).fetchone()["c"]
        today_unique = conn.execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(visitor_id,''), ip_hash)) AS c "
            "FROM visits WHERE dia = ?", (today,)
        ).fetchone()["c"]

        # Últimos 14 días, día a día.
        by_day = [
            {"dia": r["dia"], "visitas": r["c"], "unicos": r["u"]}
            for r in conn.execute(
                """SELECT dia,
                          COUNT(*) AS c,
                          COUNT(DISTINCT COALESCE(NULLIF(visitor_id,''), ip_hash)) AS u
                   FROM visits
                   GROUP BY dia
                   ORDER BY dia DESC
                   LIMIT 14"""
            ).fetchall()
        ]

        by_brand = [
            {"brand": r["brand"], "visitas": r["c"]}
            for r in conn.execute(
                "SELECT brand, COUNT(*) AS c FROM visits GROUP BY brand ORDER BY c DESC"
            ).fetchall()
        ]

    return {
        "total_visitas": total,
        "visitantes_unicos": unique_total,
        "hoy_visitas": today_total,
        "hoy_unicos": today_unique,
        "por_dia": by_day,
        "por_marca": by_brand,
    }


# Inicializar DB al arrancar
init_db()


# ── Google Sheets ─────────────────────────────────────────────────────────
def get_sheet(brand="gourmet"):
    """Get Google Sheet for the specified brand."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
    if creds_b64:
        creds_info = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    # Select sheet based on brand
    sheet_id = KIDS_SHEET_ID if brand == "kids" else GOURMET_SHEET_ID
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet


def save_to_sheet(order: dict, brand: str = "gourmet"):
    """Añade una fila nueva con los datos del pedido a la sheet del brand."""
    try:
        sheet = get_sheet(brand)
        # Cabeceras si la hoja está vacía
        if sheet.row_count == 0 or not sheet.get_all_values():
            sheet.append_row([
                "Fecha", "Nombre", "Email", "Teléfono",
                "Dirección", "Ciudad", "CP", "País",
                "Productos", "Subtotal", "Envío", "Total", "Estado", "Stripe ID", "Brand"
            ])

        productos_str = " | ".join(
            f"{item['name']} x{item['qty']} (€{item['price']*item['qty']:.2f})"
            for item in order.get("items", [])
        )

        sheet.append_row([
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            order.get("name", ""),
            order.get("email", ""),
            order.get("phone", ""),
            order.get("address", ""),
            order.get("city", ""),
            order.get("zip", ""),
            order.get("country", ""),
            productos_str,
            f"€{order.get('subtotal', 0):.2f}",
            f"€{order.get('shipping', 0):.2f}",
            f"€{order.get('total', 0):.2f}",
            "✅ Pagado",
            order.get("stripe_id", ""),
            brand.upper(),
        ])
        print(f"✓ Pedido {brand.upper()} guardado en Google Sheets: {order.get('name')}")
    except Exception as e:
        print(f"✗ Error Google Sheets ({brand}): {e}")


# ── Admin Auth Decorator ──────────────────────────────────────────────────
def require_admin_key(f):
    """Decorator to require admin API key for protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        # Accept "Bearer KEY" or "KEY" format
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header

        if not token or token != ADMIN_API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


# ── ROUTES ────────────────────────────────────────────────────────────────


@app.route("/create-checkout", methods=["POST"])
def create_checkout():
    """
    Recibe el pedido del frontend (Gourmet o Kids) y crea una sesión de pago en Stripe.
    Detecta el brand desde el payload y configura URLs de retorno según corresponda.
    """
    data = request.json
    items     = data.get("items", [])
    customer  = data.get("customer", {})
    brand     = data.get("brand", "gourmet").lower()  # "gourmet" o "kids"
    subtotal  = sum(i["price"] * i["qty"] for i in items)

    # Shipping: Kids sin envío (kits se entregan directamente), Gourmet gratis desde €60
    if brand == "kids":
        shipping = 0
    else:
        shipping = 0 if subtotal >= 60 else 4.95

    total = subtotal + shipping

    if not items:
        return jsonify({"error": "Cesta vacía"}), 400

    # Construir line_items para Stripe
    def build_product_data(item):
        data = {"name": f"{item.get('icon', '')} {item['name']}".strip()}
        if item.get("size"):  # Solo incluir description si hay valor (Stripe rechaza strings vacíos)
            data["description"] = item["size"]
        return data

    line_items = [
        {
            "price_data": {
                "currency": "eur",
                "product_data": build_product_data(item),
                "unit_amount": int(item["price"] * 100),  # céntimos
            },
            "quantity": item["qty"],
        }
        for item in items
    ]

    # Envío como line item separado (solo Gourmet)
    if shipping > 0:
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": "Envío a domicilio"},
                "unit_amount": int(shipping * 100),
            },
            "quantity": 1,
        })

    # Guardar datos del cliente en metadata para recuperarlos en el webhook
    metadata = {
        "brand":   brand,  # CRITICAL: marca el brand para webhook
        "name":    customer.get("name", ""),
        "email":   customer.get("email", ""),
        "phone":   customer.get("phone", ""),
        "address": customer.get("address", ""),
        "city":    customer.get("city", ""),
        "zip":     customer.get("zip", ""),
        "country": customer.get("country", "ES"),
        "items":   json.dumps(items),
        "subtotal": str(subtotal),
        "shipping": str(shipping),
        "total":    str(total),
    }

    # Seleccionar URLs según brand
    frontend_url = KIDS_FRONTEND_URL if brand == "kids" else FRONTEND_URL

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            customer_email=customer.get("email"),
            metadata=metadata,
            success_url=f"{frontend_url}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/?cancelled=1",
            locale="es",
        )
        print(f"✓ Sesión Stripe creada para {brand.upper()}: {session.id}")
        return jsonify({"url": session.url})
    except Exception as e:
        print(f"✗ Error Stripe ({brand}): {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Stripe webhook handler - payment completion.
    Detects brand from metadata and processes order through all alert channels.
    """
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe signature")
        return jsonify({"error": "Invalid signature"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        # Detect brand from metadata (default: gourmet for backward compatibility)
        brand = metadata.get("brand", "gourmet").lower()

        # Reconstruct order object
        order = {
            "stripe_id": session["id"],
            "name": metadata.get("name"),
            "email": metadata.get("email"),
            "phone": metadata.get("phone"),
            "address": metadata.get("address"),
            "city": metadata.get("city"),
            "zip": metadata.get("zip"),
            "country": metadata.get("country"),
            "items": json.loads(metadata.get("items", "[]")),
            "subtotal": float(metadata.get("subtotal", 0)),
            "shipping": float(metadata.get("shipping", 0)),
            "total": float(metadata.get("total", 0)),
        }

        # Save to SQLite (primary, always)
        save_to_sqlite(order, brand=brand)

        # Save to Google Sheets (secondary, best-effort — errors are logged but ignored)
        try:
            save_to_sheet(order, brand=brand)
        except Exception as sheets_err:
            logger.warning(f"Google Sheets skipped ({brand}): {sheets_err}")

        # Record in admin dashboard
        AdminDashboard.record_order(order, brand=brand)

        # Send alerts across all configured channels
        alert_results = AlertOrchestrator.send_all_alerts(order, brand=brand)

        # Log webhook processing
        logger.info(
            f"Order processed: {brand.upper()} - {order['name']} - "
            f"€{order['total']:.2f} - Alerts: {alert_results['summary']}"
        )

        # Return success with alert summary
        return jsonify({
            "status": "ok",
            "order_id": order["stripe_id"],
            "brand": brand,
            "alerts": alert_results["summary"]
        })

    return jsonify({"status": "ok"})


# ── Visitas / Analytics ───────────────────────────────────────────────────
@app.route("/track-visit", methods=["POST", "GET"])
def track_visit():
    """
    Registra que alguien ha entrado a jugar.
    El frontend (web de Netlify) llama a este endpoint al cargar la página.
    Público a propósito: no requiere clave, porque lo llama el navegador del visitante.
    """
    data = request.get_json(silent=True) or {}

    # IP real detrás del proxy (Railway/Netlify) → cabecera X-Forwarded-For.
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "")

    save_visit(
        brand=data.get("brand", "kids"),
        path=data.get("path", request.args.get("path", "")),
        referrer=data.get("referrer", request.referrer or ""),
        visitor_id=data.get("visitor_id", request.args.get("visitor_id", "")),
        ip=ip,
    )
    # Respuesta mínima; CORS ya permite el origen de Netlify.
    return jsonify({"status": "ok"})


# ── Admin Dashboard Endpoints ────────────────────────────────────────────
@app.route("/admin/orders", methods=["GET"])
@require_admin_key
def admin_orders():
    """Get recent orders for admin dashboard."""
    limit = request.args.get("limit", 10, type=int)
    orders = AdminDashboard.get_recent_orders(limit=limit)
    return jsonify({
        "status": "ok",
        "count": len(orders),
        "orders": orders
    })


@app.route("/admin/stats", methods=["GET"])
@require_admin_key
def admin_stats():
    """Get dashboard statistics."""
    stats = AdminDashboard.get_stats()
    return jsonify({
        "status": "ok",
        "stats": stats
    })


@app.route("/admin/visits", methods=["GET"])
@require_admin_key
def admin_visits():
    """Estadísticas de visitas (cuánta gente entra a jugar)."""
    return jsonify({
        "status": "ok",
        "visits": get_visit_stats()
    })


@app.route("/admin/alerts", methods=["GET"])
@require_admin_key
def admin_alerts():
    """Get recent alert logs."""
    limit = request.args.get("limit", 50, type=int)
    alerts = AlertLogger.get_recent_alerts(limit=limit)
    return jsonify({
        "status": "ok",
        "count": len(alerts),
        "alerts": alerts
    })


@app.route("/admin/alerts/config", methods=["GET"])
@require_admin_key
def admin_alerts_config():
    """Get current alert configuration status."""
    valid, warnings = AlertConfig.validate()
    return jsonify({
        "status": "ok",
        "valid": valid,
        "warnings": warnings,
        "config": {
            "email_enabled": bool(AlertConfig.SMTP_PASSWORD),
            "email_primary": AlertConfig.ALERT_EMAIL_PRIMARY,
            "email_secondary": bool(AlertConfig.ALERT_EMAIL_SECONDARY),
            "email_backup": bool(AlertConfig.ALERT_EMAIL_BACKUP),
            "sms_enabled": AlertConfig.SMS_ALERT_ENABLED,
            "sms_min_amount": AlertConfig.SMS_ALERT_MIN_AMOUNT,
            "webhooks_enabled": AlertConfig.WEBHOOK_ALERT_ENABLED,
            "discord_configured": bool(AlertConfig.DISCORD_WEBHOOK_URL),
            "slack_configured": bool(AlertConfig.SLACK_WEBHOOK_URL),
            "custom_webhook_configured": bool(AlertConfig.CUSTOM_WEBHOOK_URL),
        }
    })


# ── CSV Export ───────────────────────────────────────────────────────────
@app.route("/admin/export.csv", methods=["GET"])
@require_admin_key
def admin_export_csv():
    """Descarga todos los pedidos de SQLite como CSV."""
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "fecha", "nombre", "email", "telefono", "direccion",
            "ciudad", "cp", "pais", "productos", "subtotal", "envio",
            "total", "estado", "stripe_id", "brand"
        ])
        for row in rows:
            writer.writerow(list(row))

        csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM para Excel
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=pedidos.csv"},
        )
    except Exception as e:
        logger.error(f"Error exportando CSV: {e}")
        return jsonify({"error": str(e)}), 500


# ── Panel visual de visitas ───────────────────────────────────────────────
PANEL_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel · ¿Cuánta gente entra?</title>
<style>
  :root { --bg:#0f1226; --card:#1b1f3b; --accent:#ffd23f; --text:#f5f6ff; --muted:#9aa0c7; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--text); padding:24px; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:var(--muted); margin:0 0 24px; font-size:14px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; }
  .card { background:var(--card); border-radius:16px; padding:20px; }
  .num { font-size:40px; font-weight:700; color:var(--accent); line-height:1; }
  .label { color:var(--muted); font-size:13px; margin-top:8px; }
  table { width:100%; border-collapse:collapse; margin-top:14px; font-size:14px; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid #2a2f55; }
  th { color:var(--muted); font-weight:600; }
  .bar { height:8px; background:var(--accent); border-radius:4px; }
  .section { background:var(--card); border-radius:16px; padding:20px; margin-top:16px; }
  .section h2 { font-size:16px; margin:0 0 6px; }
  input,button { font-size:15px; padding:10px 14px; border-radius:10px; border:1px solid #2a2f55; }
  input { background:#11142b; color:var(--text); width:260px; }
  button { background:var(--accent); color:#1b1f3b; font-weight:700; border:none; cursor:pointer; }
  .login { max-width:360px; margin:60px auto; text-align:center; }
  .err { color:#ff6b6b; font-size:14px; min-height:18px; }
  .muted { color:var(--muted); font-size:12px; margin-top:24px; }
</style>
</head>
<body>
<div id="login" class="login" style="display:none">
  <h1>Panel de visitas</h1>
  <p class="sub">Introduce la clave de administrador</p>
  <p><input id="key" type="password" placeholder="Admin API key" autocomplete="off"></p>
  <p><button onclick="saveKey()">Entrar</button></p>
  <p class="err" id="loginErr"></p>
</div>

<div id="dash" style="display:none">
  <h1>¿Cuánta gente entra a jugar?</h1>
  <p class="sub">Datos en tiempo real · <span id="updated"></span> ·
     <a href="#" onclick="logout();return false" style="color:var(--muted)">salir</a></p>

  <div class="grid">
    <div class="card"><div class="num" id="hoyUnicos">–</div><div class="label">Personas hoy</div></div>
    <div class="card"><div class="num" id="hoyVisitas">–</div><div class="label">Entradas hoy</div></div>
    <div class="card"><div class="num" id="totalUnicos">–</div><div class="label">Personas (total)</div></div>
    <div class="card"><div class="num" id="totalVisitas">–</div><div class="label">Entradas (total)</div></div>
  </div>

  <div class="section">
    <h2>Últimos días</h2>
    <table id="dias"><thead><tr><th>Día</th><th>Personas</th><th>Entradas</th><th></th></tr></thead><tbody></tbody></table>
  </div>

  <div class="section">
    <h2>Por marca</h2>
    <table id="marcas"><thead><tr><th>Marca</th><th>Entradas</th></tr></thead><tbody></tbody></table>
  </div>

  <p class="muted">«Personas» = visitantes únicos · «Entradas» = veces que se ha abierto el juego.</p>
</div>

<script>
const KEY_NAME = 'dq_admin_key';
function getKey(){ return localStorage.getItem(KEY_NAME) || ''; }
function saveKey(){
  const k = document.getElementById('key').value.trim();
  if(!k){ return; }
  localStorage.setItem(KEY_NAME, k);
  load();
}
function logout(){ localStorage.removeItem(KEY_NAME); showLogin(); }
function showLogin(){ document.getElementById('login').style.display='block';
                     document.getElementById('dash').style.display='none'; }
function showDash(){ document.getElementById('login').style.display='none';
                    document.getElementById('dash').style.display='block'; }

async function load(){
  const key = getKey();
  if(!key){ showLogin(); return; }
  try{
    const res = await fetch('/admin/visits', { headers: { 'Authorization': 'Bearer ' + key } });
    if(res.status === 401){ document.getElementById('loginErr').textContent='Clave incorrecta'; showLogin(); return; }
    const data = await res.json();
    render(data.visits);
    showDash();
  }catch(e){
    document.getElementById('loginErr').textContent = 'Error de conexión';
    showLogin();
  }
}

function render(v){
  document.getElementById('hoyUnicos').textContent   = v.hoy_unicos;
  document.getElementById('hoyVisitas').textContent  = v.hoy_visitas;
  document.getElementById('totalUnicos').textContent = v.visitantes_unicos;
  document.getElementById('totalVisitas').textContent= v.total_visitas;
  document.getElementById('updated').textContent = new Date().toLocaleString('es-ES');

  const maxDia = Math.max(1, ...v.por_dia.map(d => d.visitas));
  document.querySelector('#dias tbody').innerHTML = v.por_dia.map(d =>
    `<tr><td>${d.dia}</td><td>${d.unicos}</td><td>${d.visitas}</td>
     <td><div class="bar" style="width:${Math.round(d.visitas/maxDia*100)}%"></div></td></tr>`
  ).join('') || '<tr><td colspan="4">Aún no hay visitas</td></tr>';

  document.querySelector('#marcas tbody').innerHTML = v.por_marca.map(m =>
    `<tr><td>${m.brand}</td><td>${m.visitas}</td></tr>`
  ).join('') || '<tr><td colspan="2">Sin datos</td></tr>';
}

load();
setInterval(load, 30000); // refresca cada 30s
</script>
</body>
</html>"""


@app.route("/panel", methods=["GET"])
def panel():
    """Página visual para ver cuánta gente entra a jugar. La clave se pide en la propia página."""
    return Response(PANEL_HTML, mimetype="text/html")


# ── Health & Debug Endpoints ──────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    stats = AdminDashboard.get_stats()
    return jsonify({
        "status": "ok",
        "service": "Don Quijote Gourmet & Kids",
        "alerts_enabled": True,
        "recent_stats": {
            "total_orders": stats.get("total_orders", 0),
            "total_revenue": stats.get("total_revenue", 0)
        }
    })


@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access."""
    return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401


@app.errorhandler(500)
def server_error(error):
    """Handle server errors."""
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n🍽  Don Quijote Gourmet & Kids — Server started on port {port}")
    print(f"   Alert System: Multi-channel enabled")
    print(f"   Admin Dashboard: /admin/orders (requires API key)")
    print(f"   Health Check: /health\n")
    app.run(host="0.0.0.0", port=port, debug=False)
