import os
import secrets
from datetime import datetime, timedelta, timezone
from flask import redirect
import firebase_admin
from firebase_admin import db
from firebase_functions import db_fn
from firebase_functions.https_fn import on_request, Request
import resend_service  # Import from the local resend_service.py file

# Default base URL for production — set to the direct Cloud Run URL of the function
# Example provided: https://handle-verification-click-5czh4imcxq-uc.a.run.app
DEFAULT_FUNCTION_BASE_URL = "https://handle-verification-click-5czh4imcxq-uc.a.run.app"

@db_fn.on_value_created(
    reference="/users/{userId}",
    secrets=[resend_service.RESEND_API_KEY]
)
def send_verification_email(event: db_fn.Event[dict]) -> None:
    """Triggers when a new user is created in RTDB and sends a verification email."""
   
    # Get user data from the event
    user_data = event.data
    user_id = event.params["userId"]

    if not user_data or user_data.get("isVerified"):
        print(f"User {user_id} already verified or data is missing.")
        return

    # Generate a secure token
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Update the user's record in RTDB with the token under a nested key
    user_ref = db.reference(f"/users/{user_id}")
    user_ref.child("verification").update({
        "token": token,
        "expires": expires.isoformat(),
    })

    # Build verification URL using a simple, configurable base with a safe default
    base_url = os.getenv("FUNCTION_BASE_URL") or os.getenv("VERIFICATION_BASE_URL") or DEFAULT_FUNCTION_BASE_URL
    function_path = "handle_verification_click"
    base_clean = base_url.rstrip("/")
    # If base already points directly to the function (e.g., run.app) or ends with the function name, don't append it again
    if base_clean.lower().endswith(f"/{function_path}") or ("run.app" in base_clean.lower()):
        verification_url = f"{base_clean}?token={token}"
    else:
        verification_url = f"{base_clean}/{function_path}?token={token}"
    # Try common locations for email (flat or nested under profile)
    email = user_data.get("email") or user_data.get("profile", {}).get("email")
    if not email:
        print(f"[WARN] User {user_id} has no 'email' field. Data: {user_data}")
        return
    
    # Send email using resend_service.send_email
    params = {
        "from": "Onboarding <onboarding@finsyncdigitalservice.com>",
    "to": [email],
        "subject": "Welcome! Please Verify Your Email",
        "html": f"""
            <h1>Welcome to Our App!</h1>
            <p>Click the link below to verify your email. It expires in 1 hour.</p>
            <a href=\"{verification_url}\"><strong>Verify My Email</strong></a>
        """,
    }
    result = resend_service.send_email(
        from_addr=params["from"],
        to=params["to"],
        subject=params["subject"],
        html=params["html"]
    )
    if not result:
        print("Failed to send email via Resend.")
        return
    print(f"Verification email sent to {email}")

@on_request()
def handle_verification_click(req: Request) -> redirect:
    """Handles the verification link clicked by the user."""
    
    token = req.args.get("token")
    if not token:
        return "Invalid request: Token is missing.", 400

    # Query RTDB to find the user with the matching token
    users_ref = db.reference("users")
    # Query by nested verification token
    results = users_ref.order_by_child("verification/token").equal_to(token).limit_to_first(1).get()

    if not results:
        return "Invalid or expired verification link.", 404

    # Extract user ID and data from the query results
    user_id, user_data = next(iter(results.items()))

    # Check if the token has expired
    verification = user_data.get("verification", {})
    expires_str = verification.get("expires")
    if not expires_str:
        return "Invalid or expired verification link.", 404
    expires = datetime.fromisoformat(expires_str)
    if datetime.now(timezone.utc) > expires:
        return "Verification link has expired.", 400

    # Update user record to mark as verified
    user_ref = db.reference(f"users/{user_id}")
    user_ref.update({
        "isVerified": True,
    })
    # Clear nested verification fields
    user_ref.child("verification").update({
        "token": None,
        "expires": None,
    })

    print(f"User {user_id} successfully verified.")
    # Redirect to your website's success page
    return redirect("https://your-website.com/verification-success", code=302)