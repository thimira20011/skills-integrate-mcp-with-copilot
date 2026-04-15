"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import json
import os
from pathlib import Path
import secrets
from datetime import datetime, timedelta, timezone

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

teachers_file = current_dir / "teachers.json"
SESSION_TTL_HOURS = 12
active_sessions = {}


def load_teacher_credentials():
    if not teachers_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Teacher credentials file is missing"
        )

    try:
        with open(teachers_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to read teacher credentials"
        ) from error

    teachers = payload.get("teachers", [])
    return {
        record["username"]: record["password"]
        for record in teachers
        if "username" in record and "password" in record
    }


def issue_session_token(username: str):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    active_sessions[token] = {
        "username": username,
        "expires_at": expires_at
    }
    return token


def get_authenticated_teacher(token: str):
    session = active_sessions.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")

    if session["expires_at"] < datetime.now(timezone.utc):
        active_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired")

    return session["username"]

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def login(username: str, password: str):
    credentials = load_teacher_credentials()
    if credentials.get(username) != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = issue_session_token(username)
    return {
        "message": "Login successful",
        "username": username,
        "token": token,
        "expires_in_hours": SESSION_TTL_HOURS
    }


@app.get("/auth/me")
def get_current_teacher(x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")):
    if not x_teacher_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    username = get_authenticated_teacher(x_teacher_token)
    return {"username": username}


@app.post("/auth/logout")
def logout(x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")):
    if not x_teacher_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    username = get_authenticated_teacher(x_teacher_token)
    active_sessions.pop(x_teacher_token, None)
    return {"message": f"Logged out {username}"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")
):
    """Sign up a student for an activity"""
    if not x_teacher_token:
        raise HTTPException(status_code=401, detail="Teacher login required")

    get_authenticated_teacher(x_teacher_token)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")
):
    """Unregister a student from an activity"""
    if not x_teacher_token:
        raise HTTPException(status_code=401, detail="Teacher login required")

    get_authenticated_teacher(x_teacher_token)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
