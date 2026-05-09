# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Flask backend for **Don Quijote Gourmet & Kids** — a single service that handles Stripe checkout and post-payment notifications for **two brands** (`gourmet` and `kids`) selected at request time via a `brand` field. Deployed on Railway (`railway.json`, `Procfile`).

There is no test suite, no linter config, and no build step. The whole app is two Python files (`server.py`, `alerts.py`) plus three one-shot setup scripts.

## Commands

```bash
# Install deps
pip install -r requirements.txt

# Run locally (reads .env via python-dotenv)
python server.py                # listens on $PORT (default 5000)

# One-shot Google Sheets setup (run after creating sheets and sharing with the
# service account). Requires credentials.json + GOURMET_SHEET_ID/KIDS_SHEET_ID.
python setup_sheets.py          # both brands
python setup_sheet.py           # legacy single-sheet variant

# One-shot: share both sheets with the service account using your own
# Google OAuth client (oauth_client.json from GCP Console).
python share_sheets.py
```

There is **no `pytest` / `ruff` / `mypy`** configured. Don't claim "tests pass" — there are none. Validate changes by running `python server.py` and exercising endpoints with `curl`.

Railway deploy is `git push` to the tracked branch; `Procfile` runs `python server.py`.

## Architecture

### Request flow (the core path)

1. **Frontend → `POST /create-checkout`** with `{items, customer, brand}`. Server computes shipping (Kids = free, Gourmet = free over €60 else €4.95), builds Stripe `line_items`, and stuffs **all order data into Stripe `metadata`** (including `brand`, items as JSON, customer fields). Returns the Stripe Checkout URL.
2. **Stripe → `POST /webhook`** on `checkout.session.completed`. Server reconstructs the order from `session.metadata`, then fans out:
   - `save_to_sqlite` — **primary** persistence (`/tmp/orders.db`, table `orders`).
   - `save_to_sheet` — **secondary, best-effort**; failures are logged and swallowed.
   - `AdminDashboard.record_order` — in-memory ring buffer (last 100), used by `/admin/*`.
   - `AlertOrchestrator.send_all_alerts` — multi-channel notifications (see below).

Stripe metadata is the single source of truth for order data inside the webhook — there is no DB lookup between checkout and webhook. Don't add fields to checkout without also adding them to the metadata block in `server.py:create_checkout` and the reconstruction block in `webhook`.

### Brand multiplexing

`brand` (`"gourmet"` or `"kids"`, defaults to `"gourmet"`) is threaded through everything: it selects the Sheet ID, success/cancel URL (`FRONTEND_URL` vs `KIDS_FRONTEND_URL`), email recipients, SMTP credentials, and email template colors. When adding a feature, check whether it needs to branch on brand — most do.

### Alert system (`alerts.py`)

`AlertOrchestrator.send_all_alerts` runs each channel and aggregates results:

- `EmailAlert` — **prefers Resend HTTP API** (`RESEND_API_KEY`, Railway-friendly), falls back to brand-specific Zoho SMTP (`{GOURMET,KIDS}_SMTP_USER/PASSWORD`). Recipients are computed per-brand by `EmailAlert.get_recipients`.
- `SMSAlert` — Twilio, gated by `SMS_ALERT_ENABLED` and `SMS_ALERT_MIN_AMOUNT` (won't fire below threshold).
- `WebhookAlert` — Discord / Slack / custom; gated by `WEBHOOK_ALERT_ENABLED` plus per-target URL.
- `AlertLogger` — appends every attempt as JSON Lines to `ALERT_LOG_FILE` (default `/tmp/don_quijote_alerts.log`). `/admin/alerts` reads the tail.

Channels degrade independently: missing Twilio creds disable SMS without breaking email. `AlertConfig.validate()` runs at startup and only logs warnings — it does not block boot.

### Admin endpoints

All `/admin/*` routes require header `Authorization: Bearer $ADMIN_API_KEY` (or bare key) via `@require_admin_key`. They expose dashboard data, alert history, alert config status, and a CSV export of the SQLite `orders` table.

`AdminDashboard._orders` is **in-process memory** (lost on restart). The SQLite table and `/admin/export.csv` are the durable record; the in-memory list is just for the live dashboard widgets.

## Configuration

Everything is environment-driven — no config files. Key vars (full list and defaults live in `AlertConfig` at the top of `alerts.py` and the `── Config ──` block in `server.py`):

- **Stripe**: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- **Google Sheets**: `GOOGLE_CREDENTIALS_B64` (base64 of service-account JSON; preferred for Railway) **or** local `credentials.json`; `GOURMET_SHEET_ID`, `KIDS_SHEET_ID` (`GOOGLE_SHEET_ID` is a legacy alias for Gourmet).
- **Frontend URLs**: `FRONTEND_URL` (Gourmet), `KIDS_FRONTEND_URL` (Kids) — used for Stripe `success_url`/`cancel_url`.
- **Email**: `RESEND_API_KEY` (preferred) **or** `SMTP_HOST`/`SMTP_PORT` + brand-specific user/password pairs.
- **Admin**: `ADMIN_API_KEY` — required for the admin endpoints to be useful.
- **SQLite**: `SQLITE_DB_PATH` (default `/tmp/orders.db` — ephemeral on Railway, intentional).

The CORS allowlist in `server.py:51` is hardcoded to localhost + `donquijote-kids.netlify.app` + `FRONTEND_URL`. If you add a new frontend origin, edit that list.

## Conventions to preserve

- **Don't break the metadata round-trip.** `create_checkout` writes the order into Stripe metadata; `webhook` reads it back. Stripe metadata values are strings — JSON-encode complex fields (`items` is `json.dumps`'d) and parse on the way back.
- **Sheets writes are best-effort.** Wrap new external I/O the same way: log and continue, don't 500 the webhook (Stripe will retry).
- **Brand defaults to `"gourmet"`** for backward compatibility. Preserve that fallback when adding brand-aware code paths.
- **Spanish in user-facing strings, English in code/logs.** The codebase mixes them deliberately — match the surrounding context.
- **No new files unless necessary.** `alerts.py` already holds 8 cooperating classes; prefer adding to it over creating modules. The repo's many `.md` files are user-written docs, not generated — don't auto-rewrite them.
