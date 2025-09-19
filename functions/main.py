import os
import firebase_admin

# Initialize the Firebase Admin SDK once
firebase_admin.initialize_app()

# Import the functions from their respective files to make them deployable
from verification import send_verification_email, handle_verification_click
from notifications import handle_email_notifications
from informative_email import send_informative_email
from informative_http import send_informative
