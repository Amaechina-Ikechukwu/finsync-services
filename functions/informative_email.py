import os
from typing import Iterable, Optional

DEFAULT_FINSYNC_LOGO_URL = (
    "https://firebasestorage.googleapis.com/v0/b/finsync-8ea36.firebasestorage.app/o/icon-dark.png?alt=media&token=1f1862ab-cee1-4972-950c-b11549096d29"
)


def build_informative_html(subject: str, body_text: str, logo_url: Optional[str] = None, recipient_name: Optional[str] = None) -> str:
    """Builds a minimal informative HTML email following the project's design language.

    - Keeps all values local and deterministic (no secret access at import-time).
    - Uses inline styles like other templates in the repo.

    Inputs:
      subject: Short title shown in the header
      body_text: The plain/text body of the informative message (may contain simple HTML)
      logo_url: Optional URL to use as brand logo; falls back to env var or project default
      recipient_name: Optional recipient display name used in greeting

    Returns: full HTML string ready to pass to `resend_service.send_email`.
    """
    logo = (
        logo_url
        or os.getenv("FINSYNC_LOGO_URL")
        or DEFAULT_FINSYNC_LOGO_URL
    )
    name = recipient_name or "Customer"

    if logo:
        brand_html = f'<img src="{logo}" alt="finsync logo" width="28" height="28" style="display:block;border:0;border-radius:6px;" />'
    else:
        brand_html = '<span style="display:inline-block;width:28px;height:28px;background:#ffffff22;border-radius:6px;"></span>'

    # Keep body_text safe-ish: callers can pass already-escaped HTML if needed.
    # We do minimal wrapping and avoid evaluating or importing secrets here.
    return f"""
    <div style="margin:0;padding:24px;background:#f5f5f5;font-family:Segoe UI, Roboto, Helvetica, Arial, sans-serif;color:#111111;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:620px;margin:0 auto;background:#ffffff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06);overflow:hidden;">
        <tr>
          <td style="padding:16px 20px;background:linear-gradient(135deg,#111111,#333333);color:#ffffff;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td style="vertical-align:middle;font-weight:400;font-size:16px;">{brand_html}<span style="margin-top:10px; margin-bottom:20px;">Finsync</span></td>
              </tr>
              <tr>
                <td style="padding-top:6px;font-weight:700;font-size:18px;">{subject}</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:24px;">
            <p style="margin:0 0 12px 0;font-size:14px;color:#4a5568;">Hi {name},</p>
            <div style="margin:0 0 18px 0;font-size:14px;color:#4a5568;">{body_text}</div>
            <p style="margin:18px 0 0 0;font-size:12px;color:#6b7280;">If you have any questions contact <a href="mailto:support@finsyncdigitalservice.com" style="color:#111111;text-decoration:none;">support@finsyncdigitalservice.com</a>.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 20px;background:#f8fafc;color:#64748b;font-size:11px;text-align:center;">
            <div>© {os.getenv('FINSYNC_YEAR', '2025')} Finsync Digital Service</div>
          </td>
        </tr>
      </table>
    </div>
    """


def send_informative_email(subject: str, body_text: str, to: Iterable[str], from_addr: str = "Finsync <info@finsyncdigitalservice.com>", reply_to: Optional[str] = None, logo_url: Optional[str] = None, recipient_name: Optional[str] = None, resend_service_module=None):
    """Helper that builds the informative HTML and sends email using `resend_service.send_email`.

    - Keeps the dependency on `resend_service` lazy: either accept the module as `resend_service_module`
      (useful for tests), or import within the function to avoid secret access at module import time.
    - `to` can be a single string or iterable of addresses.
    """
    # Lazy import to avoid SecretParam access during module import in environments without secrets
    if resend_service_module is None:
        import resend_service as resend_service_module

    html = build_informative_html(subject=subject, body_text=body_text, logo_url=logo_url, recipient_name=recipient_name)

    # Normalize recipients
    if isinstance(to, str):
        to_list = [to]
    else:
        to_list = list(to)

    # Delegate to existing send_email helper
    return resend_service_module.send_email(
        from_addr=from_addr,
        to=to_list,
        subject=subject,
        html=html,
        reply_to=reply_to,
    )
