from __future__ import annotations

import os
import json
from typing import Any, Dict, List
from firebase_functions.https_fn import on_request, Request, Response

import resend_service
from informative_email import send_informative_email


def _json_response(payload: Dict[str, Any], status: int = 200) -> Response:
    return Response(
        response=json.dumps(payload),
        status=status,
        mimetype="application/json",
    )

"""To avoid local emulator crashes when Secret Manager isn't available,
you can disable secret binding by setting USE_FIREBASE_SECRETS=false.

Production default: USE_FIREBASE_SECRETS=true (bind secrets for Gen 2).
Local option: set USE_FIREBASE_SECRETS=false and provide RESEND_API_KEY via env.
"""
USE_FIREBASE_SECRETS = os.getenv("USE_FIREBASE_SECRETS", "true").lower() == "true"
_on_request = on_request(secrets=[resend_service.RESEND_API_KEY]) if USE_FIREBASE_SECRETS else on_request()

@_on_request
def send_informative(req: Request) -> Response:
    
    """HTTP endpoint to send an informative email.

    Accepts JSON body:
    {
        "subject": "...",            # required
        "body": "...",               # required (plain text or simple HTML)
        "to": "user@example.com" | ["user@example.com", ...],  # required
        "from": "Finsync <info@finsyncdigitalservice.com>",     # optional
        "replyTo": "support@...",    # optional
        "name": "Alex",              # optional recipient display name
        "logoUrl": "https://..."     # optional
    }
    """

    if req.method != "POST":
        return _json_response({"error": "Use POST with JSON body."}, status=405)

    try:
        data = req.get_json(silent=True) or {}
    except Exception:
        return _json_response({"error": "Invalid JSON."}, status=400)

    subject = data.get("subject")
    body_text = data.get("body")
    to_field = data.get("to")

    if not subject or not body_text or not to_field:
        return _json_response({
            "error": "Missing required fields: subject, body, to"
        }, status=400)

    # Normalize recipients
    if isinstance(to_field, str):
        to_list: List[str] = [to_field]
    elif isinstance(to_field, list) and all(isinstance(x, str) for x in to_field):
        to_list = to_field
    else:
        return _json_response({"error": "'to' must be a string or list of strings."}, status=400)

    from_addr = data.get("from") or "Finsync <info@finsyncdigitalservice.com>"
    reply_to = data.get("replyTo")
    recipient_name = data.get("name")
    logo_url = data.get("logoUrl")

    try:
        result = send_informative_email(
            subject=subject,
            body_text=body_text,
            to=to_list,
            from_addr=from_addr,
            reply_to=reply_to,
            recipient_name=recipient_name,
            logo_url=logo_url,
        )
    except Exception as e:
        return _json_response({"error": f"Failed to send: {e}"}, status=500)

    # Resend returns an email object; surface minimal success info
    return _json_response({
        "ok": True,
        "to": to_list,
        "subject": subject,
        "providerResponse": str(result),
    }, status=200)
