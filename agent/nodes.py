import json
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agent.state import VeriskState
from agent.tools import (
    get_claim,
    get_weather,
    get_estimate,
    write_work_order,
    write_invoice,
    write_evidence,
    update_work_order_status,
    list_adjuster_claims,
)
from agent.prompts import (
    CLAIMANT_PROMPT,
    CONTRACTOR_PROMPT,
    ADJUSTER_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
)

def _get_llm():
    headers = {}
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    if workspace_id:
        headers["anthropic-workspace-id"] = workspace_id
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=0,
        default_headers=headers if headers else None,
    )


def classify_intent(state: VeriskState) -> dict:
    """Classify the user's intent and extract claim_id from the last human message."""
    messages = state["messages"]
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    if last_human is None:
        return {"intent": "unknown", "claim_id": ""}

    response = _get_llm().invoke([
        SystemMessage(content=INTENT_CLASSIFIER_PROMPT),
        HumanMessage(content=last_human.content),
    ])

    try:
        parsed = json.loads(response.content)
        return {
            "intent": parsed.get("intent", "unknown"),
            "claim_id": parsed.get("claim_id", ""),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"intent": "unknown", "claim_id": ""}


def retrieve_claim(state: VeriskState) -> dict:
    """Fetch claim data from Verisk PEN/PES + AccuLynx."""
    result = get_claim(state["claim_id"], state["user_id"], state["persona"])
    updates = {"claim_data": result}
    if "error" in result:
        updates["error_message"] = result["error"]
    return updates


def retrieve_weather(state: VeriskState) -> dict:
    """Fetch NOAA weather data for the loss location and date."""
    claim = state.get("claim_data") or {}
    lat = claim.get("loss_lat")
    lon = claim.get("loss_lon")
    date = claim.get("loss_date")

    if lat is None or lon is None or date is None:
        return {"weather_data": {}, "weather_available": False}

    result = get_weather(lat, lon, date)
    return {
        "weather_data": result,
        "weather_available": "error" not in result,
    }


def retrieve_estimate(state: VeriskState) -> dict:
    """Fetch the AccuLynx estimate for the current claim."""
    result = get_estimate(state["claim_id"])
    return {"estimate_data": result}


def search_knowledge_base(state: VeriskState) -> dict:
    """Query the knowledge base with the last human message and stash results."""
    from knowledge_base.kb import query_kb

    messages = state["messages"]
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    message_text = last_human.content if last_human else ""

    results = query_kb(message_text, n_results=3)
    return {"claim_data": {"kb_results": results}}


def stage_write_action(state: VeriskState) -> dict:
    """Build a write_payload from the current intent and message, then await confirmation."""
    intent = state.get("intent", "")
    claim_data = state.get("claim_data") or {}
    messages = state["messages"]

    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)),
        None,
    )
    message_text = last_human.content if last_human else ""

    work_order_id = claim_data.get("work_order_id", "")

    if intent == "submit_work_order":
        payload = {
            "type": "work_order_update",
            "work_order_id": work_order_id,
            "notes": message_text,
        }
    elif intent == "submit_invoice":
        # Attempt to parse a dollar amount from the message
        amount = 0
        for token in message_text.replace(",", "").split():
            stripped = token.lstrip("$")
            try:
                amount = float(stripped)
                break
            except ValueError:
                continue
        payload = {
            "type": "invoice",
            "work_order_id": work_order_id,
            "amount": amount,
            "notes": message_text,
        }
    elif intent == "create_work_order":
        payload = {
            "type": "work_order_create",
            "claim_id": state["claim_id"],
            "description": message_text,
        }
    elif intent == "upload_evidence":
        payload = {
            "type": "evidence",
            "claim_id": state["claim_id"],
            "filename": "upload_pending.jpg",
            "description": message_text,
        }
    else:
        payload = {}

    return {"write_payload": payload, "awaiting_confirmation": True}


def execute_write_action(state: VeriskState) -> dict:
    """Execute a previously staged write action after user confirmation."""
    payload = state.get("write_payload") or {}
    action_type = payload.get("type", "")
    claim_data = state.get("claim_data") or {}

    if action_type == "work_order_update":
        result = update_work_order_status(
            payload.get("work_order_id", ""),
            "in_progress",
            payload.get("notes", ""),
        )
    elif action_type == "invoice":
        result = write_invoice(
            payload.get("work_order_id", ""),
            payload.get("amount", 0),
            payload.get("notes", ""),
        )
    elif action_type == "work_order_create":
        result = write_work_order(
            payload.get("claim_id", ""),
            payload.get("contractor_id", "TBD"),
            payload.get("description", ""),
        )
    elif action_type == "evidence":
        result = write_evidence(
            payload.get("claim_id", ""),
            payload.get("filename", "upload_pending.jpg"),
            payload.get("description", ""),
            state.get("user_id", "unknown"),
        )
    else:
        result = {"error": f"Unknown action type: {action_type}"}

    return {
        "write_payload": {},
        "awaiting_confirmation": False,
        "claim_data": {**claim_data, "write_result": result},
    }


def generate_response(state: VeriskState) -> dict:
    """Generate the final LLM response using persona prompt + all available context."""
    persona = state.get("persona", "claimant")
    if persona == "contractor":
        system_prompt = CONTRACTOR_PROMPT
    elif persona == "adjuster":
        system_prompt = ADJUSTER_PROMPT
    else:
        system_prompt = CLAIMANT_PROMPT

    weather_available = state.get("weather_available", False)
    weather_section = (
        json.dumps(state.get("weather_data") or {}, indent=2)
        if weather_available
        else "UNAVAILABLE — weather service is currently offline"
    )

    context = (
        "=== CLAIM DATA (source: Verisk PEN / PES + AccuLynx) ===\n"
        f"{json.dumps(state.get('claim_data') or {}, indent=2)}\n\n"
        "=== WEATHER/LOSS EVENT DATA (source: NOAA Weather Feed) ===\n"
        f"{weather_section}\n\n"
        "=== ACCULYNX ESTIMATE ===\n"
        f"{json.dumps(state.get('estimate_data') or {}, indent=2)}"
    )

    if state.get("awaiting_confirmation"):
        context += (
            "\n\n=== PENDING ACTION (requires your confirmation) ===\n"
            f"{json.dumps(state.get('write_payload') or {}, indent=2)}\n"
            'Please confirm: reply "yes" to execute, "no" to cancel.'
        )

    llm_messages = [
        SystemMessage(content=f"{system_prompt}\n\n{context}"),
        *state["messages"],
    ]

    response = _get_llm().invoke(llm_messages)
    return {"messages": [AIMessage(content=response.content)]}
