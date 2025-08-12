# Finsync Services — Firebase Functions (Python)

Serverless backend for Finsync built on Firebase Cloud Functions (Gen 2) with Python 3.13 and the Realtime Database. It handles user email verification and transactional email notifications via Resend.

## Features

- Realtime Database triggers for:
  - New user creation → sends verification email
  - New notification entry → sends debit alert email
- HTTP endpoint to handle verification link clicks
- Resend email integration with secret-managed API key
- Works locally with Firebase Emulators and deploys to Firebase project

## Repository structure

- `firebase.json` / `.firebaserc` — Firebase project & emulator config
- `functions/` — Python Cloud Functions source
  - `main.py` — initializes Firebase Admin SDK and exports functions
  - `verification.py` — verification trigger and HTTP handler
  - `notifications.py` — notification-to-email pipeline
  - `resend_service.py` — shared Resend email helper (with SecretParam)
  - `requirements.txt` — Python dependencies
  - `test_resend.py` — minimal local test for Resend helper

## Functions overview

- `send_verification_email` (RTDB on create)
  - Trigger: `/users/{userId}`
  - Generates a token, stores it under `users/{userId}/verification`, and emails a verification link.
- `handle_verification_click` (HTTP)
  - Path: `/handle_verification_click?token=...`
  - Validates token and expiry; marks user as verified.
- `handle_email_notifications` (RTDB on create)
  - Trigger: `/notifications/users/{userId}/{notificationId}`
  - Builds a well-formatted “Debit Alert” email and sends via Resend.

## Prerequisites

- Python 3.13
- Firebase CLI (v13+) and a Firebase project
- A Resend account + API key

## Setup

1) Install Firebase CLI:

```powershell
npm i -g firebase-tools
firebase --version
```

2) Python environment (from repository root):

```powershell
# Create & activate venv inside functions/
cd functions
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

3) Configure secrets/env vars:

- Required for email sending:
  - `RESEND_API_KEY`
- Optional for branding / links:
  - `FINSYNC_LOGO_URL` (fallback is included)
  - `FUNCTION_BASE_URL` or `VERIFICATION_BASE_URL` (used in verification links)

During local development (current PowerShell session only):

```powershell
$env:RESEND_API_KEY = "<your-resend-api-key>"
# Optional
$env:FINSYNC_LOGO_URL = "https://your.cdn/logo.png"
$env:FUNCTION_BASE_URL = "http://localhost:5001/finsync-8ea36/us-central1"
```

For deployed functions (recommended):

```powershell
firebase functions:secrets:set RESEND_API_KEY
# Optional additional secrets
firebase functions:secrets:set FINSYNC_LOGO_URL
firebase functions:secrets:set FUNCTION_BASE_URL
```

## Local development (Emulators)

Start from repo root:

```powershell
# Ensure your venv is active in functions/ if you plan to run any local scripts
firebase emulators:start
```

What’s emulated (per `firebase.json`):
- Auth (9099)
- Realtime Database (9102)
- Functions (5001)
- Emulator UI enabled

### Triggering flows locally

- Create a user (via Emulator UI or write to RTDB):
  - Path: `/users/{userId}` (object should contain at least `email`)
  - This triggers `send_verification_email`.
- Create a notification:
  - Path: `/notifications/users/{userId}/{notificationId}`
  - This triggers `handle_email_notifications`.

Example notification payload:

```json
{
  "type": "DEBIT_ALERT",
  "title": "Debit Alert!",
  "createdAt": "2025-01-01T12:00:00Z",
  "data": {
    "amount": 5000,
    "balance": 25000,
    "description": "Transfer to ABC",
    "reference": "TXN-123",
    "transactionId": "TXN-123",
    "dateTime": "2025-01-01T12:00:00Z"
  }
}
```

User record example (fields accessed by functions):

```json
{
  "email": "user@example.com",
  "firstName": "Ada",
  "accountBalance": 25000,
  "accountNumber": "0123456789",
  "bankName": "Finsync",
  "logoUrl": "https://.../logo.png"
}
```

## Deployment

Make sure you’re targeting the right project (see `.firebaserc`):

```powershell
firebase use finsync-8ea36
```

Deploy functions:

```powershell
firebase deploy --only functions
```

Secrets must be set in the target project before deploy or via your CI/CD.

## Email sending with Resend

The helper in `functions/resend_service.py` centralizes authentication and sending:
- Uses Firebase `SecretParam('RESEND_API_KEY')` in production
- Falls back to `$env:RESEND_API_KEY` in local runs
- Caches initialization for warm instances

Minimal local test:

```powershell
# In functions/ with venv activated
$env:RESEND_API_KEY = "<your-resend-api-key>"
python .\test_resend.py
```

## Configuration reference

- `RESEND_API_KEY` (required) — Resend API key for email delivery
- `FUNCTION_BASE_URL` or `VERIFICATION_BASE_URL` (optional) — base used to build verification links
- `FINSYNC_LOGO_URL` (optional) — logo URL in emails; fallback is baked in the code

The notifications email template will pick logo in this order:
1. `data.logoUrl`
2. `notification.logoUrl`
3. `user_data.logoUrl`
4. `FINSYNC_LOGO_URL`
5. Built-in default

## Troubleshooting

- “RESEND_API_KEY is missing” → set it for local runs or via `firebase functions:secrets:set`.
- No emails received locally → check your Resend account’s allowed senders and use their test inbox addresses (e.g., `delivered@resend.dev`) when testing.
- RTDB triggers not firing → confirm you’re writing under the correct paths and using the same project in the emulator.
- HTTP verification handler → ensure your `FUNCTION_BASE_URL` matches emulator or production and the token query param is present.

## License

Proprietary — All rights reserved.
