# Minimal usage example for resend_service.py

import resend_service

if __name__ == "__main__":
    resend_service.send_email(
        from_addr="onboarding@resend.dev",
        to=["delivered@resend.dev"],
        subject="hi",
        html="<strong>hello, world!</strong>",
        reply_to="to@gmail.com",
        bcc="bcc@resend.dev",
        cc=["cc@resend.dev"],
        tags=[
            {"name": "tag1", "value": "tagvalue1"},
            {"name": "tag2", "value": "tagvalue2"},
        ],
    )
