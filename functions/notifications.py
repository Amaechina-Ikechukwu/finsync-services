import os
from datetime import datetime
from firebase_admin import db
from firebase_functions import db_fn
import resend_service  # local email helper

# Default logo (used if not provided in data/notification/user and no env var)
DEFAULT_FINSYNC_LOGO_URL = (
    "https://firebasestorage.googleapis.com/v0/b/finsync-8ea36.firebasestorage.app/o/icon-dark.png?alt=media&token=1f1862ab-cee1-4972-950c-b11549096d29"
)
@db_fn.on_value_created(
    reference="/notifications/users/{userId}/{notificationId}",
    secrets=[resend_service.RESEND_API_KEY]
)
def handle_email_notifications(event: db_fn.Event[dict]) -> None:
    """Listens to RTDB /notifications for new entries and sends emails.

    Expects notification body at /notifications/users/{userId}/{notificationId} to be:
    {
        "type": "NEW_ORDER" | "PASSWORD_RESET",
        "data": { ... }  # optional, type-specific
    }
    userId is taken from the RTDB path, not the notification body.
    """

    # Value written to the RTDB node
    notification = event.data or {}
    
    
    # Validate notification body
    if not isinstance(notification, dict) or "type" not in notification:
        print(f"Error: notification body must be a dict with at least a 'type' field. Got: {notification}")
        return
    notification_type = notification["type"]
    data = notification.get("data", {})
    user_id = event.params.get("userId")
    if not user_id:
        print(f"Error: userId missing in event.params: {event.params}")
        return
    # Fetch the user's details from RTDB
    user_ref = db.reference(f"users/{user_id}")
    
    user_data = user_ref.get()
    print(f'user_data:{user_data}')
    if not user_data:
        print(f"User {user_id} not found.")
        return
    email = user_data.get("email")
    if not email:
        print(f"[WARN] User {user_id} has no 'email' field. Data: {user_data}")
        return

    # Prepare email payload
    # Keep subject from payload if provided; otherwise default
    subject = notification.get("title") or "Debit Alert!"

    # Helper formatters
    def _format_amount(value, currency_symbol="₦"):
        try:
            num = float(value)
            return f"{currency_symbol}{num:,.2f}"
        except Exception:
            return str(value) if value is not None else "—"

    def _fmt(val):
        return str(val) if val not in (None, "") else "—"

    created_at = notification.get("createdAt") or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    first_name = user_data.get("firstName") or user_data.get("name") or "Customer"

    # Map the repository's notification structure (notifications_db.json) to the debit template fields
    def coalesce(*vals):
        for v in vals:
            if v not in (None, ""):
                return v
        return None

    # Try to pretty-format the created_at if iso format provided
    def _human_time(ts: str) -> str:
        try:
            # Basic ISO handling; fall back to original on parse errors
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%d %b, %Y | %I:%M:%S %p")
        except Exception:
            return ts

    # Debit Alert HTML template (fallbacks included)
    def render_debit_alert_html(data: dict) -> str:
        amount = _format_amount(data.get("amount"))
        balance = _format_amount(data.get("balance"))
        account_number = _fmt(data.get("accountNumber"))
        timestamp = _fmt(data.get("dateTime") or created_at)
        narration = _fmt(data.get("narration"))
        reference = _fmt(data.get("reference"))
        bank_name = _fmt(data.get("bankName") or "finsync")
        logo_url = (
            data.get("logoUrl")
            or notification.get("logoUrl")
            or user_data.get("logoUrl")
            or os.getenv("FINSYNC_LOGO_URL")
            or DEFAULT_FINSYNC_LOGO_URL
        )
        # Build brand block (logo if available, else text)
        if logo_url:
            brand_html = f'<img src="{logo_url}" alt="{bank_name} logo" width="28" height="28" style="display:block;border:0;border-radius:6px;" />'
        else:
            brand_html = f'<span style="display:inline-block;width:28px;height:28px;background:#ffffff22;border-radius:6px;"></span>'

        return f"""
                <div style="margin:0;padding:24px;background:#f5f5f5;font-family:Segoe UI, Roboto, Helvetica, Arial, sans-serif;color:#111111;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:620px;margin:0 auto;background:#ffffff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06);overflow:hidden;">
                        <tr>
                            <td style="padding:0;background:linear-gradient(135deg,#111111,#333333);">
                                                                <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr><td style=\"padding:24px 28px;color:#ffffff;\">
                                                                        <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr>
                                                                            <td style=\"font-size:18px;font-weight:600;\">
                                                                                <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr>
                                                                                    <td style=\"vertical-align:middle;\">{brand_html}</td>
                                                                                    <td style=\"vertical-align:middle;padding-left:10px;text-transform:lowercase;\">{bank_name}</td>
                                                                                </tr></table>
                                                                            </td>
                                                                            <td style=\"text-align:right;font-size:18px;font-weight:700;\">Debit Alert!</td>
                                                                        </tr></table>
                                                                </td></tr></table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:28px;">
                                <p style="margin:0 0 12px 0;font-size:14px;color:#4a5568;">Hi {first_name},</p>
                                <p style="margin:0 0 18px 0;font-size:14px;color:#4a5568;">We wish to inform you that a transaction occurred on your account with us.</p>

                                <div style="margin:18px 0 22px 0;text-align:center;">
                                    <div style="font-size:12px;color:#666666;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Debit Amount</div>
                                    <div style="font-size:28px;font-weight:800;color:#111111;">{amount}</div>
                                </div>

                                                                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #e5e7eb;border-radius:10px;">
                                                                    <tr>
                                                                                                        <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                                                                            <div style="font-size:11px;color:#8a94a6;text-transform:uppercase;letter-spacing:0.06em;">Account Balance</div>
                                                                                                            <div style="font-size:14px;font-weight:600;color:#111111;">{balance}</div>
                                                                        </td>
                                                                    </tr>
                                                                    <tr>
                                                                                                        <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                                                                            <div style="font-size:11px;color:#8a94a6;text-transform:uppercase;letter-spacing:0.06em;">Account Number</div>
                                                                                                            <div style="font-size:14px;font-weight:600;color:#111111;">{account_number}</div>
                                                                        </td>
                                                                    </tr>
                                                                    <tr>
                                                                                                        <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                                                                            <div style="font-size:11px;color:#8a94a6;text-transform:uppercase;letter-spacing:0.06em;">Date & Time</div>
                                                                                                            <div style="font-size:14px;font-weight:600;color:#111111;">{timestamp}</div>
                                                                        </td>
                                                                    </tr>
                                                                    <tr>
                                                                                                        <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;">
                                                                            <div style="font-size:11px;color:#8a94a6;text-transform:uppercase;letter-spacing:0.06em;">Narration</div>
                                                                                                            <div style="font-size:14px;font-weight:600;color:#111111;word-break:break-word;">{narration}</div>
                                                                        </td>
                                                                    </tr>
                                                                    <tr>
                                                                        <td style="padding:14px 16px;">
                                                                            <div style="font-size:11px;color:#8a94a6;text-transform:uppercase;letter-spacing:0.06em;">Reference</div>
                                                                                                            <div style="font-size:13px;color:#333333;word-break:break-all;">{reference}</div>
                                                                        </td>
                                                                    </tr>
                                                                </table>

                                <p style="margin:18px 0 0 0;font-size:12px;color:#6b7280;">If you experience any problems kindly contact us at <a href="mailto:support@finsyncdigitalservice.com" style="color:#111111;text-decoration:none;">support@finsyncdigitalservice.com</a> or send a WhatsApp message at <a style=\"color:#111111;text-decoration:none;\" href=\"https://wa.me/2348068810033\">+234 806 881 0033</a>.</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:18px 28px;background:#f8fafc;color:#64748b;font-size:11px;text-align:center;">
                                <div style="margin-bottom:6px;">Follow us on</div>
                                <div>
                                    <a href="https://twitter.com" style="color:#111111;text-decoration:none;margin:0 6px;">Twitter</a>
                                    <a href="https://facebook.com" style="color:#111111;text-decoration:none;margin:0 6px;">Facebook</a>
                                    <a href="https://instagram.com" style="color:#111111;text-decoration:none;margin:0 6px;">Instagram</a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
        """

    # Always map and render the Debit Alert template (no condition by type/flow)
    mapped = {
        "amount": coalesce(data.get("amount")),
        "balance": coalesce(data.get("balance"), user_data.get("accountBalance")),
        "accountNumber": coalesce(user_data.get("accountNumber"), user_data.get("accountNo")),
        "dateTime": _human_time(coalesce(notification.get("createdAt"), data.get("dateTime"), created_at)),
        "narration": coalesce(data.get("description"), notification.get("body")),
        "reference": coalesce(data.get("transactionId"), data.get("reference"), notification.get("id")),
        "bankName": coalesce(user_data.get("bankName"), "Finsync"),
    }
    html = render_debit_alert_html(mapped)
    params = {
        "from": "Finsync <alerts@finsyncdigitalservice.com>",
        "to": [email],
        "subject": subject,
        "html": html,
    }

    # Send the email via Resend
    try:
        resend_service.send_email(
            from_addr=params["from"],
            to=params["to"],
            subject=params["subject"],
            html=params["html"],
        )
        print(f"Sent '{notification_type}' email to {user_data['email']}")
    except Exception as e:
        print(f"Error sending email via Resend: {e}")