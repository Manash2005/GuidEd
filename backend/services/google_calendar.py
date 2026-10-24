import httpx
from datetime import datetime
from typing import Optional, Dict, Any

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
    GOOGLE_CALENDAR_ID
)

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3/calendars"

def is_google_calendar_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN)

async def get_google_access_token() -> Optional[str]:
    if not is_google_calendar_configured():
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": GOOGLE_REFRESH_TOKEN,
                    "grant_type": "refresh_token"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("access_token")
            print(f"Warning: Google OAuth token refresh failed ({resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        print(f"Warning: Failed to refresh Google access token: {e}")
        return None

async def create_calendar_event(
    booking_id: str,
    mentor_id: str,
    mentor_name: str,
    student_name: str,
    student_email: str,
    slot_start: datetime,
    slot_end: datetime,
    topic: str
) -> Dict[str, Optional[str]]:
    fallback_link = f"https://meet.google.com/lookup/guided-{booking_id[:8]}"

    if not is_google_calendar_configured():
        return {
            "calendarEventId": None,
            "meetingLink": fallback_link
        }

    token = await get_google_access_token()
    if not token:
        return {
            "calendarEventId": None,
            "meetingLink": fallback_link
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    event_body = {
        "summary": f"GuidEd Mentorship: {mentor_name} & {student_name}",
        "description": f"Mentorship Discussion: {topic}\nMentor ID: {mentor_id}\nBooking ID: {booking_id}",
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "attendees": [{"email": student_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet_{booking_id}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    }

    url = f"{CALENDAR_API_BASE}/{GOOGLE_CALENDAR_ID}/events?conferenceDataVersion=1"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=event_body)
            if resp.status_code in (200, 201):
                data = resp.json()
                event_id = data.get("id")

                # Extract Meet link from hangoutLink or conferenceData entryPoints
                meet_link = data.get("hangoutLink")
                if not meet_link:
                    entry_points = data.get("conferenceData", {}).get("entryPoints", [])
                    for ep in entry_points:
                        if ep.get("entryPointType") == "video":
                            meet_link = ep.get("uri")
                            break

                return {
                    "calendarEventId": event_id,
                    "meetingLink": meet_link or fallback_link
                }
            else:
                print(f"Warning: Google Calendar API error ({resp.status_code}): {resp.text}")
                return {
                    "calendarEventId": None,
                    "meetingLink": fallback_link
                }
    except Exception as e:
        print(f"Warning: Exception calling Google Calendar API: {e}")
        return {
            "calendarEventId": None,
            "meetingLink": fallback_link
        }

async def delete_calendar_event(calendar_event_id: str) -> bool:
    if not is_google_calendar_configured() or not calendar_event_id:
        return False

    token = await get_google_access_token()
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{CALENDAR_API_BASE}/{GOOGLE_CALENDAR_ID}/events/{calendar_event_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=headers)
            return resp.status_code in (200, 204, 404, 410)
    except Exception as e:
        print(f"Warning: Failed to delete Google Calendar event: {e}")
        return False
