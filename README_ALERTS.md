# Don Quijote Multi-Channel Alert System

Production-ready order notification system with Email, SMS, Discord, Slack, and Admin Dashboard.

## Start Here

Choose your use case:

### I Just Want to Deploy (5 min)
→ Read: `SETUP_GUIDE.md`

### I Need Complete Documentation
→ Read: `ALERT_SYSTEM.md`

### I'm Upgrading from v1.0
→ Read: `UPGRADE_GUIDE.md`

### I Need Quick Answers
→ Read: `QUICK_REFERENCE.md`

### I Need All the Details
→ Read: `IMPLEMENTATION_SUMMARY.md`

## What's Included

### Core System
- **alerts.py** (450 lines) — Email, SMS, webhooks, logging, dashboard
- **server.py** (updated) — Flask integration with admin endpoints
- **.env.example** — Environment template with all variables

### Documentation (2500+ lines)
| Document | Purpose | Read Time |
|----------|---------|-----------|
| `QUICK_REFERENCE.md` | Quick lookup card | 5 min |
| `SETUP_GUIDE.md` | Quick start guide | 10 min |
| `ALERT_SYSTEM.md` | Complete reference | 30 min |
| `UPGRADE_GUIDE.md` | Migration instructions | 20 min |
| `IMPLEMENTATION_SUMMARY.md` | What was built | 15 min |
| `README_ALERTS.md` | This file | 5 min |

## Features

### Email Alerts
- ✅ Multiple recipients (primary, secondary, backup)
- ✅ Brand-specific routing (Gourmet vs Kids)
- ✅ Rich HTML templates with brand colors
- ✅ Action buttons (View in Stripe, Email Customer)
- ✅ Professional formatting

### SMS Alerts (Optional)
- ✅ Twilio integration
- ✅ Configurable minimum order threshold
- ✅ Short message format
- ✅ Graceful fallback if not configured

### Webhook Alerts (Optional)
- ✅ Discord: Embedded messages with brand colors
- ✅ Slack: Formatted messages with attachments
- ✅ Custom: Full JSON payload to any HTTP endpoint
- ✅ Independent, non-blocking

### Admin Dashboard
- ✅ Real-time order tracking (`/admin/orders`)
- ✅ Revenue statistics (`/admin/stats`)
- ✅ Alert history (`/admin/alerts`)
- ✅ System status (`/admin/alerts/config`)
- ✅ API key protection on all endpoints

### Reliability
- ✅ Complete error handling
- ✅ Comprehensive logging
- ✅ Graceful degradation
- ✅ Zero breaking changes
- ✅ 100% backward compatible

## Quick Start

### 1. Install (1 min)
```bash
cd ~/Desktop/DonQuijoteGourmet/server
# Already includes all dependencies
# Optional: pip install twilio (for SMS)
```

### 2. Configure (5 min)
```bash
# Update .env file
cp .env.example .env

# Add essential variables:
GMAIL_USER=tarapachecovr@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx    # From Gmail settings
ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
KIDS_NOTIFY_EMAIL=hola@donquijotekids.com
ADMIN_API_KEY=$(openssl rand -base64 32)
```

### 3. Test Locally (5 min)
```bash
python server.py
# Should see: ✓ Alert system validated

# Visit http://localhost:3456
# Make test order
# Check email received
```

### 4. Deploy to Railway (5 min)
```bash
git add -A
git commit -m "chore: upgrade to multi-channel alert system"
railway env ADMIN_API_KEY "$(openssl rand -base64 32)"
railway up

# Verify
curl https://your-server/health
```

## Environment Variables

### Required
```bash
GMAIL_USER=tarapachecovr@gmail.com
GMAIL_APP_PASSWORD=16_char_app_password
ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
KIDS_NOTIFY_EMAIL=hola@donquijotekids.com
ADMIN_API_KEY=random_32_char_key
```

### Optional
```bash
SMS_ALERT_ENABLED=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE=

WEBHOOK_ALERT_ENABLED=false
DISCORD_WEBHOOK_URL=
SLACK_WEBHOOK_URL=
CUSTOM_WEBHOOK_URL=
```

See `.env.example` for complete list with documentation.

## API Endpoints

All admin endpoints require: `Authorization: Bearer $ADMIN_API_KEY`

```bash
# Recent orders
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/orders?limit=10

# Statistics
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats

# Alert history
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=50

# System status
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts/config

# Health check (no auth needed)
curl https://your-server/health
```

See `QUICK_REFERENCE.md` for complete API documentation.

## Adding Optional Features

### SMS Alerts (5 min setup)
1. Create Twilio account: https://twilio.com
2. Get Account SID, Auth Token, phone number
3. Update .env and test
See `SETUP_GUIDE.md` for details

### Discord Webhook (2 min setup)
1. Right-click Discord channel → Webhooks
2. Create webhook, copy URL
3. Set `DISCORD_WEBHOOK_URL` and enable
See `SETUP_GUIDE.md` for details

### Slack Webhook (3 min setup)
1. Create Slack app: https://api.slack.com
2. Enable Incoming Webhooks
3. Set `SLACK_WEBHOOK_URL` and enable
See `SETUP_GUIDE.md` for details

## Testing

### Test Email
```bash
# Make test order through frontend
# Check email received at ALERT_EMAIL_PRIMARY
# Verify in admin dashboard:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/orders?limit=1
```

### Test SMS (if enabled)
```bash
# Make order > SMS_ALERT_MIN_AMOUNT
# Verify SMS received on TWILIO_PHONE
# Check alert log:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts | jq '.alerts[] | select(.alert_type == "sms")'
```

### Test Webhooks (if enabled)
```bash
# Make test order
# Check Discord/Slack channel for message
# Verify in alert log:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts | jq '.alerts[] | select(.alert_type | contains("webhook"))'
```

## Monitoring

### Daily Health Check (30 sec)
```bash
curl https://your-server/health
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats
```

### Weekly Alert Review (2 min)
```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=500 | \
     jq '.alerts[] | select(.success == false)'
```

### Monthly Maintenance (5 min)
- Verify all alert channels working
- Rotate alert log if needed
- Review alert configuration
- Update credentials if expired

## Troubleshooting

### Email Not Sending
1. Verify GMAIL_APP_PASSWORD (16 chars, not regular password)
2. Check `/admin/alerts/config` to confirm email enabled
3. Make test order and check `/admin/alerts` for errors
4. See `SETUP_GUIDE.md` for detailed troubleshooting

### Admin Dashboard 401 Error
1. Verify ADMIN_API_KEY is set: `echo $ADMIN_API_KEY`
2. Use correct header format: `Authorization: Bearer key`
3. Regenerate if needed: `openssl rand -base64 32`

### SMS/Webhooks Not Working
1. Check if enabled: `?limit=50&success=false` in `/admin/alerts`
2. Verify credentials configured: `/admin/alerts/config`
3. Test webhook independently (Discord/Slack test endpoint)
4. See `SETUP_GUIDE.md` for detailed troubleshooting

See `ALERT_SYSTEM.md` or `SETUP_GUIDE.md` for complete troubleshooting.

## Key Files

| File | Purpose |
|------|---------|
| `alerts.py` | Core alert system (450 lines) |
| `server.py` | Flask app with admin endpoints (415 lines) |
| `.env.example` | Environment template (100+ lines) |
| `QUICK_REFERENCE.md` | Quick lookup (5 min read) |
| `SETUP_GUIDE.md` | Quick start (10 min read) |
| `ALERT_SYSTEM.md` | Complete docs (30 min read) |
| `UPGRADE_GUIDE.md` | Migration steps (20 min read) |
| `IMPLEMENTATION_SUMMARY.md` | What was built (15 min read) |

## Architecture

```
Flask Server (server.py)
    ↓
Webhook Handler (detect brand, validate signature)
    ↓
AlertOrchestrator (coordinate all channels)
    ├→ EmailAlert (multiple recipients, branded templates)
    ├→ SMSAlert (Twilio, optional)
    ├→ WebhookAlert (Discord, Slack, custom)
    ├→ AlertLogger (audit trail)
    └→ AdminDashboard (order tracking)
    ↓
Google Sheets (save order)
```

## Security

- ✅ Admin endpoints protected with API key
- ✅ Stripe webhook signatures validated
- ✅ No credentials logged
- ✅ CORS restricted to known frontends
- ✅ All inputs validated and sanitized

## Support

| Need | Document | Time |
|------|----------|------|
| Quick start | `SETUP_GUIDE.md` | 10 min |
| Quick reference | `QUICK_REFERENCE.md` | 5 min |
| Complete docs | `ALERT_SYSTEM.md` | 30 min |
| Upgrade help | `UPGRADE_GUIDE.md` | 20 min |
| Implementation details | `IMPLEMENTATION_SUMMARY.md` | 15 min |

## FAQ

**Q: Will this break my existing system?**
A: No. Zero breaking changes. 100% backward compatible.

**Q: Do I have to use all features?**
A: No. All features except email are optional. System gracefully handles missing config.

**Q: Can I enable features gradually?**
A: Yes. Test each feature independently before enabling.

**Q: How do I protect admin dashboard?**
A: All admin endpoints require API key in Authorization header.

**Q: What if something fails?**
A: Failures are logged to `/admin/alerts`. Order still saves to Google Sheets.

**Q: Can I rollback if issues occur?**
A: Yes. Simple git revert. No data loss. See `UPGRADE_GUIDE.md`.

## Next Steps

1. ✅ Read `SETUP_GUIDE.md` (5-10 min)
2. ✅ Configure `.env` with your details (5 min)
3. ✅ Test locally: `python server.py` (5 min)
4. ✅ Make test order and verify email (5 min)
5. ✅ Deploy to Railway (5 min)
6. ✅ Test in production (5 min)
7. ✅ Optional: Add SMS/Discord/Slack (15 min each)

**Total time to production: 30-45 minutes**

## Version

- **Current**: v2.0.0 (2026-04-16)
- **Status**: Production Ready
- **Breaking Changes**: None
- **Backward Compatible**: Yes

## Credits

Multi-channel alert system built for Don Quijote Gourmet & Kids.
Designed to provide flexible, reliable order notifications.
Ready for production deployment.

---

**Questions?** See the documentation files listed above.
**Ready to deploy?** Start with `SETUP_GUIDE.md`.
**Need help?** Check `ALERT_SYSTEM.md` troubleshooting section.
