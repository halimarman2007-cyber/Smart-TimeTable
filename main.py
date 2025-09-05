from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
from datetime import datetime
import uuid
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware



# Load env vars
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

# Allow frontend (React) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in prod, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class TimetableRequest(BaseModel):
    name: str
    start_date: str = Field(..., alias="startDate")
    days: int = Field(..., alias="numberOfDays")
    hours_per_day: int = Field(..., alias="hoursPerDay")
    subjects: list[str]
    preferences: str = ""

    class Config:
        populate_by_name = True


def generate_timetable_logic(user_data: TimetableRequest):
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
    Create a structured timetable for {user_data.name}.
    Details:
    - Start date: {user_data.start_date}
    - {user_data.days} days
    - {user_data.hours_per_day} hours per day
    - Subjects: {", ".join(user_data.subjects)}
    - Preferences: {user_data.preferences}

    Output in strict JSON format with schema:
    {{
        "events": [
            {{
                "title": "Subject Name",
                "start": "YYYY-MM-DDTHH:MM:SS",
                "end": "YYYY-MM-DDTHH:MM:SS"
            }}
        ]
    }}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Extract JSON safely
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)

    return json.loads(text)

@app.post("/generate")
def generate_timetable(user_data: TimetableRequest):
    timetable = generate_timetable_logic(user_data)
    return timetable

@app.post("/generate-ics")
def generate_ics(user_data: TimetableRequest):
    timetable = generate_timetable_logic(user_data)
    filename = f"{user_data.name}_timetable.ics"

    # Convert timetable JSON → ICS
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\n"
    for event in timetable["events"]:
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        uid = str(uuid.uuid4())
        dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        ics_content += "BEGIN:VEVENT\n"
        ics_content += f"UID:{uid}\n"
        ics_content += f"DTSTAMP:{dtstamp}\n"
        ics_content += f"SUMMARY:{event['title']}\n"
        ics_content += f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}\n"
        ics_content += f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}\n"
        ics_content += "END:VEVENT\n"

    ics_content += "END:VCALENDAR"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics_content)

    return FileResponse(filename, media_type="text/calendar", filename=filename)



