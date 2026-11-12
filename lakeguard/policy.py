"""Deterministic safety policy for proposed incident actions."""
from enum import Enum

class Action(str, Enum):
    NOTIFY = "notify"
    QUARANTINE = "quarantine"
    RETRY = "retry"
    ALTER_SCHEMA = "alter_schema"
    REWRITE_HISTORY = "rewrite_history"


def evaluate_action(action: Action, *, authorized: bool, retry_count: int = 0) -> tuple[bool, str]:
    """Allow only bounded, explicitly authorized low-risk actions."""
    if not authorized:
        return False, "Execution not authorized"
    if action in {Action.ALTER_SCHEMA, Action.REWRITE_HISTORY}:
        return False, "Human approval required"
    if action == Action.RETRY and retry_count >= 1:
        return False, "Retry limit exceeded"
    return True, "Permitted by policy"
