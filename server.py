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
import stripe
import gspread
from datetime import datetime
from flask import Flask, request, jsonify
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

        # Save to Google Sheets
        save_to_sheet(order, brand=brand)

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
