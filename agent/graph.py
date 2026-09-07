from langgraph.graph import StateGraph, END
from agent.state import VeriskState
from agent.nodes import (
    classify_intent,
    retrieve_claim,
    retrieve_weather,
    retrieve_estimate,
    search_knowledge_base,
    stage_write_action,
    execute_write_action,
    generate_response,
)

# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

_WRITE_INTENTS = {"upload_evidence", "submit_work_order", "submit_invoice", "create_work_order"}
_CLAIM_INTENTS = _WRITE_INTENTS | {"check_status"}


def _route_after_classify(state: VeriskState) -> str:
    intent = state.get("intent", "unknown")
    claim_id = state.get("claim_id", "")

    if intent in _CLAIM_INTENTS and claim_id:
        return "retrieve_claim"
    return "search_knowledge_base"


def _route_after_retrieve_claim(state: VeriskState) -> str:
    intent = state.get("intent", "unknown")

    if intent == "check_status":
        return "retrieve_weather"
    if intent in _WRITE_INTENTS:
        return "stage_write_action"
    return "generate_response"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

builder = StateGraph(VeriskState)

# Nodes
builder.add_node("classify_intent", classify_intent)
builder.add_node("retrieve_claim", retrieve_claim)
builder.add_node("retrieve_weather", retrieve_weather)
builder.add_node("retrieve_estimate", retrieve_estimate)
builder.add_node("search_knowledge_base", search_knowledge_base)
builder.add_node("stage_write_action", stage_write_action)
builder.add_node("execute_write_action", execute_write_action)
builder.add_node("generate_response", generate_response)

# Entry point
builder.set_entry_point("classify_intent")

# Conditional: after classify_intent
builder.add_conditional_edges(
    "classify_intent",
    _route_after_classify,
    {
        "retrieve_claim": "retrieve_claim",
        "search_knowledge_base": "search_knowledge_base",
    },
)

# Conditional: after retrieve_claim
builder.add_conditional_edges(
    "retrieve_claim",
    _route_after_retrieve_claim,
    {
        "retrieve_weather": "retrieve_weather",
        "stage_write_action": "stage_write_action",
        "generate_response": "generate_response",
    },
)

# Fixed edges
builder.add_edge("retrieve_weather", "retrieve_estimate")
builder.add_edge("retrieve_estimate", "generate_response")
builder.add_edge("stage_write_action", "generate_response")
builder.add_edge("search_knowledge_base", "generate_response")
builder.add_edge("generate_response", END)

# Compile
graph = builder.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_turn(state: dict) -> dict:
    """Run one turn through the graph. Returns the updated full state."""
    result = graph.invoke(state)
    return result
