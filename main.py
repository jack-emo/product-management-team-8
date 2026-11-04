import json
import os
import random
from datetime import datetime

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL_NAME = "gemini-2.5-flash"

# name, zone, what it trains
CATALOG = [
    ("Treadmill 1", "Cardio", "Cardio"),
    ("Treadmill 2", "Cardio", "Cardio"),
    ("Treadmill 3", "Cardio", "Cardio"),
    ("Treadmill 4", "Cardio", "Cardio"),
    ("Elliptical 1", "Cardio", "Cardio"),
    ("Elliptical 2", "Cardio", "Cardio"),
    ("Bike 1", "Cardio", "Cardio"),
    ("Bike 2", "Cardio", "Cardio"),
    ("Rower", "Cardio", "Cardio, back"),
    ("Stair climber", "Cardio", "Cardio, legs"),
    ("Squat rack 1", "Free weights", "Quads, glutes"),
    ("Squat rack 2", "Free weights", "Quads, glutes"),
    ("Flat bench 1", "Free weights", "Chest, triceps"),
    ("Flat bench 2", "Free weights", "Chest, triceps"),
    ("Incline bench", "Free weights", "Upper chest, shoulders"),
    ("Dumbbell area", "Free weights", "Full body"),
    ("Leg press", "Machines", "Quads, glutes"),
    ("Hack squat", "Machines", "Quads, glutes"),
    ("Leg extension", "Machines", "Quads"),
    ("Leg curl", "Machines", "Hamstrings"),
    ("Lat pulldown", "Machines", "Back"),
    ("Seated row", "Machines", "Back"),
    ("Cable station", "Machines", "Back, chest, arms"),
    ("Chest press", "Machines", "Chest, triceps"),
    ("Shoulder press", "Machines", "Shoulders"),
    ("Pec deck", "Machines", "Chest"),
    ("Assisted pull-up", "Machines", "Back, biceps"),
    ("Biceps curl", "Machines", "Biceps"),
    ("Dip station", "Machines", "Triceps, chest"),
]

SUGGESTIONS = [
    "I want chest. What's actually free?",
    "Both squat racks are awkward to wait on. What else hits legs?",
    "I have 20 minutes. Build a back workout from open machines.",
]

SYSTEM = """You help a person who is already at a public gym avoid waiting on taken equipment.
You receive the live floor, split into available and in_use.
Recommend only machines listed under available.
If the machines they would normally use are in use, say those are taken and point them to a free machine that trains the same muscles.
Use minutes_in_use only to say a station was recently started. Do not guess when someone will get off.
Give a short plan they can follow right now: where to go, in order.
Do not invent equipment that is not on the floor.
If an earlier message conflicts with the live floor, follow the live floor."""


def has_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return False
    lowered = key.lower()
    return lowered not in {"your_google_api_key_here", "your-key-here"}


def fresh_floor():
    floor = []
    for name, zone, muscles in CATALOG:
        in_use = random.random() < 0.45
        floor.append(
            {
                "name": name,
                "zone": zone,
                "muscles": muscles,
                "in_use": in_use,
                "minutes": random.randint(4, 28) if in_use else 0,
            }
        )
    return floor


def refresh_floor(floor):
    for machine in floor:
        if random.random() < 0.28:
            machine["in_use"] = not machine["in_use"]
            machine["minutes"] = random.randint(1, 12) if machine["in_use"] else 0
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
            in_use.append(entry)
        else:
            available.append(entry)
    return {"available": available, "in_use": in_use}


def show_html(html):
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_card(machine):
    if machine["in_use"]:
        label = "In use"
        detail = f"{machine['minutes']} min"
        accent = "#b42318"
        background = "#fff7f6"
    else:
        label = "Available"
        detail = "Open"
        accent = "#067647"
        background = "#f4fbf7"
    show_html(
        f"""
        <div style="background:{background};border:1px solid #eceae6;border-left:4px solid {accent};border-radius:10px;padding:12px 14px;margin-bottom:10px;">
            <div style="font-weight:600;font-size:1rem;">{machine["name"]}</div>
            <div style="color:#667085;font-size:0.85rem;margin-top:2px;">{machine["muscles"]}</div>
            <div style="color:{accent};font-weight:600;font-size:0.9rem;margin-top:8px;">{label} · {detail}</div>
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
        st.session_state.updated_at = datetime.now()
        st.session_state.messages = []


def render_board():
    floor = st.session_state.floor
    open_count = sum(not machine["in_use"] for machine in floor)
    busy_count = len(floor) - open_count
    updated = st.session_state.updated_at.strftime("%I:%M %p").lstrip("0")

    title_col, action_col = st.columns([4, 1])
    with title_col:
        st.title("What's free right now")
        st.caption(
            f"Updated {updated}. Proof of concept with a simulated floor, "
            "so you can see open machines before you walk over and wait."
        )
    with action_col:
        st.write("")
        if st.button("Refresh status", width="stretch"):
            refresh_floor(floor)
            st.session_state.updated_at = datetime.now()
            st.rerun()

    metric_cols = st.columns(3)
    metric_cols[0].metric("Available", open_count)
    metric_cols[1].metric("In use", busy_count)
    metric_cols[2].metric("On the floor", len(floor))

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
