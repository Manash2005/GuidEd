from pathlib import Path
from typing import Any
import json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_FILE = ROOT / "data" / "mentors.json"

def load_mentors(data: Path | str | None = None) -> list[dict[str, Any]]:
    if data is None:
        data = DEFAULT_DATA_FILE
    elif isinstance(data, str):
        data = Path(data)

    with data.open("r", encoding="utf-8") as file:
        mentors = json.load(file)

    if not isinstance(mentors, list):
        raise ValueError("Expected the JSON file to contain list")

    seen_ids = set()

    for index, mentor in enumerate(mentors):
        if not isinstance(mentor, dict):
            raise ValueError(f"Record at {index} is not a JSON object")

        mentor_id = mentor.get("mentorId")

        if mentor_id in seen_ids:
            raise ValueError(f"Duplicate mentor ID found : {mentor_id}")

        seen_ids.add(mentor_id)

    print(f"Successfully loaded {len(mentors)} mentors")
    return mentors