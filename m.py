import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import re
import uuid


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# input loop
def get_user_data():
    print("=== Timetable Generator ===")
    name = input("Enter your name: ")
    start_date = input("Enter start date (YYYY-MM-DD): ")  # for calendar
    days = int(input("How many days do you want in your timetable? "))
    hours_per_day = int(input("How many hours per day do you want to schedule? "))
    
    subjects = []
    print("Enter your subjects (type 'done' when finished):")
    while True:
        subject = input("> ")
        if subject.lower() == "done":
            break
        subjects.append(subject)

    preferences = input("Any special preferences? (e.g., mornings, breaks, etc.): ")

    return {
        "name": name,
        "start_date": start_date,
        "days": days,
        "hours_per_day": hours_per_day,
        "subjects": subjects,
        "preferences": preferences
    }

# generate timetable JSON
def generate_timetable_json(user_data):
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    prompt = f"""
    Create a structured timetable for {user_data['name']}.

    Details:
    - Start date: {user_data['start_date']}
    - {user_data['days']} days
    - {user_data['hours_per_day']} hours per day
    - Subjects: {", ".join(user_data['subjects'])}
    - Preferences: {user_data['preferences']}

    Output in strict JSON format with this schema:
    {{
        "events": [
            {{
                "title": "Subject Name",
                "start": "YYYY-MM-DDTHH:MM:SS",
                "end": "YYYY-MM-DDTHH:MM:SS"
            }}
        ]
    }}

    Rules:
    - Do not include explanations or text outside JSON.
    - Ensure valid JSON only.
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    # extract JSON if Gemini adds extra text
    try:
        # first JSON block
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)
        json.loads(text)  # Validate
    except Exception as e:
        print("Gemini output was invalid JSON, showing raw output:")
        print(text)
        raise e

    return text

# JSON to ICS format
def json_to_ics(json_text, filename="timetable.ics"):
    try:
        data = json.loads(json_text)
        ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\n"

        for event in data["events"]:
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
        print(f" Timetable saved as {filename} (import into Google Calendar)")

    except Exception as e:
        print(" Error converting to ICS:", e)
        print(json_text)

# Main loop
if __name__ == "__main__":
    while True:
        user_data = get_user_data()
        timetable_json = generate_timetable_json(user_data)

        print("\n=== Generated JSON ===\n")
        print(timetable_json)

        json_to_ics(timetable_json, filename=f"{user_data['name']}_timetable.ics")

        again = input("\nDo you want to create another timetable? (y/n): ")
        if again.lower() != "y":
            break
