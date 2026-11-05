import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL_NAME = "gemini-2.5-flash"
TORONTO_TZ = ZoneInfo("America/Toronto")

# name, zone, what it trains, typical session in minutes
CATALOG = [
    ("Treadmill 1", "Cardio", "Cardio", 30),
    ("Treadmill 2", "Cardio", "Cardio", 30),
    ("Treadmill 3", "Cardio", "Cardio", 30),
    ("Treadmill 4", "Cardio", "Cardio", 30),
    ("Elliptical 1", "Cardio", "Cardio", 20),
    ("Elliptical 2", "Cardio", "Cardio", 20),
    ("Bike 1", "Cardio", "Cardio", 20),
    ("Bike 2", "Cardio", "Cardio", 20),
    ("Rower", "Cardio", "Cardio, back", 15),
    ("Stair climber", "Cardio", "Cardio, legs", 15),
    ("Squat rack 1", "Free weights", "Quads, glutes", 20),
    ("Squat rack 2", "Free weights", "Quads, glutes", 20),
    ("Flat bench 1", "Free weights", "Chest, triceps", 15),
    ("Flat bench 2", "Free weights", "Chest, triceps", 15),
    ("Incline bench", "Free weights", "Upper chest, shoulders", 15),
    ("Dumbbell area", "Free weights", "Full body", 20),
    ("Leg press", "Machines", "Quads, glutes", 12),
    ("Hack squat", "Machines", "Quads, glutes", 12),
    ("Leg extension", "Machines", "Quads", 10),
    ("Leg curl", "Machines", "Hamstrings", 10),
    ("Lat pulldown", "Machines", "Back", 12),
    ("Seated row", "Machines", "Back", 12),
    ("Cable station", "Machines", "Back, chest, arms", 15),
    ("Chest press", "Machines", "Chest, triceps", 12),
    ("Shoulder press", "Machines", "Shoulders", 12),
    ("Pec deck", "Machines", "Chest", 10),
    ("Assisted pull-up", "Machines", "Back, biceps", 10),
    ("Biceps curl", "Machines", "Biceps", 8),
    ("Dip station", "Machines", "Triceps, chest", 10),
]

USUAL_SESSION = {name: usual for name, _, _, usual in CATALOG}

SUGGESTIONS = [
    "I want chest. What's actually free?",
    "Both squat racks are awkward to wait on. What else hits legs?",
    "I have 20 minutes. Build a back workout from open machines.",
]

SYSTEM = """You help a person who is already at a public gym avoid waiting on taken equipment.
You receive the live floor, split into available and in_use.
Recommend only machines listed under available.
If the machines they would normally use are in use, say those are taken and point them to a free machine that trains the same muscles.
Each in-use machine includes minutes_in_use, usual_session_minutes, and estimated_wait_minutes. The estimate is the usual session minus time already in use. Mention that estimate when it helps someone decide whether to wait. Do not invent a different wait. If estimated_wait_minutes is 0, the usual session is already over.
A machine with yours set to true is the user's own session. They are already on it. Do not treat it as someone else to wait on, and do not recommend it as a free machine.
Give a short plan they can follow right now: where to go, in order.
Do not invent equipment that is not on the floor.
If an earlier message conflicts with the live floor, follow the live floor."""


def has_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return False
    lowered = key.lower()
    return lowered not in {"your_google_api_key_here", "your-key-here"}


def usual_session(machine):
    return machine.get("usual_minutes", USUAL_SESSION[machine["name"]])


def estimated_wait(machine):
    return max(usual_session(machine) - machine["minutes"], 0)


def fresh_floor():
    floor = []
    for name, zone, muscles, usual in CATALOG:
        in_use = random.random() < 0.45
        floor.append(
            {
                "name": name,
                "zone": zone,
                "muscles": muscles,
                "usual_minutes": usual,
                "in_use": in_use,
                "booked_by_you": False,
                "minutes": random.randint(4, max(4, usual - 2)) if in_use else 0,
            }
        )
    return floor


def claim_machine(floor, name):
    for machine in floor:
        if machine["name"] == name and not machine["in_use"]:
            machine["in_use"] = True
            machine["minutes"] = 0
            machine["booked_by_you"] = True
            return True
    return False


def release_machine(floor, name):
    for machine in floor:
        if machine["name"] == name and machine.get("booked_by_you"):
            machine["in_use"] = False
            machine["minutes"] = 0
            machine["booked_by_you"] = False
            return True
    return False


def refresh_floor(floor):
    for machine in floor:
        usual = usual_session(machine)
        machine["usual_minutes"] = usual
        if machine.get("booked_by_you"):
            continue
        if random.random() < 0.28:
            machine["in_use"] = not machine["in_use"]
            machine["minutes"] = (
                random.randint(1, max(1, usual // 2)) if machine["in_use"] else 0
            )
        elif machine["in_use"]:
            machine["minutes"] += random.randint(1, 4)


def floor_for_model(floor):
    available = []
    in_use = []
    for machine in floor:
        entry = {
            "name": machine["name"],
            "zone": machine["zone"],
            "trains": machine["muscles"],
        }
        if machine["in_use"]:
            entry["minutes_in_use"] = machine["minutes"]
            entry["usual_session_minutes"] = usual_session(machine)
            entry["estimated_wait_minutes"] = estimated_wait(machine)
            if machine.get("booked_by_you"):
                entry["yours"] = True
            in_use.append(entry)
        else:
            available.append(entry)
    return {"available": available, "in_use": in_use}


def show_html(html):
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def usage_lines(machine):
    remaining = estimated_wait(machine)
    if remaining == 0:
        wait_line = "Usual session is over"
    else:
        wait_line = f"About {remaining} min left"
    if machine.get("booked_by_you") and machine["minutes"] == 0:
        status_line = "Your session, just started"
    elif machine.get("booked_by_you"):
        status_line = f"Your session for {machine['minutes']} min"
    else:
        status_line = f"In use for {machine['minutes']} min"
    return status_line, wait_line


def render_card(machine):
    if machine.get("booked_by_you"):
        status_line, wait_line = usage_lines(machine)
        accent = "#175cd3"
        background = "#f5f8ff"
    elif machine["in_use"]:
        status_line, wait_line = usage_lines(machine)
        accent = "#b42318"
        background = "#fff7f6"
    else:
        status_line = "Available"
        wait_line = "Open now"
        accent = "#067647"
        background = "#f4fbf7"
    show_html(
        f"""
        <div style="background:{background};border:1px solid #eceae6;border-left:4px solid {accent};border-radius:10px;padding:12px 14px;margin-bottom:10px;">
            <div style="font-weight:600;font-size:1rem;">{machine["name"]}</div>
            <div style="color:#667085;font-size:0.85rem;margin-top:2px;">{machine["muscles"]}</div>
            <div style="color:{accent};font-weight:600;font-size:0.9rem;margin-top:8px;">{status_line}</div>
            <div style="color:#667085;font-size:0.85rem;margin-top:2px;">{wait_line}</div>
        </div>
        """
    )


def ask_assistant(question, floor, history):
    if not has_api_key():
        return (
            "Add your Google API key to `.env` and restart the app. "
            "The floor board still works without it."
        )

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"].strip().strip('"').strip("'"))
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM)
    prior = "\n".join(
        f"{message['role']}: {message['content']}" for message in history[-6:]
    )
    prompt = (
        "Live floor status:\n"
        f"{json.dumps(floor_for_model(floor), indent=2)}\n\n"
        f"Conversation so far:\n{prior or '(none)'}\n\n"
        f"Gym user: {question}"
    )
    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
    except Exception:
        return (
            "The assistant couldn't reach Gemini. Check the API key in `.env` "
            "and try again. The status board is still current."
        )
    return text or "The assistant didn't return a recommendation. Try asking another way."


def ensure_state():
    if "floor" not in st.session_state:
        st.session_state.floor = fresh_floor()
        st.session_state.updated_at = datetime.now(TORONTO_TZ)
        st.session_state.messages = []


def render_board():
    floor = st.session_state.floor
    open_count = sum(not machine["in_use"] for machine in floor)
    busy_count = len(floor) - open_count
    updated = st.session_state.updated_at.astimezone(TORONTO_TZ).strftime("%I:%M %p").lstrip("0")

    title_col, action_col = st.columns([4, 1])
    with title_col:
        st.title("What's free right now")
        st.caption(
            f"Updated {updated}. Simulated floor. A taken machine shows how long "
            "someone has been on it, and about how long is left."
        )
    with action_col:
        st.write("")
        if st.button("Refresh status", width="stretch"):
            refresh_floor(floor)
            st.session_state.updated_at = datetime.now(TORONTO_TZ)
            st.rerun()

    metric_cols = st.columns(3)
    metric_cols[0].metric("Available", open_count)
    metric_cols[1].metric("In use", busy_count)
    metric_cols[2].metric("On the floor", len(floor))

    render_booking(floor)

    filter_cols = st.columns(2)
    zone = filter_cols[0].selectbox(
        "Area",
        ["All", "Cardio", "Free weights", "Machines"],
    )
    status = filter_cols[1].selectbox("Status", ["All", "Available", "In use"])

    visible = floor
    if zone != "All":
        visible = [machine for machine in visible if machine["zone"] == zone]
    if status == "Available":
        visible = [machine for machine in visible if not machine["in_use"]]
    elif status == "In use":
        visible = [machine for machine in visible if machine["in_use"]]

    if not visible:
        st.info("Nothing matches this filter. Switch it to see the rest of the floor.")
        return

    zones = []
    for machine in visible:
        if machine["zone"] not in zones:
            zones.append(machine["zone"])

    for zone_name in zones:
        group = [machine for machine in visible if machine["zone"] == zone_name]
        open_in_zone = sum(not machine["in_use"] for machine in group)
        st.subheader(zone_name)
        st.caption(f"{open_in_zone} of {len(group)} open")
        columns = st.columns(3)
        for index, machine in enumerate(group):
            with columns[index % 3]:
                render_card(machine)


def render_booking(floor):
    open_names = [machine["name"] for machine in floor if not machine["in_use"]]
    yours = [machine["name"] for machine in floor if machine.get("booked_by_you")]

    st.subheader("Your session")
    st.caption(
        "Claim an open machine on this screen. Refresh leaves it in place. "
        "Reloading the page clears it."
    )
    claim_col, release_col = st.columns(2)
    with claim_col:
        if open_names:
            with st.form("claim_form"):
                choice = st.selectbox("Open machine", open_names)
                claimed = st.form_submit_button("Start session", width="stretch")
            if claimed and claim_machine(floor, choice):
                st.session_state.updated_at = datetime.now(TORONTO_TZ)
                st.rerun()
        else:
            st.info("Every machine is in use.")
    with release_col:
        if yours:
            with st.form("release_form"):
                choice = st.selectbox("Your machine", yours)
                released = st.form_submit_button("I'm done", width="stretch")
            if released and release_machine(floor, choice):
                st.session_state.updated_at = datetime.now(TORONTO_TZ)
                st.rerun()
        else:
            st.caption("You have not claimed a machine.")


def render_assistant():
    st.divider()
    st.subheader("Skip the wait")
    st.write(
        "Say what you want to train. The assistant reads the board above and "
        "sends you only to machines that are open."
    )
    if not has_api_key():
        st.warning("Add `GOOGLE_API_KEY` to `.env`, then restart, to use the assistant.")

    suggestion_cols = st.columns(3)
    for column, suggestion in zip(suggestion_cols, SUGGESTIONS):
        if column.button(suggestion, width="stretch"):
            st.session_state.pending_question = suggestion

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.form("ask_form", clear_on_submit=True):
        typed = st.text_input(
            "What do you want to train?",
            placeholder="Chest, legs, or a short back session",
        )
        submitted = st.form_submit_button("Ask")

    question = st.session_state.pop("pending_question", None)
    if submitted and typed.strip():
        question = typed.strip()
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Checking what's open..."):
        answer = ask_assistant(
            question,
            st.session_state.floor,
            st.session_state.messages[:-1],
        )
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()


def main():
    st.set_page_config(page_title="Gym floor", layout="wide")
    ensure_state()
    render_board()
    render_assistant()


main()
