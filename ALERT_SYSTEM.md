# Multi-Channel Alert System Documentation

## Overview

The enhanced order notification system provides multiple alert channels for order completions:

- **Email** (Primary): Multiple branded recipients, rich HTML templates
- **SMS** (Optional): Twilio integration for urgent alerts
- **Webhooks** (Optional): Discord, Slack, custom endpoints
- **Admin Dashboard**: Real-time order tracking and statistics
- **Alert Logging**: Complete audit trail of all notifications

## Architecture

### New Files

```
server/
├── alerts.py                 # Core alert system (NEW)
├── server.py                 # Updated Flask app
└── ALERT_SYSTEM.md          # This documentation
```

### Classes Overview

**alerts.py** contains:

- `AlertConfig`: Load and validate configuration from env vars
- `EmailTemplate`: Generate branded HTML email templates
- `EmailAlert`: Send emails to multiple recipients
- `SMSAlert`: Send SMS via Twilio (optional)
- `WebhookAlert`: Send to Discord/Slack/custom endpoints
- `AlertLogger`: Audit trail of all alert attempts
- `AlertOrchestrator`: Coordinate all channels with error handling
- `AdminDashboard`: Order tracking and statistics

## Environment Variables

### Email Configuration

```bash
# Gmail SMTP credentials
GMAIL_USER="tarapachecovr@gmail.com"
GMAIL_APP_PASSWORD="your_16_char_app_password"

# Alert recipients
ALERT_EMAIL_PRIMARY="tarapachecovr@gmail.com"          # Primary (Gourmet)
ALERT_EMAIL_SECONDARY="optional@example.com"          # Optional secondary
ALERT_EMAIL_BACKUP="backup@example.com"               # Fallback recipient
KIDS_NOTIFY_EMAIL="hola@donquijotekids.com"          # Kids brand (overrides primary)
```

### SMS Configuration (Optional)

```bash
SMS_ALERT_ENABLED="false"                             # Enable SMS alerts
TWILIO_ACCOUNT_SID="your_account_sid"
TWILIO_AUTH_TOKEN="your_auth_token"
TWILIO_PHONE="+1234567890"                           # Your Twilio number
SMS_ALERT_MIN_AMOUNT="50"                            # Only alert for orders > €50
```

### Webhook Configuration (Optional)

```bash
WEBHOOK_ALERT_ENABLED="false"                         # Enable webhooks

# Discord webhook (for Discord server integration)
DISCORD_WEBHOOK_URL="https://discordapp.com/api/webhooks/..."

# Slack webhook (for Slack workspace integration)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Custom HTTP endpoint
CUSTOM_WEBHOOK_URL="https://your-api.example.com/orders"
```

### Admin Dashboard

```bash
ADMIN_API_KEY="your_secret_admin_key"                 # Protect admin endpoints
ADMIN_ALERT_ENABLED="true"                            # Enable dashboard
ALERT_LOG_FILE="/tmp/don_quijote_alerts.log"         # Alert audit log location
```

## Email Templates

### Gourmet Brand
- **Primary Color**: Gold (#C9A84C)
- **Background**: Near black (#0D0D0D)
- **Text**: Cream (#F5F0E8)
- **Theme**: Luxury, premium

### Kids Brand
- **Primary Color**: Coral (#FF6B4A)
- **Background**: Warm white (#FFF9EF)
- **Text**: Dark brown (#1A1208)
- **Theme**: Playful, bright

### Template Features

Each email includes:
- Brand-specific header with logo styling
- Prominent order total with accent background
- Customer summary card (name, email, phone)
- Shipping address formatted nicely
- Product breakdown table (name, qty, price)
- Subtotal + Shipping + Total calculation
- Quick action buttons (View in Stripe, Email Customer)
- Order metadata (Stripe ID, timestamp, brand)

## API Endpoints

### Admin Dashboard (Protected)

All admin endpoints require `Authorization` header:

```bash
curl -H "Authorization: Bearer your_admin_api_key" \
     https://your-server/admin/orders
```

#### GET /admin/orders

Get recent orders.

**Query Parameters:**
- `limit` (int, default 10): Number of orders to return

**Response:**
```json
{
  "status": "ok",
  "count": 10,
  "orders": [
    {
      "timestamp": "2026-04-16T15:30:00...",
      "stripe_id": "cs_live_...",
      "brand": "gourmet",
      "customer_name": "John Doe",
      "customer_email": "john@example.com",
      "total": 99.95,
      "items_count": 3
    }
  ]
}
```

#### GET /admin/stats

Get overall statistics.

**Response:**
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

#### GET /admin/alerts

Get alert log entries.

**Query Parameters:**
- `limit` (int, default 50): Number of log entries to return

**Response:**
```json
{
  "status": "ok",
  "count": 50,
  "alerts": [
    {
      "timestamp": "2026-04-16T15:30:05...",
      "order_id": "cs_live_...",
      "brand": "gourmet",
      "alert_type": "email",
      "customer": "John Doe",
      "total": 99.95,
      "success": true,
      "message": "Email alert sent to 2 recipient(s)"
    }
  ]
}
```

#### GET /admin/alerts/config

Get alert system configuration and status.

**Response:**
```json
{
  "status": "ok",
  "valid": true,
  "warnings": [],
  "config": {
    "email_enabled": true,
    "email_primary": "tarapachecovr@gmail.com",
    "email_secondary": true,
    "email_backup": false,
    "sms_enabled": false,
    "sms_min_amount": 50,
    "webhooks_enabled": true,
    "discord_configured": true,
    "slack_configured": false,
    "custom_webhook_configured": false
  }
}
```

#### GET /health

Health check with recent stats.

**Response:**
```json
{
  "status": "ok",
  "service": "Don Quijote Gourmet & Kids",
  "alerts_enabled": true,
  "recent_stats": {
    "total_orders": 42,
    "total_revenue": 4215.50
  }
}
```

## Webhook Payloads

### Discord Webhook

Sends an embedded message with order details.

**Payload Structure:**
```json
{
  "embeds": [
    {
      "title": "🛒 New Order — GOURMET",
      "description": "Customer info",
      "color": 13158476,
      "fields": [
        {
          "name": "Shipping Address",
          "value": "Address details",
          "inline": false
        },
        {
          "name": "Order Total",
          "value": "€99.95",
          "inline": true
        },
        {
          "name": "Products",
          "value": "• Product X ×2 (€50.00)\n• Product Y ×1 (€49.95)",
          "inline": false
        },
        {
          "name": "Stripe ID",
          "value": "`cs_live_...`",
          "inline": false
        }
      ],
      "timestamp": "2026-04-16T15:30:00Z"
    }
  ]
}
```

### Slack Webhook

Sends a formatted message with attachments.

**Payload Structure:**
```json
{
  "text": "🛒 New Order: John Doe • €99.95",
  "attachments": [
    {
      "color": "#C9A84C",
      "fields": [
        {
          "title": "Customer",
          "value": "John Doe\njohn@example.com\n+34 600 123 456",
          "short": false
        },
        {
          "title": "Order Total",
          "value": "€99.95",
          "short": true
        },
        {
          "title": "Products",
          "value": "• Product X ×2 (€50.00)\n• Product Y ×1 (€49.95)",
          "short": false
        }
      ],
      "footer": "Don Quijote Gourmet & Kids",
      "ts": 1713275400
    }
  ]
}
```

### Custom Webhook

Sends complete order JSON payload.

**Payload Structure:**
```json
{
  "event": "order.completed",
  "brand": "gourmet",
  "order": {
    "stripe_id": "cs_live_...",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "+34 600 123 456",
    "total": 99.95,
    "subtotal": 99.95,
    "shipping": 0.00,
    "items": [
      {
        "name": "Product X",
        "price": 25.00,
        "qty": 2
      }
    ],
    "address": "Calle Mayor 123",
    "city": "Madrid",
    "zip": "28001",
    "country": "ES",
    "timestamp": "2026-04-16T15:30:00..."
  }
}
```

## Alert Log Format

Each alert attempt is logged to `ALERT_LOG_FILE` (default: `/tmp/don_quijote_alerts.log`) as JSON:

```json
{
  "timestamp": "2026-04-16T15:30:05.123456",
  "order_id": "cs_live_abc123...",
  "brand": "gourmet",
  "alert_type": "email",
  "customer": "John Doe",
  "total": 99.95,
  "success": true,
  "message": "Email alert sent to 2 recipient(s)"
}
```

## Error Handling & Fallbacks

### Email Failures
1. If primary email fails, continues to secondary and backup recipients
2. Each recipient attempt logged separately
3. All attempts must succeed for email channel to succeed
4. Logged to alert log with error details

### SMS Failures
1. Only sent if configured and order exceeds minimum amount
2. Failures logged but don't block other channels
3. Twilio SDK import error is caught gracefully

### Webhook Failures
1. Each webhook (Discord/Slack/Custom) attempted independently
2. Timeout set to 10 seconds per webhook
3. Failed webhooks logged but don't affect other channels
4. HTTP non-2xx responses treated as failures

### Graceful Degradation
- If no channels succeed, alert logged as critical
- Order still saved to Google Sheets (primary goal achieved)
- Admin dashboard still shows order
- Email is always attempted (primary channel)
- SMS/Webhooks are optional enhancements

## Setup Guide

### Step 1: Gmail Configuration

1. Enable 2-factor authentication on your Gmail account
2. Create app password: https://myaccount.google.com/apppasswords
3. Copy the 16-character password
4. Set `GMAIL_USER` and `GMAIL_APP_PASSWORD` env vars

### Step 2: Email Recipients

```bash
# Primary recipient (Gourmet brand)
ALERT_EMAIL_PRIMARY="tarapachecovr@gmail.com"

# Optional: Additional recipient (also gets Gourmet alerts)
ALERT_EMAIL_SECONDARY="someone@example.com"

# Optional: Backup recipient (fallback if primary fails)
ALERT_EMAIL_BACKUP="backup@example.com"

# Kids brand (separate email)
KIDS_NOTIFY_EMAIL="hola@donquijotekids.com"
```

### Step 3: Optional - SMS Setup

1. Create Twilio account: https://www.twilio.com
2. Get your Account SID and Auth Token from dashboard
3. Get your Twilio phone number
4. Install Twilio SDK: `pip install twilio`
5. Configure env vars:

```bash
SMS_ALERT_ENABLED="true"
TWILIO_ACCOUNT_SID="ACxxxxx..."
TWILIO_AUTH_TOKEN="your_token"
TWILIO_PHONE="+1234567890"
SMS_ALERT_MIN_AMOUNT="50"  # Only alert for orders >= €50
```

### Step 4: Optional - Webhook Setup

#### Discord
1. Create a Discord server (if needed)
2. Right-click channel → Integrations → Webhooks → Create Webhook
3. Copy webhook URL
4. Set `DISCORD_WEBHOOK_URL` env var

#### Slack
1. Go to your Slack workspace settings
2. Create incoming webhook: https://api.slack.com/messaging/webhooks
3. Copy webhook URL
4. Set `SLACK_WEBHOOK_URL` env var

#### Custom Webhook
1. Prepare your API endpoint that accepts POST requests with JSON
2. Implement endpoint to handle payload (see Webhook Payloads section)
3. Set `CUSTOM_WEBHOOK_URL` env var

### Step 5: Admin Dashboard

```bash
# Generate random API key (use strong password generator)
ADMIN_API_KEY="your_random_secret_key_32_chars_min"

# Set alert log location (must be writable)
ALERT_LOG_FILE="/var/log/don_quijote_alerts.log"
```

### Step 6: Deploy to Railway

Update `.env` file with all new variables, then:

```bash
# Local testing
python server.py

# Deploy to Railway
railway up
```

## Testing Procedures

### Test Email Alerts

```bash
# Check email configuration
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config

# View alert logs
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts

# Make test order through frontend
# Check that alert is logged and email received
```

### Test SMS Alerts

```bash
# Verify Twilio is configured
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config

# Make test order > SMS_ALERT_MIN_AMOUNT
# Check SMS received on TWILIO_PHONE
# Verify in alert logs
```

### Test Webhooks

#### Discord
1. Post test payload using curl/Postman
2. Check that message appears in Discord channel
3. Verify message formatting

```bash
curl -X POST $DISCORD_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "title": "Test",
      "description": "Test message"
    }]
  }'
```

#### Slack
1. Test webhook endpoint
2. Verify message in Slack channel
3. Check formatting

#### Custom Webhook
1. Test your endpoint handles POST requests
2. Verify payload structure matches
3. Test with sample order data

### Integration Testing

1. Create test order through Gourmet frontend
2. Verify order saved to Google Sheets
3. Check all alert channels:
   - Email received at ALERT_EMAIL_PRIMARY
   - SMS received (if enabled and amount > SMS_ALERT_MIN_AMOUNT)
   - Discord message (if enabled)
   - Slack message (if enabled)
   - Custom webhook received (if enabled)
4. Check admin dashboard:
   ```bash
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/orders
   ```

## Troubleshooting Guide

### Email Not Sending

**Symptom**: No emails received, alert log shows "Email alert failed"

**Solutions**:
1. Verify `GMAIL_APP_PASSWORD` is correct (16 chars, not regular password)
2. Check Gmail account has 2FA enabled
3. Verify recipient emails are correct
4. Check spam/promotions folder
5. Test SMTP credentials:
   ```python
   import smtplib
   server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
   server.login("your@gmail.com", "16charapppassword")
   ```

### SMS Not Sending

**Symptom**: SMS alerts never arrive despite enabled

**Solutions**:
1. Verify `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`
2. Check `TWILIO_PHONE` is valid (with country code)
3. Verify order amount exceeds `SMS_ALERT_MIN_AMOUNT`
4. Check Twilio account has sufficient balance
5. Install Twilio SDK: `pip install twilio`
6. Check alert logs for specific error

### Webhooks Not Firing

**Symptom**: Messages not appearing in Discord/Slack

**Solutions**:

**Discord**:
1. Verify webhook URL is correct and recent
2. Check channel still exists and bot has permissions
3. Test webhook with curl
4. Check server logs for timeout errors

**Slack**:
1. Verify webhook URL hasn't expired
2. Check app has permission to post
3. Test webhook separately
4. Verify workspace/channel configuration

### Admin Dashboard Returning 401

**Symptom**: "Unauthorized - Invalid or missing API key"

**Solutions**:
1. Verify `ADMIN_API_KEY` is set and non-empty
2. Include header correctly: `Authorization: Bearer key`
3. Check key matches exactly (case-sensitive)
4. Regenerate key if unsure

### High Server Memory Usage

**Symptom**: Server memory increases over time

**Solutions**:
1. In-memory order store limited to 100 orders
2. Alert log is file-based (append only)
3. Consider moving alert log to database
4. Monitor with `/admin/stats` endpoint
5. Restart server weekly to clear memory

## Migration Guide (Railway Deployment)

### Before Deployment

1. Create `.env` file locally with all new variables
2. Test alert system locally:
   ```bash
   python server.py
   ```
3. Verify each alert channel individually

### Deployment Steps

1. **Backup existing configuration**
   ```bash
   railway env list > backup_env.txt
   ```

2. **Add new environment variables**
   ```bash
   railway env GMAIL_APP_PASSWORD "your_16_char_password"
   railway env ALERT_EMAIL_PRIMARY "tarapachecovr@gmail.com"
   railway env ALERT_EMAIL_SECONDARY "optional@example.com"
   railway env SMS_ALERT_ENABLED "false"
   railway env WEBHOOK_ALERT_ENABLED "false"
   railway env ADMIN_API_KEY "your_secret_key"
   ```

3. **Deploy updated code**
   ```bash
   git add -A
   git commit -m "chore: upgrade to multi-channel alert system"
   git push
   # or: railway up
   ```

4. **Verify deployment**
   ```bash
   curl https://your-server/health
   ```

5. **Test alert system**
   ```bash
   # Check configuration loaded correctly
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/alerts/config
   
   # Make test order
   # Verify alerts received
   ```

### Rollback Procedure

If issues occur, revert to previous version:

```bash
git revert HEAD
git push
# or: railway up

# Verify reverted
curl https://your-server/health
```

The system gracefully handles missing env vars by disabling optional features.

## Configuration Examples

### Minimal Setup (Email Only)

```bash
GMAIL_USER="tarapachecovr@gmail.com"
GMAIL_APP_PASSWORD="16charapppassword"
ALERT_EMAIL_PRIMARY="tarapachecovr@gmail.com"
KIDS_NOTIFY_EMAIL="hola@donquijotekids.com"
```

### Full Setup (All Channels)

```bash
# Email
GMAIL_USER="tarapachecovr@gmail.com"
GMAIL_APP_PASSWORD="16charapppassword"
ALERT_EMAIL_PRIMARY="tarapachecovr@gmail.com"
ALERT_EMAIL_SECONDARY="secondary@example.com"
ALERT_EMAIL_BACKUP="backup@example.com"
KIDS_NOTIFY_EMAIL="hola@donquijotekids.com"

# SMS
SMS_ALERT_ENABLED="true"
TWILIO_ACCOUNT_SID="ACxxxxx..."
TWILIO_AUTH_TOKEN="your_token"
TWILIO_PHONE="+1234567890"
SMS_ALERT_MIN_AMOUNT="50"

# Webhooks
WEBHOOK_ALERT_ENABLED="true"
DISCORD_WEBHOOK_URL="https://discordapp.com/api/webhooks/..."
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Admin
ADMIN_API_KEY="your_secret_admin_key_32_chars"
ALERT_LOG_FILE="/var/log/don_quijote_alerts.log"
```

### Development Setup (Local)

```bash
# Use test credentials
GMAIL_USER="test@gmail.com"
GMAIL_APP_PASSWORD="testapppassword"
ALERT_EMAIL_PRIMARY="test@gmail.com"

# Disable optional features
SMS_ALERT_ENABLED="false"
WEBHOOK_ALERT_ENABLED="false"

# Test credentials (don't need real keys)
ADMIN_API_KEY="dev_test_key"
ALERT_LOG_FILE="/tmp/test_alerts.log"
```

## Production Checklist

- [ ] All email addresses verified and correct
- [ ] Gmail App Password generated and saved securely
- [ ] SMS credentials configured (if using)
- [ ] Webhook URLs tested independently
- [ ] Admin API key generated (32+ characters)
- [ ] Alert log file location writable by Flask process
- [ ] Tested full order flow end-to-end
- [ ] Verified all alert channels working
- [ ] Admin dashboard tested and password protected
- [ ] Error logs monitored (first 24 hours)
- [ ] Backups of configuration created
- [ ] Team trained on dashboard usage
- [ ] Escalation procedure documented
- [ ] Alert thresholds reviewed (SMS min amount, etc.)

## Support & Monitoring

### Daily Health Checks

```bash
# Check service health
curl https://your-server/health

# View recent orders
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/orders?limit=5

# Review alert status
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=20
```

### Common Monitoring Tasks

1. **Daily revenue check**
   ```bash
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/stats | jq '.stats.total_revenue'
   ```

2. **Alert channel status**
   ```bash
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/alerts/config | jq '.config'
   ```

3. **Recent failures**
   ```bash
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/alerts?limit=100 | \
        jq '.alerts[] | select(.success == false)'
   ```

## Code Changes Summary

### Modified Files

**server.py**
- Added `from alerts import ...` imports
- Updated webhook handler to use `AlertOrchestrator`
- Added `AdminDashboard.record_order()` call
- Added `/admin/*` endpoints
- Added `@require_admin_key` decorator
- Added improved logging
- Improved error handling

### New Files

**alerts.py** (400+ lines)
- Complete multi-channel alert system
- All classes listed above

### Backward Compatibility

- No breaking changes to existing APIs
- Old `send_email_notification()` completely replaced (internal only)
- Webhook signature verification unchanged
- Google Sheets integration unchanged
- Stripe integration unchanged
- All new features optional (graceful degradation)

## Version History

- **v2.0.0** (2026-04-16): Multi-channel alert system
- **v1.0.0** (2026-03-xx): Initial email-only system
