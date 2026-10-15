import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/auto"
DATA_FILE = "students.json"

# --- Database Helper Functions ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- Action Executors (Python Logic) ---
def execute_action(command):
    action = command.get("action")
    
    if action == "clarify":
        return {"ai_question": command.get("question")}
    
    students = load_data()
    
    if action == "get_student":
        # 'roll_no' ya 'roll' dono ko handle karega
        roll = command.get("roll_no") or command.get("roll")
        for s in students:
            if s["roll"] == roll:
                present = s["attendance_5_days"].count("Present")
                percentage = (present / s["total_days"]) * 100
                marks_deducted = 0 if percentage >= 75 else 5
                return {
                    "roll": s["roll"],
                    "name": s["name"],
                    "attendance_percentage": f"{percentage:.1f}%",
                    "marks_deducted": marks_deducted,
                    "status": "Eligible" if percentage >= 75 else "Short Attendance Warning"
                }
        return {"error": f"Student with roll number {roll} not found."}

    elif action == "get_all_attendance":
        return students

    elif action == "get_class_average":
        if not students:
            return {"error": "No student records found."}
        total_percentages = []
        for s in students:
            present = s["attendance_5_days"].count("Present")
            total_percentages.append((present / s["total_days"]) * 100)
        avg = sum(total_percentages) / len(students)
        return {"class_average_attendance": f"{avg:.1f}%"}

    elif action == "update_attendance":
        roll = command.get("roll_no") or command.get("roll")
        day_str = str(command.get("day"))  # e.g., "Day 3" ya "3"
        status = command.get("status")  # Present, Absent, Unrecorded
        
        try:
            day_num = int(''.join(filter(str.isdigit, day_str)))
            day_index = day_num - 1
        except ValueError:
            return {"error": "Invalid day format."}

        for s in students:
            if s["roll"] == roll:
                if 0 <= day_index < len(s["attendance_5_days"]):
                    s["attendance_5_days"][day_index] = status if status != "Unrecorded" else "Absent"
                    save_data(students)
                    return {"message": "Attendance updated successfully", "student": s}
                return {"error": "Invalid day range (1-5)."}
        return {"error": f"Student with roll number {roll} not found."}

    return command

# --- AI Interpreter ---
def interpret_instruction(user_instruction):
    if not API_KEY:
        return {"error": "OPENROUTER_API_KEY is missing from your .env file."}

    system_prompt = """
You are an assistant for a student attendance management system.
Convert the user's instruction into exactly one JSON object.
Do not calculate attendance yourself. Python will do calculations.

Supported actions:
1. get_student: requires roll (use key "roll")
2. get_all_attendance: requires no other fields
3. get_class_average: requires no other fields
4. update_attendance: requires roll, day, and status

For update_attendance, status must be Present, Absent, or Unrecorded.
Use Unrecorded when the user asks to remove or delete a day's attendance.

Rules:
- Never invent a roll number or day.
- If required information is missing or unclear, use action "clarify".
- Return pure JSON only, without any markdown tags like ```json or ```.

JSON formats:
{"action":"get_student","roll":"001"}
{"action":"get_all_attendance"}
{"action":"get_class_average"}
{"action":"update_attendance","roll":"002","day":"Day 3","status":"Present"}
{"action":"clarify","question":"Which student's roll number do you mean?"}
"""

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_instruction},
                ],
                "max_tokens": 600,
                "temperature": 0,
            },
            timeout=60,
        )

        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        if not content:
            return {"error": "The AI returned an empty response."}

        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)

    except Exception as error:
        return {"error": f"API request failed: {error}"}


# --- Main Application Loop ---
if __name__ == "__main__":
    print("=== AI Attendance Management System Ready ===")
    while True:
        prompt = input("\nTerminal Prompt > ").strip()
        if prompt.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        if not prompt:
            continue

        command = interpret_instruction(prompt)
        result = execute_action(command)

        print("\n[Execution Result]:")
        print(json.dumps(result, indent=2))