"""LangGraph incident triage with safe default: advisory only."""
from typing import TypedDict
from lakeguard.policy import Action, evaluate_action

class AgentState(TypedDict, total=False):
    incident_id: str
    evidence: dict
    diagnosis: str
    proposed_action: str
    approved: bool
    decision: str


def investigate(state: AgentState) -> dict:
    """Summarize verified evidence without inventing root causes."""
    evidence = state.get("evidence", {})
    return {"diagnosis": f"Triage evidence: {evidence}. Root cause unconfirmed."}


def propose(state: AgentState) -> dict:
    """Default to notification; no LLM can bypass the policy engine."""
    return {"proposed_action": Action.NOTIFY.value}


def gate(state: AgentState) -> dict:
    """Evaluate authorization before external side effects."""
    action = Action(state.get("proposed_action", Action.NOTIFY.value))
    allowed, reason = evaluate_action(action, authorized=state.get("approved", False))
    return {"decision": "allowed" if allowed else f"blocked: {reason}"}


def build_graph():
    """Compile an explicit investigation → proposal → policy graph."""
    from langgraph.graph import END, START, StateGraph
    graph = StateGraph(AgentState)
    graph.add_node("investigate", investigate)
    graph.add_node("propose", propose)
    graph.add_node("policy_gate", gate)
    graph.add_edge(START, "investigate")
    graph.add_edge("investigate", "propose")
    graph.add_edge("propose", "policy_gate")
    graph.add_edge("policy_gate", END)
    return graph.compile()
