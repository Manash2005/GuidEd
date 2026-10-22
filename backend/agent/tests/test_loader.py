from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))

from agent.ingestion.loader import load_mentors

DATA = Path(__file__).resolve().parents[2] / "data" / "mentors.json"

mentors = load_mentors(DATA)
for mentor in mentors:
    print(f"{mentor.get("mentorId")}")