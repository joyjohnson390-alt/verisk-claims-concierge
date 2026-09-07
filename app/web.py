"""
Verisk Claims Concierge AI — Web UI server.
Serves a browser-based chat interface backed by the same LangGraph agent.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Verisk Claims Concierge AI")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Session state (single-session demo — not multi-user)
# ---------------------------------------------------------------------------
_session = {
    "persona": "claimant",
    "user_id": "CLM-001",
    "messages": [],
    "claim_id": "",
    "claim_data": {},
    "weather_data": {},
    "estimate_data": {},
    "weather_available": True,
    "write_payload": {},
    "awaiting_confirmation": False,
    "error_message": "",
    "intent": "",
}

PERSONA_DEFAULTS = {
    "claimant":   {"user_id": "CLM-001", "name": "Robert Chen"},
    "contractor": {"user_id": "CON-001", "name": "Jake Morales"},
    "adjuster":   {"user_id": "ADJ-001", "name": "Maria Santos"},
}

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str

class PersonaRequest(BaseModel):
    persona: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    sources: list
    awaiting_confirmation: bool
    weather_available: bool
    persona: str
    user_id: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_agent(message: str) -> dict:
    from langchain_core.messages import HumanMessage
    from agent.graph import run_turn

    state = dict(_session)
    state["messages"] = list(_session["messages"]) + [HumanMessage(content=message)]

    result = run_turn(state)

    # Merge result back into session
    for key in (
        "messages", "claim_id", "claim_data", "weather_data", "estimate_data",
        "weather_available", "write_payload", "awaiting_confirmation",
        "error_message", "intent",
    ):
        if key in result:
            _session[key] = result[key]

    # Extract last AI message
    reply = ""
    for msg in reversed(result.get("messages", [])):
        msg_type = getattr(msg, "type", "") or getattr(msg, "role", "")
        content = getattr(msg, "content", "")
        if msg_type in ("ai", "assistant") and content:
            reply = content if isinstance(content, str) else str(content)
            break

    sources = []
    if result.get("claim_data"):
        sources.append("Data 360 (PES + AccuLynx)")
    if result.get("weather_data") and result.get("weather_available"):
        sources.append("NOAA Weather Feed")
    if result.get("estimate_data") and "error" not in result.get("estimate_data", {}):
        sources.append("AccuLynx Estimates")

    return {
        "reply": reply or "No response received.",
        "sources": sources,
        "awaiting_confirmation": result.get("awaiting_confirmation", False),
        "weather_available": result.get("weather_available", True),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = _run_agent(req.message)
        return ChatResponse(
            reply=result["reply"],
            sources=result["sources"],
            awaiting_confirmation=result["awaiting_confirmation"],
            weather_available=result["weather_available"],
            persona=_session["persona"],
            user_id=_session["user_id"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/persona")
def set_persona(req: PersonaRequest):
    if req.persona not in PERSONA_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {req.persona}")
    _session["persona"] = req.persona
    _session["user_id"] = req.user_id or PERSONA_DEFAULTS[req.persona]["user_id"]
    _session["messages"] = []
    _session["claim_id"] = ""
    _session["claim_data"] = {}
    _session["weather_data"] = {}
    _session["estimate_data"] = {}
    _session["awaiting_confirmation"] = False
    _session["write_payload"] = {}
    return {
        "persona": _session["persona"],
        "user_id": _session["user_id"],
        "name": PERSONA_DEFAULTS[req.persona]["name"],
    }


@app.post("/api/clear")
def clear_session():
    _session["messages"] = []
    _session["claim_id"] = ""
    _session["claim_data"] = {}
    _session["weather_data"] = {}
    _session["estimate_data"] = {}
    _session["awaiting_confirmation"] = False
    _session["write_payload"] = {}
    return {"ok": True}


@app.get("/api/weather/status")
def weather_status():
    import httpx
    try:
        r = httpx.get("http://localhost:8001/admin/status", timeout=2)
        return r.json()
    except Exception:
        return {"enabled": False}


@app.post("/api/weather/toggle")
def weather_toggle():
    import httpx
    try:
        r = httpx.post("http://localhost:8001/admin/toggle", timeout=2)
        return r.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/demo/{n}")
def run_demo_scenario(n: int):
    """Return the pre-built message for demo scenario n (1, 2, or 3)."""
    demos = {
        1: {
            "persona": "claimant",
            "user_id": "CLM-001",
            "message": (
                "What's the current status of my claim CLM-2024-0891? "
                "I want to know everything — the damage assessment, the repair progress, "
                "and whether there was a weather event linked to my claim."
            ),
        },
        2: {
            "persona": "contractor",
            "user_id": "CON-001",
            "message": (
                "I need to submit an update on work order WO-2024-0891-A. "
                "Roof replacement is 80% complete — we finished installing new shingles "
                "on the front section. On track to complete by end of this week."
            ),
        },
        3: {
            "persona": "adjuster",
            "user_id": "ADJ-001",
            "message": "Show me all the claims in my current book.",
        },
    }
    if n not in demos:
        raise HTTPException(status_code=404, detail="Demo not found")

    scenario = demos[n]
    # Switch persona first
    _session["persona"] = scenario["persona"]
    _session["user_id"] = scenario["user_id"]
    _session["messages"] = []
    _session["claim_id"] = ""
    _session["claim_data"] = {}

    try:
        result = _run_agent(scenario["message"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        **result,
        "sent_message": scenario["message"],
        "persona": _session["persona"],
        "user_id": _session["user_id"],
        "persona_name": PERSONA_DEFAULTS[scenario["persona"]]["name"],
    }
