import asyncio
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_ENABLED
)
from db.mongo import get_database
from templates.email_templates import (
    render_booking_confirmation_email,
    render_booking_cancellation_email
)

def _send_smtp_sync(recipient: str, subject: str, html_body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [recipient], msg.as_string())
        return True
    except Exception as e:
        print(f"Warning: SMTP email delivery failed to {recipient}: {e}")
        return False

async def send_email_idempotent(
    recipient: str,
    subject: str,
    html_content: str,
    idempotency_key: str,
    booking_id: Optional[str] = None
) -> Dict[str, Any]:
    db = get_database()

    # Idempotency check: skip if already successfully sent
    if db is not None:
        existing = await db["notifications"].find_one({"idempotencyKey": idempotency_key})
        if existing and existing.get("status") == "sent":
            return {
                "status": "skipped",
                "reason": "already_sent",
                "idempotencyKey": idempotency_key
            }

    delivery_status = "sent"

    if SMTP_ENABLED and SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        success = await asyncio.to_thread(_send_smtp_sync, recipient, subject, html_content)
        if not success:
            delivery_status = "failed"
    else:
        # Simulated delivery for local development & automated testing
        delivery_status = "simulated"

    now = datetime.now(timezone.utc)
    notif_doc = {
        "idempotencyKey": idempotency_key,
        "bookingId": booking_id,
        "recipient": recipient,
        "subject": subject,
        "status": "sent" if delivery_status in ("sent", "simulated") else "failed",
        "deliveryMode": delivery_status,
        "sentAt": now
    }

    if db is not None:
        try:
            await db["notifications"].update_one(
                {"idempotencyKey": idempotency_key},
                {"$set": notif_doc},
                upsert=True
            )
        except Exception as e:
            print(f"Warning: Failed to persist email notification status: {e}")

    return {
        "status": notif_doc["status"],
        "deliveryMode": delivery_status,
        "idempotencyKey": idempotency_key
    }

async def send_booking_confirmation(booking: Dict[str, Any]) -> Dict[str, Any]:
    booking_id = booking.get("bookingId", "")
    recipient = booking.get("userEmail", "")
    mentor_email = booking.get("mentorEmail", "")
    if not recipient and not mentor_email:
        return {"status": "skipped", "reason": "missing_recipient"}

    subject, html = render_booking_confirmation_email(booking)
    student_res = {"status": "skipped", "reason": "no_student_email"}
    if recipient:
        idempotency_key = f"email_confirm_{booking_id}"
        student_res = await send_email_idempotent(recipient, subject, html, idempotency_key, booking_id)

    if mentor_email:
        mentor_key = f"email_confirm_mentor_{booking_id}"
        await send_email_idempotent(mentor_email, subject, html, mentor_key, booking_id)

    return student_res if recipient else {"status": "sent"}

async def send_booking_cancellation(booking: Dict[str, Any]) -> Dict[str, Any]:
    booking_id = booking.get("bookingId", "")
    recipient = booking.get("userEmail", "")
    mentor_email = booking.get("mentorEmail", "")
    if not recipient and not mentor_email:
        return {"status": "skipped", "reason": "missing_recipient"}

    subject, html = render_booking_cancellation_email(booking)
    student_res = {"status": "skipped", "reason": "no_student_email"}
    if recipient:
        idempotency_key = f"email_cancel_{booking_id}"
        student_res = await send_email_idempotent(recipient, subject, html, idempotency_key, booking_id)

    if mentor_email:
        mentor_key = f"email_cancel_mentor_{booking_id}"
        await send_email_idempotent(mentor_email, subject, html, mentor_key, booking_id)

    return student_res if recipient else {"status": "sent"}
