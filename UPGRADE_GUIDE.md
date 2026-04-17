# Upgrade Guide — v1.0 → v2.0 Multi-Channel Alert System

## Summary of Changes

The multi-channel alert system adds optional SMS, webhook, and admin dashboard capabilities while maintaining 100% backward compatibility with existing code.

### What's New

✓ **Email Alerts Enhanced**
- Multiple recipient support (primary, secondary, backup)
- Brand-specific recipient routing
- Improved HTML templates with action buttons
- Enhanced customer and product information

✓ **SMS Alerts (Optional)**
- Twilio integration
- Configurable minimum order threshold
- Short, urgent message format

✓ **Webhook Alerts (Optional)**
- Discord integration with embedded messages
- Slack integration with formatted attachments
- Custom HTTP endpoint support
- Full JSON payload delivery

✓ **Admin Dashboard**
- Real-time order tracking (`/admin/orders`)
- Statistical dashboards (`/admin/stats`)
- Alert log viewing (`/admin/alerts`)
- Configuration status (`/admin/alerts/config`)
- API key protection for all admin endpoints

✓ **Comprehensive Logging**
- All alert attempts logged to file
- Audit trail for debugging
- Queryable alert history
- Success/failure tracking

### What Stays the Same

- ✓ Stripe webhook integration unchanged
- ✓ Google Sheets storage unchanged
- ✓ Frontend API unchanged
- ✓ Payment flow unchanged
- ✓ User experience unchanged
- ✓ Zero breaking changes to existing code

## Files Changed

### Modified Files

**`server.py`**
- Added: `from alerts import ...` imports (6 new imports)
- Changed: Webhook handler now uses `AlertOrchestrator` (3 new lines)
- Added: `@require_admin_key` decorator for admin protection (9 lines)
- Added: 6 new admin endpoints (`/admin/*`)
- Added: Improved error handling and logging
- Removed: Old `send_email_notification()` function (now in alerts.py)
- **Impact**: 100% backward compatible, all existing endpoints unchanged

### New Files

**`alerts.py` (450+ lines)**
- Core alert system with all alert channels
- Email templates with brand-specific styling
- SMS, webhook, logging, and dashboard modules
- Fully documented with docstrings

**`ALERT_SYSTEM.md` (1000+ lines)**
- Complete system documentation
- API reference for all endpoints
- Setup guides for each alert channel
- Troubleshooting guide
- Configuration examples

**`SETUP_GUIDE.md` (200+ lines)**
- Quick start (5-minute setup)
- Optional feature setup
- Monitoring and troubleshooting
- Production checklist

**`.env.example` (100+ lines)**
- All environment variables documented
- Examples and usage notes
- Setup instructions for each service

## Step-by-Step Upgrade

### Phase 1: Preparation (5 min)

1. **Backup current environment**
   ```bash
   cd ~/Desktop/DonQuijoteGourmet/server
   cp .env .env.backup.$(date +%s)
   git status  # Verify clean working directory
   ```

2. **Review changes**
   ```bash
   # Check what files are being added/modified
   git status
   git diff HEAD
   ```

3. **Test locally** (if developing locally)
   ```bash
   python server.py
   # Should see: "✓ Alert system validated"
   ```

### Phase 2: Configuration (10 min)

1. **Update .env file**
   ```bash
   # Copy new template
   cp .env.example .env.new
   
   # Merge with existing (keep existing values, add new ones)
   # Add these new lines to .env:
   
   # Email (new)
   ALERT_EMAIL_PRIMARY=tarapachecovr@gmail.com
   ALERT_EMAIL_SECONDARY=
   ALERT_EMAIL_BACKUP=
   
   # SMS (optional)
   SMS_ALERT_ENABLED=false
   TWILIO_ACCOUNT_SID=
   TWILIO_AUTH_TOKEN=
   TWILIO_PHONE=
   SMS_ALERT_MIN_AMOUNT=50
   
   # Webhooks (optional)
   WEBHOOK_ALERT_ENABLED=false
   DISCORD_WEBHOOK_URL=
   SLACK_WEBHOOK_URL=
   CUSTOM_WEBHOOK_URL=
   
   # Admin
   ADMIN_API_KEY=your_random_key_32_chars
   ADMIN_ALERT_ENABLED=true
   ALERT_LOG_FILE=/tmp/don_quijote_alerts.log
   ```

2. **Generate admin API key**
   ```bash
   # Option A: Using openssl
   openssl rand -base64 32
   
   # Option B: Using Python
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Verify Gmail App Password**
   - Must be 16-character app-specific password
   - From: https://myaccount.google.com/apppasswords
   - NOT your regular Gmail password

### Phase 3: Code Deployment (5 min)

1. **Deploy to Railway**
   ```bash
   git add -A
   git commit -m "chore: upgrade to multi-channel alert system v2.0"
   
   # Add new environment variables
   railway env ADMIN_API_KEY "$(openssl rand -base64 32)"
   railway env ALERT_EMAIL_PRIMARY "tarapachecovr@gmail.com"
   railway env SMS_ALERT_ENABLED "false"
   railway env WEBHOOK_ALERT_ENABLED "false"
   railway env ALERT_LOG_FILE "/tmp/don_quijote_alerts.log"
   
   # Deploy
   railway up
   ```

2. **Verify deployment**
   ```bash
   # Check health
   curl https://your-server/health
   
   # Should see: "alerts_enabled": true
   ```

### Phase 4: Testing (10 min)

1. **Test email alert**
   ```bash
   # Check configuration loaded
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/alerts/config
   
   # Make test order
   # Visit: https://donquijote-kids.netlify.app
   # Complete test order
   
   # Verify email received
   # Check admin dashboard
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/orders
   ```

2. **Verify Google Sheets still works**
   - Check your Gourmet sheet
   - Check your Kids sheet
   - New order should appear in correct sheet

3. **Check alert logs**
   ```bash
   # View recent alerts
   curl -H "Authorization: Bearer $ADMIN_API_KEY" \
        https://your-server/admin/alerts?limit=5
   
   # Should show successful email alerts
   ```

### Phase 5: Optional Features (15 min each)

#### Add SMS Alerts
1. Create Twilio account: https://www.twilio.com/console
2. Get Account SID, Auth Token, and phone number
3. Install SDK: `pip install twilio`
4. Update .env:
   ```bash
   SMS_ALERT_ENABLED=true
   TWILIO_ACCOUNT_SID=ACxxxxxx...
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE=+1234567890
   SMS_ALERT_MIN_AMOUNT=50
   ```
5. Test with order > €50

#### Add Discord Webhook
1. Right-click Discord channel → Integrations → Webhooks
2. Create Webhook, copy URL
3. Update .env:
   ```bash
   WEBHOOK_ALERT_ENABLED=true
   DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/...
   ```
4. Test with new order

#### Add Slack Webhook
1. Go to https://api.slack.com/messaging/webhooks
2. Create webhook, copy URL
3. Update .env:
   ```bash
   WEBHOOK_ALERT_ENABLED=true
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```
4. Test with new order

### Phase 6: Cleanup (2 min)

1. **Verify rollback procedure works**
   ```bash
   # Document previous version
   git log --oneline -1
   
   # Confirm you can revert if needed
   git log --oneline | head -5
   ```

2. **Backup configuration**
   ```bash
   # Save current env vars
   railway env list > env_backup_v2.txt
   ```

3. **Document access credentials**
   - Save ADMIN_API_KEY securely (1password, vault, etc.)
   - Share with team members who need dashboard access
   - Document in team wiki/docs

## Rollback Procedure

If issues arise, rollback is simple:

```bash
# Option A: Revert to previous commit
git revert HEAD
git push
railway up

# Option B: Force previous version
git reset --hard HEAD~1
git push --force
railway up

# Verify
curl https://your-server/health
```

**No data loss**: Alert system is non-destructive. Old orders remain in Google Sheets.

## Testing Checklist

- [ ] Server starts without errors
- [ ] Health check passes (`/health`)
- [ ] Admin dashboard accessible with API key
- [ ] Make test order (Gourmet)
- [ ] Email received at ALERT_EMAIL_PRIMARY
- [ ] Order appears in Google Sheets (Gourmet)
- [ ] Admin dashboard shows order (`/admin/orders`)
- [ ] Alert statistics updated (`/admin/stats`)
- [ ] Alert log shows successful email (`/admin/alerts`)
- [ ] Make test order (Kids)
- [ ] Email received at KIDS_NOTIFY_EMAIL
- [ ] Order appears in Google Sheets (Kids)
- [ ] Dashboard shows correct brand
- [ ] SMS test (if enabled): Order > €50, SMS received
- [ ] Discord test (if enabled): Message appears in channel
- [ ] Slack test (if enabled): Message appears in channel
- [ ] Error handling test: Temporarily disable GMAIL_APP_PASSWORD
- [ ] Verify graceful degradation (other channels still work)
- [ ] Re-enable GMAIL_APP_PASSWORD and verify recovery

## What to Monitor After Upgrade

### First 24 Hours

```bash
# Every 4 hours, check:
curl https://your-server/health

# Check for errors:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/alerts?limit=100 | \
     jq '.alerts[] | select(.success == false)'

# Monitor order volume:
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats
```

### First Week

- Monitor alert channel performance
- Verify all orders are being saved to sheets
- Check that emails are consistent
- Monitor admin dashboard usage
- Review any alert failures
- Check alert log file size (rotate if needed)

### Ongoing

- Daily health checks
- Weekly alert review
- Monthly performance report
- Alert log rotation (monthly)
- Security review of API key access

## FAQ

**Q: Will my existing orders/integrations break?**
A: No. Zero breaking changes. All existing APIs work identically.

**Q: What if I don't want to use the new features?**
A: Just leave optional env vars empty. System gracefully handles missing features.

**Q: Can I enable features gradually?**
A: Yes! Enable one feature at a time and test each independently.

**Q: What happens if an alert channel fails?**
A: Order is still saved to Google Sheets. Other channels continue. Failure is logged.

**Q: How do I protect the admin dashboard?**
A: It requires `ADMIN_API_KEY` in Authorization header. Only share with authorized users.

**Q: Is the alert system GDPR compliant?**
A: Alerts log order data. If GDPR required, implement log retention policy and deletion.

**Q: Can I move alert logs to a database?**
A: Yes. Modify `AlertLogger` class in `alerts.py` to use your database instead of file.

**Q: What if Twilio/Discord/Slack credentials leak?**
A: Regenerate immediately. Deactivate webhook URLs. Create new Twilio tokens.

## Support

1. **Check Documentation**: `ALERT_SYSTEM.md` for detailed docs
2. **Quick Setup**: `SETUP_GUIDE.md` for quick reference
3. **Troubleshooting**: Both docs have troubleshooting sections
4. **Check Logs**: `/admin/alerts` endpoint shows all attempts
5. **Test Endpoints**: Use curl to test each channel individually

## Version History

- **v2.0.0** (2026-04-16): Multi-channel alert system
  - Email: Multiple recipients, branded templates
  - SMS: Twilio integration (optional)
  - Webhooks: Discord, Slack, custom (optional)
  - Admin: Dashboard endpoints with API key protection
  - Logging: Complete audit trail
  - Docs: Comprehensive documentation

- **v1.0.0** (2026-03-xx): Initial system
  - Email: Single recipient per brand
  - Google Sheets: Order storage
  - Stripe: Payment processing

## Congratulations!

Your multi-channel alert system is now live. Check the dashboard:

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
     https://your-server/admin/stats
```

Welcome to v2.0!
