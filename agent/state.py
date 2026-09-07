from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class VeriskState(TypedDict):
    messages: Annotated[list, add_messages]
    persona: str           # "claimant" | "contractor" | "adjuster"
    user_id: str           # e.g. "CLM-001", "CON-001", "ADJ-001"
    intent: str            # "check_status" | "upload_evidence" | "submit_work_order" | "submit_invoice" | "create_work_order" | "general_query" | "unknown"
    claim_id: str          # extracted from user message or ""
    claim_data: dict       # from DB query, {} if not found
    weather_data: dict     # from weather API, {} if unavailable
    estimate_data: dict    # from AccuLynx API, {} if unavailable
    weather_available: bool  # False if API returned 503
    write_payload: dict    # staged write (work order / invoice / evidence) awaiting confirmation
    awaiting_confirmation: bool  # True when a write is staged
    error_message: str     # "" if no error
