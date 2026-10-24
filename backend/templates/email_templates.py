from typing import Dict, Any, Tuple

def render_booking_confirmation_email(booking: Dict[str, Any]) -> Tuple[str, str]:
    mentor_name = booking.get("mentorName", "Your Mentor")
    student_name = booking.get("userName", "Student")
    slot_start = booking.get("slotStart")
    time_str = slot_start.strftime("%A, %B %d, %Y at %H:%M UTC") if hasattr(slot_start, "strftime") else str(slot_start)
    duration = booking.get("durationMinutes", 30)
    topic = booking.get("topic", "Career Mentorship Discussion")
    meeting_link = booking.get("meetingLink", "#")
    booking_id = booking.get("bookingId", "")

    subject = f"Confirmed: Mentorship Session with {mentor_name}"

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
    <div style="background: linear-gradient(135deg, #2563eb, #1d4ed8); padding: 28px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 700;">Mentorship Session Confirmed</h1>
      <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">GuidEd Career Mentorship</p>
    </div>
    <div style="padding: 28px;">
      <p style="margin: 0 0 16px 0; font-size: 16px;">Hi <strong>{student_name}</strong>,</p>
      <p style="margin: 0 0 20px 0; color: #475569; font-size: 14px; line-height: 1.6;">
        Your mentorship session with <strong>{mentor_name}</strong> has been successfully booked.
      </p>

      <div style="background-color: #f1f5f9; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <tr>
            <td style="padding: 6px 0; color: #64748b; width: 110px;">Date & Time:</td>
            <td style="padding: 6px 0; font-weight: 600; color: #0f172a;">{time_str}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #64748b;">Duration:</td>
            <td style="padding: 6px 0; font-weight: 600; color: #0f172a;">{duration} minutes</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #64748b;">Topic:</td>
            <td style="padding: 6px 0; color: #0f172a;">{topic}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #64748b;">Booking ID:</td>
            <td style="padding: 6px 0; font-family: monospace; color: #475569;">{booking_id}</td>
          </tr>
        </table>
      </div>

      <div style="text-align: center; margin: 28px 0;">
        <a href="{meeting_link}" style="display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; font-size: 15px;">
          Join Google Meet
        </a>
      </div>

      <p style="margin: 0; font-size: 12px; color: #94a3b8; text-align: center;">
        Direct link: <a href="{meeting_link}" style="color: #2563eb;">{meeting_link}</a>
      </p>
    </div>
  </div>
</body>
</html>"""

    return subject, html


def render_booking_cancellation_email(booking: Dict[str, Any]) -> Tuple[str, str]:
    mentor_name = booking.get("mentorName", "Your Mentor")
    student_name = booking.get("userName", "Student")
    slot_start = booking.get("slotStart")
    time_str = slot_start.strftime("%A, %B %d, %Y at %H:%M UTC") if hasattr(slot_start, "strftime") else str(slot_start)
    booking_id = booking.get("bookingId", "")

    subject = f"Cancelled: Mentorship Session with {mentor_name}"

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
    <div style="background: linear-gradient(135deg, #ef4444, #dc2626); padding: 24px; text-align: center; color: #ffffff;">
      <h1 style="margin: 0; font-size: 20px; font-weight: 700;">Session Cancelled</h1>
    </div>
    <div style="padding: 24px;">
      <p style="margin: 0 0 16px 0; font-size: 16px;">Hi <strong>{student_name}</strong>,</p>
      <p style="margin: 0 0 16px 0; color: #475569; font-size: 14px; line-height: 1.6;">
        Your mentorship session with <strong>{mentor_name}</strong> scheduled for <strong>{time_str}</strong> has been cancelled.
      </p>
      <p style="margin: 0 0 16px 0; color: #475569; font-size: 14px;">
        Booking Reference: <code>{booking_id}</code>
      </p>
      <p style="margin: 0; font-size: 13px; color: #64748b;">
        The time slot has been released. You can visit GuidEd at any time to schedule a new call.
      </p>
    </div>
  </div>
</body>
</html>"""

    return subject, html
