# Quick Setup Guide — Multi-Channel Alert System

## 5-Minute Quick Start

### 1. Install Dependencies
```bash
cd ~/Desktop/DonQuijoteGourmet/server
pip install -r requirements.txt
# Or add to requirements.txt:
# twilio (optional, for SMS)
# requests (already included for webhooks)
```

### 2. Update .env File
Copy `.env.example` → `.env` and fill in:

```bash
# Essential (already configured)
STRIPE_SECRET_KEY=sk_live_...
GOOGLE_CREDENTIALS_B64=...
GOURMET_SHEET_ID=...
KIDS_SHEET_ID=...

# Email (add/update these)
GMAIL_USER=tarapachecovr@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx    # From: https://myaccount.google.com/apppasswords
ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
KIDS_NOTIFY_EMAIL=hola@donquijotekids.com

# Admin (add these)
ADMIN_API_KEY=$(openssl rand -base64 32)  # Or any strong random string
```

### 3. Test Locally
```bash
python server.py
# Should start without errors:
# ✓ Alert system validated
# ✓ Server running on port 5000
```

### 4. Test with Order
1. Visit: http://localhost:3456 (Gourmet frontend)
2. Make test order through payment flow
3. Check email received at `ALERT_EMAIL_PRIMARY`
4. Verify alert logged: `tail -f /tmp/don_quijote_alerts.log`

### 5. Deploy to Railway
```bash
git add -A
git commit -m "chore: upgrade to multi-channel alert system"
railway env ADMIN_API_KEY "$(openssl rand -base64 32)"
railway env SMS_ALERT_ENABLED "false"
railway env WEBHOOK_ALERT_ENABLED "false"
railway up
```

## Optional: SMS Alerts

### Setup Twilio (5 minutes)

1. **Create Twilio Account**: https://www.twilio.com/console
2. **Get Credentials**:
   - Account SID: Copy from dashboard
   - Auth Token: Copy from dashboard
   - Phone Number: Buy a number (e.g., +1-800-...) or use trial
3. **Install SDK**: `pip install twilio`
4. **Update .env**:
   ```bash
   SMS_ALERT_ENABLED=true
   TWILIO_ACCOUNT_SID=ACxxxxxx...
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE=+1234567890
   SMS_ALERT_MIN_AMOUNT=50
   ```
5. **Test**: Make order > €50, verify SMS received

## Optional: Discord Webhook

### Setup Discord Channel (2 minutes)

1. **Create/Select Channel** in your Discord server
2. **Create Webhook**:
   - Right-click channel → Integrations → Webhooks
   - Click "Create Webhook"
   - Copy webhook URL
3. **Update .env**:
   ```bash
   WEBHOOK_ALERT_ENABLED=true
   DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/...
   ```
4. **Test**: Make order, check Discord channel

## Optional: Slack Webhook

### Setup Slack (3 minutes)

1. **Create Webhook**:
   - Go to: https://api.slack.com/messaging/webhooks
   - Click "Create New App"
   - From scratch → Name app → Pick workspace
   - Enable Incoming Webhooks
   - Add New Webhook to Workspace
   - Select channel → Authorize
   - Copy webhook URL
2. **Update .env**:
   ```bash
   WEBHOOK_ALERT_ENABLED=true
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```
3. **Test**: Make order, check Slack

## Optional: Custom Webhook

For any other service (Zapier, Make, custom API):

1. **Prepare Endpoint** that accepts:
   ```json
   {
     "event": "order.completed",
     "brand": "gourmet",
     "order": { ... }
   }
   ```
2. **Update .env**:
   ```bash
   WEBHOOK_ALERT_ENABLED=true
   CUSTOM_WEBHOOK_URL=https://your-api.example.com/orders
   ```
3. **Test**: Make order, check webhook receiver

## Admin Dashboard

### Access Dashboard

```bash
# Get recent orders
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/orders

# Get statistics
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats

# Get alert status
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config
```

### Dashboard Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/admin/orders?limit=10` | Recent orders | List of 10 most recent orders |
| `/admin/stats` | Statistics | Total revenue, order counts, etc. |
| `/admin/alerts?limit=50` | Alert log | Recent alert attempts with status |
| `/admin/alerts/config` | Configuration | Alert system status and channels |
| `/health` | Health check | Service status + recent stats |

## Troubleshooting

### Email Not Sending

```bash
# 1. Check config
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config

# 2. Check recent alerts for errors
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts | jq '.alerts[-5:]'

# 3. Verify Gmail App Password (not regular password)
# https://myaccount.google.com/apppasswords

# 4. Test SMTP manually
python3 << 'EOF'
import smtplib
server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login("your@gmail.com", "16charapppassword")
print("✓ SMTP works!")
EOF
```

### SMS Not Sending

```bash
# 1. Verify order amount >= SMS_ALERT_MIN_AMOUNT
# 2. Check Twilio credits/balance
# 3. Verify phone number format (+1234567890)
# 4. Check recent alerts:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts | jq '.alerts[] | select(.alert_type == "sms")'
```

### Webhooks Not Firing

```bash
# 1. Test webhook independently
curl -X POST $DISCORD_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"embeds":[{"title":"Test"}]}'

# 2. Check alert logs
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts | \
     jq '.alerts[] | select(.alert_type | contains("webhook"))'

# 3. Verify webhook URL hasn't expired
```

### "Unauthorized" on Admin Endpoints

```bash
# Check ADMIN_API_KEY is set
echo $ADMIN_API_KEY

# Use correct header format
curl -H "Authorization: Bearer $ADMIN_API_KEY" https://server/admin/orders

# Regenerate if needed
ADMIN_API_KEY=$(openssl rand -base64 32)
railway env ADMIN_API_KEY "$ADMIN_API_KEY"
```

## Monitoring

### Daily Check (30 seconds)

```bash
# Health
curl https://your-server/health

# Orders today
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats | jq '.stats.total_orders'

# Revenue today
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats | jq '.stats.total_revenue'
```

### Weekly Check (2 minutes)

```bash
# View all alerts from past week
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=500 | \
     jq '.alerts[] | select(.timestamp > now(-604800))'

# Check for alert failures
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=500 | \
     jq '.alerts[] | select(.success == false)'

# Review alert configuration
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config
```

## Rollback

If something breaks:

```bash
# Revert to previous version
git revert HEAD
git push
railway up

# Or restore from backup
git checkout previous_working_commit
railway up
```

The system gracefully handles missing config, so no data loss.

## Next Steps

1. ✓ Set up email alerts (required)
2. Optional: Add SMS alerts (Twilio)
3. Optional: Add Discord webhook
4. Optional: Add Slack webhook
5. Set up monitoring/health checks
6. Train team on admin dashboard
7. Document escalation procedures

## Support

- **Docs**: See `ALERT_SYSTEM.md` for complete documentation
- **Issues**: Check alert logs: `/tmp/don_quijote_alerts.log`
- **Debug**: Use `/admin/alerts` endpoint to view all attempts
- **Test**: Always test new channels with a real order first

## Production Checklist

- [ ] Email addresses verified
- [ ] Gmail App Password created and set
- [ ] Test order sent and email received
- [ ] Admin API key generated and saved securely
- [ ] Alert log file location writable
- [ ] All optional features tested before enabling
- [ ] Team trained on dashboard
- [ ] Monitoring set up
- [ ] Backup env vars saved
- [ ] Deployment successful
- [ ] No errors in alert logs
- [ ] Revenue is being tracked correctly
