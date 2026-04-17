# Quick Reference Card — Multi-Channel Alert System

## Files at a Glance

| File | Purpose | Size |
|------|---------|------|
| `alerts.py` | Core alert system | 450 lines |
| `server.py` | Flask app (updated) | 415 lines |
| `ALERT_SYSTEM.md` | Complete documentation | 1000+ lines |
| `SETUP_GUIDE.md` | Quick start guide | 200+ lines |
| `UPGRADE_GUIDE.md` | Migration guide | 200+ lines |
| `.env.example` | Environment template | 100+ lines |

## Essential Environment Variables

```bash
# Email (REQUIRED)
GMAIL_USER=tarapachecovr@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
KIDS_NOTIFY_EMAIL=hola@donquijotekids.com

# Admin (REQUIRED)
ADMIN_API_KEY=your_32_char_random_key

# SMS (Optional)
SMS_ALERT_ENABLED=false
TWILIO_ACCOUNT_SID=ACxxxxxx...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE=+1234567890

# Webhooks (Optional)
WEBHOOK_ALERT_ENABLED=false
DISCORD_WEBHOOK_URL=https://...
SLACK_WEBHOOK_URL=https://...
CUSTOM_WEBHOOK_URL=https://...
```

## Admin API Endpoints

All require: `-H "Authorization: Bearer $ADMIN_API_KEY"`

| Endpoint | Method | Purpose | Params |
|----------|--------|---------|--------|
| `/admin/orders` | GET | Recent orders | `?limit=10` |
| `/admin/stats` | GET | Revenue/stats | — |
| `/admin/alerts` | GET | Alert history | `?limit=50` |
| `/admin/alerts/config` | GET | System status | — |
| `/health` | GET | Server health | — |

## Quick Test Commands

```bash
# Health check
curl https://your-server/health

# View recent orders
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/orders?limit=5

# Check statistics
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats

# View alert history
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=20

# Check configuration
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config
```

## Alert Channels

### Email (Always Enabled)
- Recipients: ALERT_EMAIL_PRIMARY + optional secondary/backup
- Kids brand: KIDS_NOTIFY_EMAIL (overrides primary)
- Template: Branded HTML with action buttons
- Status: Logged and queryable

### SMS (Optional)
- Platform: Twilio
- Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE
- Threshold: Only for orders >= SMS_ALERT_MIN_AMOUNT
- Message: Short format with order total and customer
- Status: Logged and queryable

### Discord (Optional)
- Format: Embedded message
- Color: Brand-specific (gold for Gourmet, coral for Kids)
- Content: Customer, address, products, totals
- Status: Logged and queryable

### Slack (Optional)
- Format: Message with attachments
- Color: Brand-specific
- Content: Customer, address, products, totals
- Status: Logged and queryable

### Custom Webhook (Optional)
- Format: JSON payload
- Content: Complete order data
- Timing: HTTP POST with 10s timeout
- Status: Logged and queryable

## Authentication

All admin endpoints protected:

```bash
# Correct format
curl -H "Authorization: Bearer YOUR_ADMIN_API_KEY" https://...

# Alternative format
curl -H "Authorization: YOUR_ADMIN_API_KEY" https://...

# Wrong format (fails)
curl -H "api-key: YOUR_ADMIN_API_KEY" https://...
```

## Alert Log Format

Location: `ALERT_LOG_FILE` (default: `/tmp/don_quijote_alerts.log`)

```json
{
  "timestamp": "2026-04-16T15:30:05.123456",
  "order_id": "cs_live_...",
  "brand": "gourmet",
  "alert_type": "email",
  "customer": "John Doe",
  "total": 99.95,
  "success": true,
  "message": "Email alert sent to 2 recipient(s)"
}
```

Query with:
```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=100 | \
     jq '.alerts[] | select(.alert_type == "email")'
```

## Deployment Checklist

- [ ] Updated `.env` with all required variables
- [ ] Generated strong `ADMIN_API_KEY`
- [ ] Verified Gmail App Password (16 chars)
- [ ] Tested locally: `python server.py`
- [ ] Made test order and received email
- [ ] Pushed to git: `git add -A && git commit -m "..."`
- [ ] Deployed to Railway: `railway up`
- [ ] Verified health: `curl https://your-server/health`
- [ ] Tested admin dashboard with API key
- [ ] Optional features enabled and tested

## Troubleshooting

### Email Not Working
```bash
# 1. Check if GMAIL_APP_PASSWORD is correct (16 chars)
echo $GMAIL_APP_PASSWORD | wc -c  # Should be 17 (16 + newline)

# 2. Check recent alert log
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=5 | \
     jq '.alerts[] | select(.alert_type == "email")'

# 3. Verify email is configured
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config | \
     jq '.config.email_enabled'
```

### SMS Not Working
```bash
# 1. Check if enabled
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config | \
     jq '.config.sms_enabled'

# 2. Check if order amount meets threshold
# Make order > SMS_ALERT_MIN_AMOUNT

# 3. Verify Twilio credentials
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=100 | \
     jq '.alerts[] | select(.alert_type == "sms")'
```

### Webhooks Not Firing
```bash
# 1. Check if enabled
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config | \
     jq '.config.webhooks_enabled'

# 2. Check webhook URL is valid
curl -X POST $DISCORD_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"embeds":[{"title":"Test"}]}'

# 3. View webhook attempt logs
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=100 | \
     jq '.alerts[] | select(.alert_type | contains("webhook"))'
```

### API Key Issues
```bash
# Generate new key
NEW_KEY=$(openssl rand -base64 32)
echo $NEW_KEY
railway env ADMIN_API_KEY "$NEW_KEY"

# Test with new key
curl -H "Authorization: Bearer $NEW_KEY" \
     https://your-server/admin/orders
```

## Platform-Specific Setup

### Discord Webhook
1. Right-click channel → Integrations → Webhooks
2. New Webhook → Copy URL → Paste in `DISCORD_WEBHOOK_URL`
3. Test: Make order > check channel

### Slack Webhook
1. https://api.slack.com/messaging/webhooks
2. Create New App → From scratch → Name → Select workspace
3. Enable Incoming Webhooks → Add New → Select channel
4. Copy URL → Paste in `SLACK_WEBHOOK_URL`
5. Test: Make order → check channel

### Twilio SMS
1. https://www.twilio.com/console
2. Account SID → Copy
3. Auth Token → Copy
4. Buy/verify phone number
5. Paste credentials in `.env`
6. Test: Make order > €50 → check SMS

## Production Defaults

```bash
# Email: REQUIRED and always enabled
GMAIL_USER=tarapachecovr@gmail.com
GMAIL_APP_PASSWORD=<generated>
ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
KIDS_NOTIFY_EMAIL=hola@donquijotekids.com

# SMS: disabled by default
SMS_ALERT_ENABLED=false

# Webhooks: disabled by default
WEBHOOK_ALERT_ENABLED=false

# Admin: protected
ADMIN_API_KEY=<randomly generated>

# Logging: to /tmp by default
ALERT_LOG_FILE=/tmp/don_quijote_alerts.log
```

## Response Examples

### GET /admin/orders
```json
{
  "status": "ok",
  "count": 3,
  "orders": [
    {
      "timestamp": "2026-04-16T15:30:00...",
      "stripe_id": "cs_live_abc123",
      "brand": "gourmet",
      "customer_name": "John Doe",
      "customer_email": "john@example.com",
      "total": 99.95,
      "items_count": 2
    }
  ]
}
```

### GET /admin/stats
```json
{
  "status": "ok",
  "stats": {
    "total_orders": 42,
    "total_revenue": 4215.50,
    "avg_order_value": 100.37,
    "gourmet_orders": 28,
    "kids_orders": 14,
    "gourmet_revenue": 2850.00,
    "kids_revenue": 1365.50
  }
}
```

### GET /admin/alerts/config
```json
{
  "status": "ok",
  "valid": true,
  "warnings": [],
  "config": {
    "email_enabled": true,
    "email_primary": "tarapachecovr@gmail.com",
    "email_secondary": false,
    "email_backup": false,
    "sms_enabled": false,
    "webhooks_enabled": false,
    "discord_configured": false,
    "slack_configured": false
  }
}
```

## Common Commands

```bash
# Generate admin API key
openssl rand -base64 32

# Check server health
curl https://your-server/health | jq .

# Export admin key for testing
export ADMIN_API_KEY="your_key_here"

# View today's orders
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats | jq .

# Find failed alerts
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=500 | \
     jq '.alerts[] | select(.success == false)'

# Count orders by brand
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats | \
     jq '.stats | {gourmet: .gourmet_orders, kids: .kids_orders}'

# Check total revenue
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats | \
     jq '.stats.total_revenue'
```

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `AlertConfig` | alerts.py | Configuration management |
| `EmailTemplate` | alerts.py | HTML email generation |
| `EmailAlert` | alerts.py | Email sending |
| `SMSAlert` | alerts.py | SMS via Twilio |
| `WebhookAlert` | alerts.py | Discord/Slack/custom |
| `AlertLogger` | alerts.py | Audit logging |
| `AlertOrchestrator` | alerts.py | Coordinate all channels |
| `AdminDashboard` | alerts.py | Order tracking |

## Support Resources

1. **Setup**: See `SETUP_GUIDE.md` (5-minute quick start)
2. **Reference**: See `ALERT_SYSTEM.md` (complete docs)
3. **Migration**: See `UPGRADE_GUIDE.md` (step-by-step upgrade)
4. **Debugging**: Use `/admin/alerts` endpoint to view logs
5. **Status**: Use `/admin/alerts/config` to check configuration

---

**Version**: 2.0.0 (2026-04-16)
**Status**: Production Ready
**Breaking Changes**: None
