
import os
import resend
from firebase_functions.params import SecretParam

"""Resend email helper using Firebase Functions Gen 2 SecretParam.

Optimized for Cloud Functions warm instances: initialize Resend once and reuse.
"""

# Declare the secret as a parameter per Firebase Gen 2 docs
RESEND_API_KEY = SecretParam('RESEND_API_KEY')

# In-memory cache (persists for warm function instances)
_CACHED_API_KEY: str | None = None
_RESEND_INITIALIZED = False

def _mask(value: str, show: int = 6) -> str:
    if not value:
        return "<none>"
    if len(value) <= show:
        return "*" * len(value)
    return value[:show] + "*" * (len(value) - show)


def get_resend_api_key():
    # Try SecretParam, then env
    try:
        val = RESEND_API_KEY.value  # Populated only if function declares run_with.secrets
        if val:
            return val
    except Exception:
        # SecretParam not available in this context
        pass
    return os.getenv('RESEND_API_KEY')


def _ensure_resend_initialized():
    global _CACHED_API_KEY, _RESEND_INITIALIZED
    if _RESEND_INITIALIZED and _CACHED_API_KEY:
        return
    key = get_resend_api_key()
    if not key:
        raise ValueError("RESEND_API_KEY is missing. Attach it via run_with.secrets or set env var.")
    _CACHED_API_KEY = key
    resend.api_key = key
    _RESEND_INITIALIZED = True
    print(f"[DEBUG] Resend initialized with API key: {_mask(key)}")

def send_email(
    from_addr,
    to,
    subject,
    html,
    reply_to=None,
    bcc=None,
    cc=None,
    tags=None
):
    _ensure_resend_initialized()
    params = {
        "from": from_addr,
        "to": to,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = reply_to
    if bcc:
        params["bcc"] = bcc
    if cc:
        params["cc"] = cc
    if tags:
        params["tags"] = tags
    try:
        email = resend.Emails.send(params)
        print(f"[DEBUG] Email sent: {email}")
        return email
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return None
