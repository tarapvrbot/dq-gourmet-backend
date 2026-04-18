"""
Alert System for Don Quijote Gourmet & Kids
============================================
Multi-channel notification system with graceful fallbacks:
- Email (primary): Multiple recipients, branded templates
- SMS (optional): Twilio integration for urgent alerts
- Webhooks (optional): Discord, Slack, custom endpoints
- Admin dashboard: Real-time order tracking
- Logging: Complete audit trail of all alerts
"""

import os
import json
import requests
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List, Tuple
import logging

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("alerts")


# ── Configuration ──────────────────────────────────────────────────────────
class AlertConfig:
    """Load alert configuration from environment variables."""

    # Email — Resend HTTP API (preferred, Railway-compatible)
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

    # Email — Zoho SMTP (fallback if Resend not configured)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zoho.eu")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

    # Gourmet brand SMTP
    GOURMET_SMTP_USER = os.getenv("GOURMET_SMTP_USER", "hello@donquijotegourmet.com")
    GOURMET_SMTP_PASSWORD = os.getenv("GOURMET_SMTP_PASSWORD")

    # Kids brand SMTP
    KIDS_SMTP_USER = os.getenv("KIDS_SMTP_USER", "hello@donquijotekids.com")
    KIDS_SMTP_PASSWORD = os.getenv("KIDS_SMTP_PASSWORD")

    # Fallback (legacy)
    SMTP_USER = os.getenv("SMTP_USER", GOURMET_SMTP_USER)
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", GOURMET_SMTP_PASSWORD)

    # Primary alerts
    ALERT_EMAIL_PRIMARY = os.getenv("ALERT_EMAIL_PRIMARY", "tarapachecovr@gmail.com")
    ALERT_EMAIL_SECONDARY = os.getenv("ALERT_EMAIL_SECONDARY", "")
    ALERT_EMAIL_BACKUP = os.getenv("ALERT_EMAIL_BACKUP", "")

    # Kids brand alternate email
    KIDS_NOTIFY_EMAIL = os.getenv("KIDS_NOTIFY_EMAIL", "hola@donquijotekids.com")

    # SMS (Twilio)
    SMS_ALERT_ENABLED = os.getenv("SMS_ALERT_ENABLED", "false").lower() == "true"
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE", "")
    SMS_ALERT_MIN_AMOUNT = float(os.getenv("SMS_ALERT_MIN_AMOUNT", "50"))

    # Webhooks
    WEBHOOK_ALERT_ENABLED = os.getenv("WEBHOOK_ALERT_ENABLED", "false").lower() == "true"
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    CUSTOM_WEBHOOK_URL = os.getenv("CUSTOM_WEBHOOK_URL", "")

    # Admin dashboard
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
    ADMIN_ALERT_ENABLED = os.getenv("ADMIN_ALERT_ENABLED", "true").lower() == "true"

    # Alert log
    ALERT_LOG_FILE = os.getenv("ALERT_LOG_FILE", "/tmp/don_quijote_alerts.log")

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """Validate configuration and return (is_valid, warnings)."""
        warnings = []

        if not cls.SMTP_PASSWORD:
            warnings.append("GMAIL_APP_PASSWORD not set - email alerts will fail")

        if cls.SMS_ALERT_ENABLED and not (cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN):
            warnings.append("SMS enabled but TWILIO credentials missing")

        if cls.WEBHOOK_ALERT_ENABLED and not any([
            cls.DISCORD_WEBHOOK_URL,
            cls.SLACK_WEBHOOK_URL,
            cls.CUSTOM_WEBHOOK_URL
        ]):
            warnings.append("Webhooks enabled but no webhook URLs configured")

        return len(warnings) == 0, warnings


# ── Email Templates ────────────────────────────────────────────────────────
class EmailTemplate:
    """Generate branded HTML email templates."""

    @staticmethod
    def get_brand_colors(brand: str) -> Dict[str, str]:
        """Get brand-specific color palette."""
        if brand == "kids":
            return {
                "primary": "#FF6B4A",    # Coral
                "secondary": "#FFB3A0",  # Light coral
                "background": "#FFF9EF", # Warm white
                "text": "#1A1208",       # Dark brown
                "accent": "#FFE0D6",     # Pale coral
            }
        else:  # gourmet
            return {
                "primary": "#C9A84C",    # Gold
                "secondary": "#9E7E2B",  # Dark gold
                "background": "#0D0D0D", # Near black
                "text": "#F5F0E8",       # Cream
                "accent": "#2A2A2A",     # Dark gray
            }

    @staticmethod
    def get_brand_name(brand: str) -> str:
        """Get display name for brand."""
        return "Don Quijote Kids" if brand == "kids" else "Don Quijote Gourmet"

    @staticmethod
    def render_order_summary(order: dict, brand: str = "gourmet") -> str:
        """Generate complete order email HTML."""
        colors = EmailTemplate.get_brand_colors(brand)
        brand_name = EmailTemplate.get_brand_name(brand)

        # Product table
        products_html = "".join(
            f"""<tr style="border-bottom:1px solid {colors['accent']};">
                <td style="padding:8px 0;text-align:left;">{item['name']}</td>
                <td style="padding:8px 0;text-align:center;">×{item['qty']}</td>
                <td style="padding:8px 0;text-align:right;font-weight:500;">€{item['price']*item['qty']:.2f}</td>
              </tr>"""
            for item in order.get("items", [])
        )

        # Quick action buttons
        action_buttons = f"""
        <table style="width:100%;margin-top:20px;">
          <tr>
            <td style="padding-right:10px;">
              <a href="https://dashboard.stripe.com/search?query={order.get('stripe_id')}"
                 style="display:inline-block;padding:10px 20px;background:{colors['primary']};color:{colors['background']};text-decoration:none;border-radius:4px;font-weight:bold;font-size:13px;">
                View in Stripe
              </a>
            </td>
            <td>
              <a href="mailto:{order.get('email')}"
                 style="display:inline-block;padding:10px 20px;background:{colors['accent']};color:{colors['text']};text-decoration:none;border-radius:4px;font-weight:bold;font-size:13px;">
                Email Customer
              </a>
            </td>
          </tr>
        </table>
        """

        html = f"""
        <div style="font-family:'Segoe UI', Arial, sans-serif;max-width:650px;margin:0 auto;background:{colors['background']};color:{colors['text']};padding:40px 30px;border-radius:6px;">

          <!-- Header -->
          <div style="text-align:center;margin-bottom:30px;padding-bottom:20px;border-bottom:2px solid {colors['primary']};">
            <h1 style="color:{colors['primary']};font-size:28px;margin:0;letter-spacing:1px;text-transform:uppercase;font-weight:300;">
              ✓ Nuevo Pedido
            </h1>
            <p style="color:{colors['primary']};font-size:13px;margin:8px 0 0 0;letter-spacing:2px;text-transform:uppercase;">{brand_name}</p>
          </div>

          <!-- Order Total - Prominent -->
          <div style="background:{colors['accent']};padding:20px;border-radius:4px;margin-bottom:25px;text-align:center;">
            <p style="margin:0;color:#999;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Total del Pedido</p>
            <h2 style="margin:0;color:{colors['primary']};font-size:32px;font-weight:bold;">€{order.get('total', 0):.2f}</h2>
          </div>

          <!-- Customer Summary Card -->
          <div style="background:{colors['accent']};padding:20px;border-left:4px solid {colors['primary']};margin-bottom:25px;border-radius:2px;">
            <h3 style="color:{colors['primary']};font-size:11px;margin:0 0 12px 0;letter-spacing:2px;text-transform:uppercase;font-weight:700;">Cliente</h3>
            <p style="margin:0 0 8px 0;font-size:14px;"><strong>{order.get('name', 'N/A')}</strong></p>
            <p style="margin:0 0 4px 0;font-size:13px;color:#999;">{order.get('email', '')}</p>
            <p style="margin:0;font-size:13px;color:#999;">📱 {order.get('phone', '')}</p>
          </div>

          <!-- Shipping Address -->
          <div style="background:{colors['accent']};padding:20px;border-left:4px solid {colors['primary']};margin-bottom:25px;border-radius:2px;">
            <h3 style="color:{colors['primary']};font-size:11px;margin:0 0 12px 0;letter-spacing:2px;text-transform:uppercase;font-weight:700;">Envío</h3>
            <p style="margin:0 0 4px 0;font-size:13px;"><strong>{order.get('address', '')}</strong></p>
            <p style="margin:0;font-size:13px;color:#999;">{order.get('zip', '')} {order.get('city', '')}, {order.get('country', '')}</p>
          </div>

          <!-- Products Table -->
          <div style="margin-bottom:25px;">
            <h3 style="color:{colors['primary']};font-size:11px;margin:0 0 15px 0;letter-spacing:2px;text-transform:uppercase;font-weight:700;">Productos</h3>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
              <thead>
                <tr style="border-bottom:2px solid {colors['primary']};">
                  <th style="padding:10px 0;text-align:left;font-weight:600;color:{colors['primary']};font-size:11px;text-transform:uppercase;letter-spacing:1px;">Producto</th>
                  <th style="padding:10px 0;text-align:center;font-weight:600;color:{colors['primary']};font-size:11px;text-transform:uppercase;letter-spacing:1px;">Cant.</th>
                  <th style="padding:10px 0;text-align:right;font-weight:600;color:{colors['primary']};font-size:11px;text-transform:uppercase;letter-spacing:1px;">Precio</th>
                </tr>
              </thead>
              <tbody>
                {products_html}
              </tbody>
            </table>

            <!-- Totals -->
            <table style="width:100%;margin-top:15px;border-collapse:collapse;">
              <tr>
                <td style="text-align:right;padding:8px 0;color:#999;border-top:1px solid {colors['accent']};">Subtotal:</td>
                <td style="text-align:right;padding:8px 0;color:#999;border-top:1px solid {colors['accent']};width:80px;">€{order.get('subtotal', 0):.2f}</td>
              </tr>
              <tr>
                <td style="text-align:right;padding:8px 0;color:#999;">Envío:</td>
                <td style="text-align:right;padding:8px 0;color:#999;width:80px;">€{order.get('shipping', 0):.2f}</td>
              </tr>
              <tr style="border-top:2px solid {colors['primary']};">
                <td style="text-align:right;padding:12px 0;font-weight:bold;color:{colors['primary']};font-size:16px;">Total:</td>
                <td style="text-align:right;padding:12px 0;font-weight:bold;color:{colors['primary']};font-size:16px;width:80px;">€{order.get('total', 0):.2f}</td>
              </tr>
            </table>
          </div>

          <!-- Action Buttons -->
          {action_buttons}

          <!-- Footer -->
          <div style="margin-top:30px;padding-top:20px;border-top:1px solid {colors['accent']};text-align:center;color:#999;font-size:11px;">
            <p style="margin:0 0 4px 0;">
              <strong>Stripe ID:</strong> <code style="background:{colors['accent']};padding:2px 6px;border-radius:2px;font-family:monospace;">{order.get('stripe_id', '')}</code>
            </p>
            <p style="margin:0 0 4px 0;"><strong>Brand:</strong> {brand.upper()}</p>
            <p style="margin:0;"><strong>Timestamp:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S UTC')}</p>
          </div>

        </div>
        """
        return html


# ── Email Alerts ───────────────────────────────────────────────────────────
class EmailAlert:
    """Handle email notifications with multiple recipients and brand templates."""

    @staticmethod
    def get_recipients(order: dict, brand: str = "gourmet") -> List[str]:
        """
        Determine recipient list based on brand and configuration.
        Returns list of email addresses.
        """
        recipients = []

        if brand == "kids":
            # Kids brand: primary Kids email + secondary option
            recipients.append(AlertConfig.KIDS_NOTIFY_EMAIL)
            if AlertConfig.ALERT_EMAIL_SECONDARY:
                recipients.append(AlertConfig.ALERT_EMAIL_SECONDARY)
        else:
            # Gourmet: primary email
            recipients.append(AlertConfig.ALERT_EMAIL_PRIMARY)
            # Add secondary if configured
            if AlertConfig.ALERT_EMAIL_SECONDARY:
                recipients.append(AlertConfig.ALERT_EMAIL_SECONDARY)

        # Add backup if configured
        if AlertConfig.ALERT_EMAIL_BACKUP:
            recipients.append(AlertConfig.ALERT_EMAIL_BACKUP)

        # Remove duplicates and empty strings
        return list(set(r for r in recipients if r))

    @staticmethod
    def _send_via_resend(recipients, subject, html_content, from_email) -> Tuple[bool, str]:
        """Send email via Resend HTTP API (Railway-compatible, no SMTP ports needed)."""
        api_key = AlertConfig.RESEND_API_KEY
        for recipient in recipients:
            try:
                resp = requests.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"from": from_email, "to": recipient, "subject": subject, "html": html_content},
                    timeout=15,
                )
                if resp.status_code not in (200, 201):
                    return False, f"Resend API error {resp.status_code}: {resp.text}"
                logger.info(f"Email sent via Resend to {recipient}")
            except Exception as e:
                return False, f"Resend request failed: {e}"
        return True, f"Email sent via Resend to {len(recipients)} recipient(s)"

    @staticmethod
    def send(order: dict, brand: str = "gourmet") -> Tuple[bool, str]:
        """
        Send email notification to configured recipients.
        Uses Resend HTTP API if configured, falls back to SMTP.
        Returns (success: bool, message: str)
        """
        recipients = EmailAlert.get_recipients(order, brand)
        if not recipients:
            msg = "No email recipients configured"
            logger.warning(msg)
            return False, msg

        subject = f"🛒 Nuevo pedido {brand.upper()} — {order.get('name', 'Unknown')} • €{order.get('total', 0):.2f}"

        try:
            html_content = EmailTemplate.render_order_summary(order, brand)
        except Exception as e:
            return False, f"Failed to render email template: {e}"

        # ── Path 1: Resend HTTP API (preferred — works on Railway) ──────────
        if AlertConfig.RESEND_API_KEY:
            from_email = f"Don Quijote {brand.capitalize()} <hello@donquijotegourmet.com>"
            return EmailAlert._send_via_resend(recipients, subject, html_content, from_email)

        # ── Path 2: SMTP fallback ────────────────────────────────────────────
        if brand == "kids":
            smtp_user = AlertConfig.KIDS_SMTP_USER
            smtp_pass = AlertConfig.KIDS_SMTP_PASSWORD
        else:
            smtp_user = AlertConfig.GOURMET_SMTP_USER
            smtp_pass = AlertConfig.GOURMET_SMTP_PASSWORD

        if not smtp_pass:
            msg = f"No email method configured for {brand} (set RESEND_API_KEY or SMTP password)"
            logger.warning(msg)
            return False, msg

        try:
            mime_msg = MIMEMultipart("alternative")
            mime_msg["Subject"] = subject
            mime_msg["From"] = smtp_user
            mime_msg["To"] = ", ".join(recipients)
            mime_msg.attach(MIMEText(html_content, "html"))

            port = AlertConfig.SMTP_PORT
            context = ssl.create_default_context()
            if port == 465:
                smtp_conn = smtplib.SMTP_SSL(AlertConfig.SMTP_HOST, port, context=context, timeout=15)
            else:
                smtp_conn = smtplib.SMTP(AlertConfig.SMTP_HOST, port, timeout=15)
                smtp_conn.starttls(context=context)

            with smtp_conn as server:
                server.login(smtp_user, smtp_pass)
                for recipient in recipients:
                    try:
                        server.sendmail(smtp_user, recipient, mime_msg.as_string())
                        logger.info(f"Email sent to {recipient} for order {order.get('stripe_id')}")
                    except Exception as e:
                        logger.error(f"Failed to send email to {recipient}: {e}")

            success_msg = f"Email alert sent to {len(recipients)} recipient(s)"
            logger.info(success_msg)
            return True, success_msg

        except Exception as e:
            error_msg = f"Email alert failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# ── SMS Alerts ─────────────────────────────────────────────────────────────
class SMSAlert:
    """Handle SMS notifications via Twilio (optional)."""

    @staticmethod
    def should_send(order: dict) -> bool:
        """Check if SMS should be sent based on order amount."""
        if not AlertConfig.SMS_ALERT_ENABLED:
            return False
        if order.get("total", 0) < AlertConfig.SMS_ALERT_MIN_AMOUNT:
            logger.info(f"Order {order.get('stripe_id')} below SMS threshold (€{AlertConfig.SMS_ALERT_MIN_AMOUNT})")
            return False
        return True

    @staticmethod
    def send(order: dict, brand: str = "gourmet") -> Tuple[bool, str]:
        """
        Send SMS alert via Twilio.
        Returns (success: bool, message: str)
        """
        if not AlertConfig.SMS_ALERT_ENABLED:
            return False, "SMS alerts not enabled"

        if not AlertConfig.should_send(order):
            return False, f"Order amount below SMS threshold (€{AlertConfig.SMS_ALERT_MIN_AMOUNT})"

        if not (AlertConfig.TWILIO_ACCOUNT_SID and AlertConfig.TWILIO_AUTH_TOKEN):
            msg = "Twilio credentials not configured"
            logger.warning(msg)
            return False, msg

        try:
            from twilio.rest import Client

            client = Client(AlertConfig.TWILIO_ACCOUNT_SID, AlertConfig.TWILIO_AUTH_TOKEN)

            # Format message (keep it short for SMS)
            brand_emoji = "🧒" if brand == "kids" else "🍽"
            message_text = f"{brand_emoji} ¡Nuevo pedido! €{order.get('total', 0):.0f} de {order.get('name', 'Cliente')} • Stripe: {order.get('stripe_id', '')[:8]}"

            message = client.messages.create(
                body=message_text,
                from_=AlertConfig.TWILIO_PHONE,
                to=AlertConfig.TWILIO_PHONE  # Send to admin phone
            )

            success_msg = f"SMS alert sent (SID: {message.sid})"
            logger.info(success_msg)
            return True, success_msg

        except ImportError:
            msg = "Twilio SDK not installed (pip install twilio)"
            logger.warning(msg)
            return False, msg
        except Exception as e:
            error_msg = f"SMS alert failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# ── Webhook Alerts ────────────────────────────────────────────────────────
class WebhookAlert:
    """Send alerts to Discord, Slack, or custom webhooks."""

    @staticmethod
    def build_discord_payload(order: dict, brand: str = "gourmet") -> dict:
        """Build Discord embed payload."""
        colors = EmailTemplate.get_brand_colors(brand)
        color_int = int(colors['primary'].lstrip('#'), 16)

        return {
            "embeds": [
                {
                    "title": f"🛒 New Order — {brand.upper()}",
                    "description": f"**Customer:** {order.get('name', 'Unknown')}\n**Email:** {order.get('email', 'N/A')}\n**Phone:** {order.get('phone', 'N/A')}",
                    "color": color_int,
                    "fields": [
                        {
                            "name": "Shipping Address",
                            "value": f"{order.get('address', '')}\n{order.get('zip', '')} {order.get('city', '')}, {order.get('country', '')}",
                            "inline": False
                        },
                        {
                            "name": "Order Total",
                            "value": f"€{order.get('total', 0):.2f}",
                            "inline": True
                        },
                        {
                            "name": "Subtotal",
                            "value": f"€{order.get('subtotal', 0):.2f}",
                            "inline": True
                        },
                        {
                            "name": "Shipping",
                            "value": f"€{order.get('shipping', 0):.2f}",
                            "inline": True
                        },
                        {
                            "name": "Products",
                            "value": "\n".join(
                                f"• {item['name']} ×{item['qty']} (€{item['price']*item['qty']:.2f})"
                                for item in order.get("items", [])
                            ) or "No items",
                            "inline": False
                        },
                        {
                            "name": "Stripe ID",
                            "value": f"`{order.get('stripe_id', 'N/A')}`",
                            "inline": False
                        }
                    ],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }

    @staticmethod
    def build_slack_payload(order: dict, brand: str = "gourmet") -> dict:
        """Build Slack message payload."""
        colors = EmailTemplate.get_brand_colors(brand)

        return {
            "text": f"🛒 New Order: {order.get('name', 'Unknown')} • €{order.get('total', 0):.2f}",
            "attachments": [
                {
                    "color": colors['primary'],
                    "fields": [
                        {
                            "title": "Customer",
                            "value": f"{order.get('name', 'Unknown')}\n{order.get('email', 'N/A')}\n{order.get('phone', 'N/A')}",
                            "short": False
                        },
                        {
                            "title": "Shipping Address",
                            "value": f"{order.get('address', '')}\n{order.get('zip', '')} {order.get('city', '')}, {order.get('country', '')}",
                            "short": False
                        },
                        {
                            "title": "Order Total",
                            "value": f"€{order.get('total', 0):.2f}",
                            "short": True
                        },
                        {
                            "title": "Subtotal",
                            "value": f"€{order.get('subtotal', 0):.2f}",
                            "short": True
                        },
                        {
                            "title": "Products",
                            "value": "\n".join(
                                f"• {item['name']} ×{item['qty']} (€{item['price']*item['qty']:.2f})"
                                for item in order.get("items", [])
                            ) or "No items",
                            "short": False
                        },
                        {
                            "title": "Stripe ID",
                            "value": order.get('stripe_id', 'N/A'),
                            "short": True
                        },
                        {
                            "title": "Brand",
                            "value": brand.upper(),
                            "short": True
                        }
                    ],
                    "footer": "Don Quijote Gourmet & Kids",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }

    @staticmethod
    def send_discord(order: dict, brand: str = "gourmet") -> Tuple[bool, str]:
        """Send alert to Discord webhook."""
        if not AlertConfig.DISCORD_WEBHOOK_URL:
            return False, "Discord webhook not configured"

        try:
            payload = WebhookAlert.build_discord_payload(order, brand)
            response = requests.post(AlertConfig.DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Discord alert sent for order {order.get('stripe_id')}")
            return True, "Discord alert sent"
        except Exception as e:
            error_msg = f"Discord alert failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_slack(order: dict, brand: str = "gourmet") -> Tuple[bool, str]:
        """Send alert to Slack webhook."""
        if not AlertConfig.SLACK_WEBHOOK_URL:
            return False, "Slack webhook not configured"

        try:
            payload = WebhookAlert.build_slack_payload(order, brand)
            response = requests.post(AlertConfig.SLACK_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack alert sent for order {order.get('stripe_id')}")
            return True, "Slack alert sent"
        except Exception as e:
            error_msg = f"Slack alert failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_custom(order: dict, brand: str = "gourmet") -> Tuple[bool, str]:
        """Send alert to custom webhook endpoint."""
        if not AlertConfig.CUSTOM_WEBHOOK_URL:
            return False, "Custom webhook not configured"

        try:
            payload = {
                "event": "order.completed",
                "brand": brand,
                "order": {
                    "stripe_id": order.get("stripe_id"),
                    "customer_name": order.get("name"),
                    "customer_email": order.get("email"),
                    "customer_phone": order.get("phone"),
                    "total": order.get("total"),
                    "subtotal": order.get("subtotal"),
                    "shipping": order.get("shipping"),
                    "items": order.get("items"),
                    "address": order.get("address"),
                    "city": order.get("city"),
                    "zip": order.get("zip"),
                    "country": order.get("country"),
                    "timestamp": datetime.now().isoformat()
                }
            }
            response = requests.post(AlertConfig.CUSTOM_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Custom webhook alert sent for order {order.get('stripe_id')}")
            return True, "Custom webhook alert sent"
        except Exception as e:
            error_msg = f"Custom webhook alert failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_all(order: dict, brand: str = "gourmet") -> Dict[str, Tuple[bool, str]]:
        """Send to all configured webhooks."""
        results = {}
        if AlertConfig.WEBHOOK_ALERT_ENABLED:
            results["discord"] = WebhookAlert.send_discord(order, brand)
            results["slack"] = WebhookAlert.send_slack(order, brand)
            results["custom"] = WebhookAlert.send_custom(order, brand)
        return results


# ── Alert Logging ──────────────────────────────────────────────────────────
class AlertLogger:
    """Log all alert activity for audit trail and debugging."""

    @staticmethod
    def log_alert(order: dict, alert_type: str, success: bool, message: str, brand: str = "gourmet"):
        """Log alert attempt to file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "order_id": order.get("stripe_id"),
                "brand": brand,
                "alert_type": alert_type,
                "customer": order.get("name"),
                "total": order.get("total"),
                "success": success,
                "message": message
            }

            with open(AlertConfig.ALERT_LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

            logger.info(f"Alert logged: {alert_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")

    @staticmethod
    def get_recent_alerts(limit: int = 50) -> List[dict]:
        """Read recent alert logs."""
        try:
            alerts = []
            with open(AlertConfig.ALERT_LOG_FILE, "r") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        alerts.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return alerts
        except FileNotFoundError:
            return []


# ── Main Alert Orchestrator ───────────────────────────────────────────────
class AlertOrchestrator:
    """
    Coordinate all alert channels with proper error handling and fallbacks.
    Ensures at least one alert channel succeeds.
    """

    @staticmethod
    def send_all_alerts(order: dict, brand: str = "gourmet") -> Dict[str, any]:
        """
        Send order notification across all enabled channels.
        Returns summary of all alert attempts.
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "order_id": order.get("stripe_id"),
            "brand": brand,
            "alerts": {}
        }

        # Email (primary channel - usually always enabled)
        success, msg = EmailAlert.send(order, brand)
        results["alerts"]["email"] = {
            "enabled": True,
            "success": success,
            "message": msg
        }
        AlertLogger.log_alert(order, "email", success, msg, brand)

        # SMS (optional)
        if AlertConfig.SMS_ALERT_ENABLED and SMSAlert.should_send(order):
            success, msg = SMSAlert.send(order, brand)
            results["alerts"]["sms"] = {
                "enabled": True,
                "success": success,
                "message": msg
            }
            AlertLogger.log_alert(order, "sms", success, msg, brand)

        # Webhooks (optional)
        if AlertConfig.WEBHOOK_ALERT_ENABLED:
            webhook_results = WebhookAlert.send_all(order, brand)
            for webhook_type, (success, msg) in webhook_results.items():
                if success or msg != f"{webhook_type} webhook not configured":
                    results["alerts"][f"webhook_{webhook_type}"] = {
                        "enabled": True,
                        "success": success,
                        "message": msg
                    }
                    AlertLogger.log_alert(order, f"webhook_{webhook_type}", success, msg, brand)

        # Summary
        successful_channels = sum(1 for a in results["alerts"].values() if a["success"])
        results["summary"] = {
            "total_channels": len(results["alerts"]),
            "successful_channels": successful_channels,
            "overall_success": successful_channels > 0
        }

        if results["summary"]["overall_success"]:
            logger.info(f"Alerts sent successfully: {successful_channels}/{len(results['alerts'])} channels")
        else:
            logger.error(f"All alert channels failed for order {order.get('stripe_id')}")

        return results


# ── Admin Dashboard Data ───────────────────────────────────────────────────
class AdminDashboard:
    """Provide data for admin dashboard."""

    # In-memory order store (for demo - replace with database in production)
    _orders = []

    @staticmethod
    def record_order(order: dict, brand: str = "gourmet"):
        """Store order for dashboard."""
        dashboard_entry = {
            "timestamp": datetime.now().isoformat(),
            "stripe_id": order.get("stripe_id"),
            "brand": brand,
            "customer_name": order.get("name"),
            "customer_email": order.get("email"),
            "total": order.get("total"),
            "items_count": len(order.get("items", []))
        }
        AdminDashboard._orders.append(dashboard_entry)
        # Keep only last 100 orders in memory
        AdminDashboard._orders = AdminDashboard._orders[-100:]

    @staticmethod
    def get_recent_orders(limit: int = 10) -> List[dict]:
        """Get recent orders."""
        return AdminDashboard._orders[-limit:][::-1]  # Reverse for newest first

    @staticmethod
    def get_stats() -> dict:
        """Get dashboard statistics."""
        orders = AdminDashboard._orders
        if not orders:
            return {
                "total_orders": 0,
                "total_revenue": 0.0,
                "avg_order_value": 0.0,
                "gourmet_orders": 0,
                "kids_orders": 0,
                "gourmet_revenue": 0.0,
                "kids_revenue": 0.0
            }

        gourmet = [o for o in orders if o.get("brand") == "gourmet"]
        kids = [o for o in orders if o.get("brand") == "kids"]

        total_revenue = sum(o.get("total", 0) for o in orders)

        return {
            "total_orders": len(orders),
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(total_revenue / len(orders), 2) if orders else 0,
            "gourmet_orders": len(gourmet),
            "kids_orders": len(kids),
            "gourmet_revenue": round(sum(o.get("total", 0) for o in gourmet), 2),
            "kids_revenue": round(sum(o.get("total", 0) for o in kids), 2)
        }
